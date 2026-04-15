import json
import os
from datetime import datetime, timedelta

SEEN_FILE = "logs/seen_urls.json"

def load_seen_urls() -> dict:
    """Load previously seen URLs"""
    if not os.path.exists(SEEN_FILE):
        return {}
    try:
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_seen_urls(seen: dict):
    """Save seen URLs to file"""
    os.makedirs("logs", exist_ok=True)
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f, indent=2)

def clean_old_urls(seen: dict, days: int = 7) -> dict:
    """Remove URLs older than X days to prevent file growing forever"""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    return {url: date for url, date in seen.items() if date > cutoff}

def filter_new_items(items: list) -> list:
    """Remove items we've already seen"""
    seen = load_seen_urls()
    seen = clean_old_urls(seen)
    
    new_items = []
    now = datetime.utcnow().isoformat()
    
    for item in items:
        url = item.get("link", "")
        if url and url not in seen:
            new_items.append(item)
            seen[url] = now
    
    save_seen_urls(seen)
    return new_items