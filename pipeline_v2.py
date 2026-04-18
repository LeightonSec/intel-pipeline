"""
Intel Pipeline v2 — Multi-Agent Architecture
LeightonSec | github.com/LeightonSec

Agents:
  FetcherAgent      — pulls RSS feeds by category
  FilterAgent       — keyword relevance filter
  DeduplicatorAgent — removes already-seen items
  EnricherAgent     — scores items by severity/relevance
  SummariserAgent   — Claude API summarisation
  ReporterAgent     — builds and saves markdown report

Orchestrator coordinates flow via LangGraph state machine.
"""

import os
import sys
import logging
from datetime import datetime
from typing import TypedDict, Dict, List, Any
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END

from fetcher import fetch_all_feeds, filter_by_keywords
from deduplicator import filter_new_items
from summariser import summarise_all

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

OBSIDIAN_PATH = os.path.expanduser("~/Documents/MyVault/Inbox")

USER_KEYWORDS = [
    "vulnerability", "exploit", "ransomware", "zero-day", "CVE",
    "malware", "phishing", "breach", "firewall", "intrusion",
    "AI", "LLM", "machine learning", "neural network", "Claude",
    "GPT", "artificial intelligence", "agentic",
    "BSV", "Bitcoin SV", "Bastion", "blockchain", "post-quantum",
    "zero knowledge", "cryptography", "privacy protocol",
    "cybersecurity", "SIEM", "SOC", "threat intelligence",
    "network security", "cloud security"
]

# ── Pipeline State ─────────────────────────────────────────────────────────────

class PipelineState(TypedDict):
    period: str
    raw_items: Dict[str, List[Any]]
    filtered_items: Dict[str, List[Any]]
    deduped_items: Dict[str, List[Any]]
    enriched_items: Dict[str, List[Any]]
    summaries: Dict[str, str]
    report: str
    session_seen: set
    errors: List[str]
    item_counts: Dict[str, Dict]

# ── Agents ────────────────────────────────────────────────────────────────────

def fetcher_agent(state: PipelineState) -> PipelineState:
    """Agent 1: Pull all RSS feeds"""
    logger.info("[FetcherAgent] Starting feed collection")
    try:
        raw = fetch_all_feeds()
        counts = {cat: {"fetched": len(items)} for cat, items in raw.items()}
        logger.info(f"[FetcherAgent] Done — {sum(len(v) for v in raw.values())} total items")
        return {**state, "raw_items": raw, "item_counts": counts}
    except Exception as e:
        logger.error(f"[FetcherAgent] Failed: {e}")
        return {**state, "raw_items": {}, "errors": state["errors"] + [f"FetcherAgent: {e}"]}


def filter_agent(state: PipelineState) -> PipelineState:
    """Agent 2: Keyword relevance filter"""
    logger.info("[FilterAgent] Applying keyword filter")
    filtered = {}
    counts = state.get("item_counts", {})

    for category, items in state["raw_items"].items():
        relevant = filter_by_keywords(items, USER_KEYWORDS)
        filtered[category] = relevant
        if category in counts:
            counts[category]["after_keyword_filter"] = len(relevant)
        logger.info(f"[FilterAgent] {category}: {len(items)} → {len(relevant)} relevant")

    return {**state, "filtered_items": filtered, "item_counts": counts}


def deduplicator_agent(state: PipelineState) -> PipelineState:
    """Agent 3: Remove seen items"""
    logger.info("[DeduplicatorAgent] Deduplicating across session")
    deduped = {}
    counts = state.get("item_counts", {})
    session_seen = state.get("session_seen", set())

    for category, items in state["filtered_items"].items():
        new_items = filter_new_items(items, session_seen)
        deduped[category] = new_items
        if category in counts:
            counts[category]["after_dedup"] = len(new_items)
        logger.info(f"[DeduplicatorAgent] {category}: {len(items)} → {len(new_items)} new")

    return {**state, "deduped_items": deduped, "session_seen": session_seen, "item_counts": counts}


def enricher_agent(state: PipelineState) -> PipelineState:
    """Agent 4: Score items by severity"""
    logger.info("[EnricherAgent] Scoring items")

    HIGH_SEVERITY = [
        "critical", "zero-day", "0-day", "rce", "remote code execution",
        "actively exploited", "ransomware", "nation-state", "apt",
        "supply chain", "cisa", "emergency"
    ]
    MEDIUM_SEVERITY = [
        "vulnerability", "cve", "patch", "exploit", "breach",
        "phishing", "malware", "backdoor"
    ]

    enriched = {}
    for category, items in state["deduped_items"].items():
        scored = []
        for item in items:
            text = f"{item['title']} {item.get('summary', '')}".lower()
            if any(k in text for k in HIGH_SEVERITY):
                score = 3
                priority = "HIGH"
            elif any(k in text for k in MEDIUM_SEVERITY):
                score = 2
                priority = "MEDIUM"
            else:
                score = 1
                priority = "LOW"
            scored.append({**item, "priority": priority, "score": score})

        scored.sort(key=lambda x: x["score"], reverse=True)
        enriched[category] = scored
        high_count = sum(1 for i in scored if i["priority"] == "HIGH")
        logger.info(f"[EnricherAgent] {category}: {len(scored)} items, {high_count} HIGH priority")

    return {**state, "enriched_items": enriched}


def summariser_agent(state: PipelineState) -> PipelineState:
    """Agent 5: Claude API summarisation"""
    logger.info("[SummariserAgent] Sending to Claude")
    try:
        summaries = summarise_all(state["enriched_items"])
        return {**state, "summaries": summaries}
    except Exception as e:
        logger.error(f"[SummariserAgent] Failed: {e}")
        return {**state, "summaries": {}, "errors": state["errors"] + [f"SummariserAgent: {e}"]}


def reporter_agent(state: PipelineState) -> PipelineState:
    """Agent 6: Build and save markdown report"""
    logger.info("[ReporterAgent] Generating report")

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    period = state["period"]
    counts = state.get("item_counts", {})

    # Audit table
    audit_lines = []
    for cat, c in counts.items():
        fetched = c.get("fetched", 0)
        relevant = c.get("after_keyword_filter", 0)
        new = c.get("after_dedup", 0)
        audit_lines.append(f"| {cat} | {fetched} | {relevant} | {new} |")

    audit_table = ""
    if audit_lines:
        audit_table = (
            "\n## 📊 Pipeline Audit\n\n"
            "| Category | Fetched | Relevant | New |\n"
            "|----------|---------|----------|-----|\n"
            + "\n".join(audit_lines)
            + "\n\n---\n\n"
        )

    category_icons = {
        "security": "🔒 Security News",
        "ai_research": "🤖 AI Research",
        "bsv_bastion": "⛓️ BSV & Bastion",
        "cve": "🚨 CVE & Vulnerabilities",
        "custom": "🎯 Custom Topics"
    }

    report = f"# 🛡️ Intel Report v2 — {date_str} {period}\n"
    report += f"*Generated: {time_str} | LeightonSec Multi-Agent Intelligence Pipeline*\n\n---\n\n"
    report += audit_table

    for category, summary in state["summaries"].items():
        title = category_icons.get(category, f"📌 {category.title()}")
        report += f"## {title}\n\n{summary}\n\n---\n\n"

    if state["errors"]:
        report += "## ⚠️ Pipeline Errors\n\n"
        for err in state["errors"]:
            report += f"- {err}\n"
        report += "\n---\n\n"

    report += "*Report generated by intel-pipeline v2 (multi-agent) — LeightonSec*\n"

    filename = f"Intel-v2-{date_str}-{period}.md"
    os.makedirs("reports", exist_ok=True)
    local_path = os.path.join("reports", filename)
    with open(local_path, "w") as f:
        f.write(report)
    logger.info(f"[ReporterAgent] Saved locally: {local_path}")

    if os.path.exists(OBSIDIAN_PATH):
        obsidian_file = os.path.join(OBSIDIAN_PATH, filename)
        with open(obsidian_file, "w") as f:
            f.write(report)
        logger.info(f"[ReporterAgent] Saved to Obsidian: {obsidian_file}")

    return {**state, "report": report}

# ── Routing ───────────────────────────────────────────────────────────────────

def should_continue_after_fetch(state: PipelineState) -> str:
    if not state.get("raw_items"):
        logger.error("[Orchestrator] No items fetched — aborting")
        return "abort"
    return "continue"

def should_continue_after_dedup(state: PipelineState) -> str:
    total_new = sum(len(v) for v in state.get("deduped_items", {}).values())
    if total_new == 0:
        logger.info("[Orchestrator] No new items — skipping summarisation")
        return "skip_summarise"
    return "continue"

def abort_node(state: PipelineState) -> PipelineState:
    logger.error("[Orchestrator] Pipeline aborted")
    return state

def skip_summarise_node(state: PipelineState) -> PipelineState:
    logger.info("[Orchestrator] No new items — skipping to reporter")
    summaries = {cat: "No new items since last run." for cat in state.get("deduped_items", {})}
    return {**state, "summaries": summaries}

# ── Graph ─────────────────────────────────────────────────────────────────────

def build_pipeline() -> StateGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("fetcher", fetcher_agent)
    graph.add_node("filter", filter_agent)
    graph.add_node("deduplicator", deduplicator_agent)
    graph.add_node("enricher", enricher_agent)
    graph.add_node("summariser", summariser_agent)
    graph.add_node("reporter", reporter_agent)
    graph.add_node("abort", abort_node)
    graph.add_node("skip_summarise", skip_summarise_node)

    graph.set_entry_point("fetcher")

    graph.add_conditional_edges(
        "fetcher",
        should_continue_after_fetch,
        {"continue": "filter", "abort": "abort"}
    )

    graph.add_edge("filter", "deduplicator")

    graph.add_conditional_edges(
        "deduplicator",
        should_continue_after_dedup,
        {"continue": "enricher", "skip_summarise": "skip_summarise"}
    )

    graph.add_edge("enricher", "summariser")
    graph.add_edge("summariser", "reporter")
    graph.add_edge("skip_summarise", "reporter")
    graph.add_edge("reporter", END)
    graph.add_edge("abort", END)

    return graph.compile()

# ── Entry Point ───────────────────────────────────────────────────────────────

def run_pipeline(period: str = "AM") -> str:
    logger.info(f"[Orchestrator] Starting multi-agent pipeline v2 — {period} run")

    initial_state: PipelineState = {
        "period": period,
        "raw_items": {},
        "filtered_items": {},
        "deduped_items": {},
        "enriched_items": {},
        "summaries": {},
        "report": "",
        "session_seen": set(),
        "errors": [],
        "item_counts": {}
    }

    pipeline = build_pipeline()
    final_state = pipeline.invoke(initial_state)

    logger.info("[Orchestrator] Pipeline v2 complete")
    return final_state["report"]


if __name__ == "__main__":
    period = sys.argv[1] if len(sys.argv) > 1 else "AM"
    run_pipeline(period)