import yaml
import os
import logging

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "sources.yaml")

def load_config() -> dict:
    """Load pipeline configuration from YAML file"""
    try:
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"Config loaded from {CONFIG_PATH}")
        return config
    except FileNotFoundError:
        logger.error(f"Config file not found: {CONFIG_PATH}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Config parse error: {e}")
        return {}

def get_feeds(config: dict) -> dict:
    """Extract feed URLs by category"""
    return config.get("feeds", {})

def get_keywords(config: dict) -> list:
    """Flatten all keyword categories into one list"""
    keywords_dict = config.get("keywords", {})
    all_keywords = []
    for category_keywords in keywords_dict.values():
        all_keywords.extend(category_keywords)
    return all_keywords

def get_whitelist(config: dict) -> list:
    """Get whitelisted domains"""
    return config.get("whitelist", [])

def get_schedule(config: dict) -> dict:
    """Get schedule configuration"""
    return config.get("schedule", {
        "morning": "07:00",
        "evening": "19:00",
        "dedup_days": 1,
        "max_items_per_feed": 10
    })
