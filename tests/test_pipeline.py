import os
import sys

# Set a dummy API key before summariser is imported so the Anthropic client
# doesn't raise at module load time in CI / environments without a real key.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # gate: ignore — own repo root, enables local module imports, not cross-repo coupling

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from deduplicator import clean_old_urls, filter_new_items
from fetcher import filter_by_keywords, is_whitelisted
from summariser import summarise_all

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _item(title="Title", summary="Summary", link="https://example.com/1"):
    return {"title": title, "summary": summary, "link": link}


# ---------------------------------------------------------------------------
# Deduplicator — already-seen filtering
# ---------------------------------------------------------------------------

class TestDeduplicatorFiltering:
    def test_new_url_passes_through(self):
        items = [_item(link="https://example.com/new")]
        with patch("deduplicator.load_seen_urls", return_value={}), \
             patch("deduplicator.save_seen_urls"):
            result = filter_new_items(items)
        assert len(result) == 1

    def test_persistent_seen_url_is_filtered(self):
        url = "https://example.com/old"
        seen = {url: datetime.now(timezone.utc).isoformat()}
        items = [_item(link=url), _item(link="https://example.com/new")]
        with patch("deduplicator.load_seen_urls", return_value=seen), \
             patch("deduplicator.save_seen_urls"):
            result = filter_new_items(items)
        assert len(result) == 1
        assert result[0]["link"] == "https://example.com/new"

    def test_session_seen_url_is_filtered(self):
        url = "https://example.com/a"
        items = [_item(link=url)]
        session = {url}
        with patch("deduplicator.load_seen_urls", return_value={}), \
             patch("deduplicator.save_seen_urls"):
            result = filter_new_items(items, session_seen=session)
        assert result == []

    def test_item_without_link_is_skipped(self):
        items = [{"title": "No link", "summary": ""}]
        with patch("deduplicator.load_seen_urls", return_value={}), \
             patch("deduplicator.save_seen_urls"):
            result = filter_new_items(items)
        assert result == []

    def test_duplicate_within_same_batch_deduplicated(self):
        url = "https://example.com/dup"
        items = [_item(link=url), _item(title="Copy", link=url)]
        with patch("deduplicator.load_seen_urls", return_value={}), \
             patch("deduplicator.save_seen_urls"):
            result = filter_new_items(items)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Deduplicator — expiry
# ---------------------------------------------------------------------------

class TestDeduplicatorExpiry:
    def test_url_older_than_window_is_removed(self):
        old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        seen = {"https://example.com/old": old}
        result = clean_old_urls(seen, days=7)
        assert "https://example.com/old" not in result

    def test_url_within_window_is_kept(self):
        recent = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        seen = {"https://example.com/recent": recent}
        result = clean_old_urls(seen, days=7)
        assert "https://example.com/recent" in result

    def test_url_exactly_on_boundary_is_removed(self):
        # A URL timestamped exactly 7 days ago falls before the cutoff.
        boundary = (datetime.now(timezone.utc) - timedelta(days=7, seconds=1)).isoformat()
        seen = {"https://example.com/boundary": boundary}
        result = clean_old_urls(seen, days=7)
        assert "https://example.com/boundary" not in result

    def test_empty_seen_returns_empty(self):
        assert clean_old_urls({}, days=7) == {}

    def test_mixed_ages_only_keeps_recent(self):
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        fresh = datetime.now(timezone.utc).isoformat()
        seen = {"https://example.com/old": old, "https://example.com/fresh": fresh}
        result = clean_old_urls(seen, days=7)
        assert list(result.keys()) == ["https://example.com/fresh"]


# ---------------------------------------------------------------------------
# filter_by_keywords
# ---------------------------------------------------------------------------

class TestFilterByKeywords:
    def test_matching_title_is_kept(self):
        items = [_item(title="New ransomware campaign", summary="Details")]
        result = filter_by_keywords(items, ["ransomware"])
        assert len(result) == 1

    def test_matching_summary_is_kept(self):
        items = [_item(title="Generic headline", summary="CVE-2024-1234 disclosed")]
        result = filter_by_keywords(items, ["cve"])
        assert len(result) == 1

    def test_non_matching_item_is_dropped(self):
        items = [_item(title="Football scores", summary="Team wins")]
        result = filter_by_keywords(items, ["ransomware", "exploit"])
        assert result == []

    def test_matching_is_case_insensitive(self):
        items = [_item(title="Critical VULNERABILITY Found", summary="")]
        result = filter_by_keywords(items, ["vulnerability"])
        assert len(result) == 1

    def test_empty_keywords_returns_all_items(self):
        items = [_item(link="https://a.com/1"), _item(link="https://a.com/2")]
        result = filter_by_keywords(items, [])
        assert result == items

    def test_mixed_items_only_matching_returned(self):
        items = [
            _item(title="Zero-day exploit", link="https://a.com/1"),
            _item(title="Sports news", link="https://a.com/2"),
            _item(title="Phishing campaign", link="https://a.com/3"),
        ]
        result = filter_by_keywords(items, ["exploit", "phishing"])
        assert len(result) == 2
        links = {i["link"] for i in result}
        assert "https://a.com/1" in links
        assert "https://a.com/3" in links


# ---------------------------------------------------------------------------
# Summariser — JSON parse fallback
# ---------------------------------------------------------------------------

def _mock_response(text):
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    response.usage.input_tokens = 10
    response.usage.output_tokens = 10
    return response


class TestSummariserFallback:
    CATEGORIES = {
        "security": [_item(title="Sec item")],
        "ai_research": [_item(title="AI item", link="https://example.com/2")],
        "cve": [_item(title="CVE item", link="https://example.com/3")],
    }

    def test_fallback_populates_every_category(self):
        raw = "This is not valid JSON"
        with patch("summariser.client") as mock_client:
            mock_client.messages.create.return_value = _mock_response(raw)
            result = summarise_all(self.CATEGORIES)
        for cat in self.CATEGORIES:
            assert result[cat] == raw

    def test_fallback_does_not_silently_drop_categories(self):
        raw = "<<<broken output>>>"
        with patch("summariser.client") as mock_client:
            mock_client.messages.create.return_value = _mock_response(raw)
            result = summarise_all(self.CATEGORIES)
        assert set(result.keys()) == set(self.CATEGORIES.keys())

    def test_successful_parse_populates_from_json(self):
        payload = {
            "security": "Security briefing",
            "ai_research": "AI briefing",
            "cve": "CVE briefing",
        }
        with patch("summariser.client") as mock_client:
            mock_client.messages.create.return_value = _mock_response(json.dumps(payload))
            result = summarise_all(self.CATEGORIES)
        for cat, text in payload.items():
            assert result[cat] == text

    def test_markdown_fenced_json_is_parsed(self):
        payload = {"security": "Fenced briefing"}
        categorised = {"security": [_item()]}
        raw = f"```json\n{json.dumps(payload)}\n```"
        with patch("summariser.client") as mock_client:
            mock_client.messages.create.return_value = _mock_response(raw)
            result = summarise_all(categorised)
        assert result["security"] == "Fenced briefing"

    def test_empty_input_skips_api_call(self):
        with patch("summariser.client") as mock_client:
            result = summarise_all({"security": [], "cve": []})
        mock_client.messages.create.assert_not_called()
        assert result["security"] == "No relevant items for security."


# ---------------------------------------------------------------------------
# is_whitelisted
# ---------------------------------------------------------------------------

class TestIsWhitelisted:
    def test_exact_domain_allowed(self):
        with patch("fetcher.WHITELISTED_DOMAINS", ["example.com"]):
            assert is_whitelisted("https://example.com/feed") is True

    def test_non_whitelisted_domain_blocked(self):
        with patch("fetcher.WHITELISTED_DOMAINS", ["example.com"]):
            assert is_whitelisted("https://evil.com/feed") is False

    def test_www_prefix_is_stripped(self):
        with patch("fetcher.WHITELISTED_DOMAINS", ["example.com"]):
            assert is_whitelisted("https://www.example.com/feed") is True

    def test_subdomain_matches_via_endswith(self):
        with patch("fetcher.WHITELISTED_DOMAINS", ["example.com"]):
            assert is_whitelisted("https://feeds.example.com/rss") is True

    def test_suffix_confusion_domain_is_blocked(self):
        # "notexample.com"/"evil-example.com" end with "example.com" but are
        # NOT subdomains of it; a bare endswith check would let them bypass
        # the whitelist (domain-suffix confusion). They must be rejected.
        with patch("fetcher.WHITELISTED_DOMAINS", ["example.com"]):
            assert is_whitelisted("https://notexample.com/feed") is False
            assert is_whitelisted("https://evil-example.com/feed") is False

    def test_empty_whitelist_blocks_everything(self):
        with patch("fetcher.WHITELISTED_DOMAINS", []):
            assert is_whitelisted("https://example.com/feed") is False

    def test_non_url_string_returns_false(self):
        with patch("fetcher.WHITELISTED_DOMAINS", ["example.com"]):
            assert is_whitelisted("not-a-url") is False
