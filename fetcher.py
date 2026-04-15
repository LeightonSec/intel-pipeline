import feedparser
import requests
from bs4 import BeautifulSoup
import time
import logging
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Whitelisted domains - only fetch from approved sources
WHITELISTED_DOMAINS = [
    "krebsonsecurity.com",
    "bleepingcomputer.com",
    "thehackernews.com",
    "feedburner.com",
    "sans.org",
    "arxiv.org",
    "github.com",
    "threatpost.com",
    "darkreading.com",
    "securityweek.com",
    "coingeek.com",
    "bitcoinsv.io",
    "bsvblockchain.org",
    "cisa.gov",
    "us-cert.cisa.gov",
    "exploit-db.com",
    "nvd.nist.gov"
]

# RSS feed sources
RSS_FEEDS = {
    "security": [
        "https://krebsonsecurity.com/feed/",
        "https://feeds.feedburner.com/TheHackersNews",
        "https://www.bleepingcomputer.com/feed/",
        "https://www.darkreading.com/rss.xml",
        "https://www.securityweek.com/feed/"
    ],
    "ai_research": [
        "https://arxiv.org/rss/cs.AI",
        "https://arxiv.org/rss/cs.CR"
    ],
    "bsv_bastion": [
        "https://coingeek.com/feed/",
        "https://bitcoinsv.io/feed/"
    ],
    "cve": [
        "https://www.cisa.gov/uscert/ncas/alerts.xml",
        "https://www.cisa.gov/uscert/ncas/current-activity.xml",
        "https://www.exploit-db.com/rss.xml"
    ]
}

RATE_LIMIT_SECONDS = 2  # Wait between requests

def is_whitelisted(url: str) -> bool:
    """Check if URL domain is in whitelist"""
    try:
        domain = urlparse(url).netloc.replace("www.", "")
        return any(domain.endswith(w) for w in WHITELISTED_DOMAINS)
    except:
        return False

def fetch_rss_feed(feed_url: str, max_items: int = 10) -> list:
    """Fetch and parse an RSS feed"""
    if not is_whitelisted(feed_url):
        logger.warning(f"Blocked non-whitelisted feed: {feed_url}")
        return []

    try:
        logger.info(f"Fetching feed: {feed_url}")
        feed = feedparser.parse(feed_url)
        items = []

        for entry in feed.entries[:max_items]:
            item = {
                "title": entry.get("title", "No title"),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", ""),
                "published": entry.get("published", "Unknown date"),
                "source": feed_url
            }
            items.append(item)

        time.sleep(RATE_LIMIT_SECONDS)
        return items

    except Exception as e:
        logger.error(f"Error fetching {feed_url}: {e}")
        return []

def fetch_all_feeds(custom_feeds: list = None) -> dict:
    """Fetch all RSS feeds by category"""
    all_items = {}

    feeds = RSS_FEEDS.copy()
    if custom_feeds:
        feeds["custom"] = custom_feeds

    for category, feed_urls in feeds.items():
        logger.info(f"Fetching category: {category}")
        items = []
        for url in feed_urls:
            items.extend(fetch_rss_feed(url))
        all_items[category] = items
        logger.info(f"Fetched {len(items)} items for {category}")

    return all_items

def filter_by_keywords(items: list, keywords: list) -> list:
    """Filter items by keyword relevance"""
    if not keywords:
        return items

    filtered = []
    keywords_lower = [k.lower() for k in keywords]

    for item in items:
        text = f"{item['title']} {item['summary']}".lower()
        if any(keyword in text for keyword in keywords_lower):
            filtered.append(item)

    return filtered