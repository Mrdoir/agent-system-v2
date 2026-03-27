"""
Daily topic rotation — automatically generates fresh research topics
based on trending searches. Agents never run out of new things to research.
"""

import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from utils.logger import log
from utils.web_search import search_web

TOPICS_FILE = "research_topics.json"
ROTATION_STATE = "state/rotation_state.json"


def get_trending_topics() -> list:
    """Get trending topics from DuckDuckGo trending searches."""
    trending = []
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/?q=trending+apps+2026&format=json&no_html=1",
            timeout=10
        )
        data = resp.json()
        for topic in data.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and topic.get("Text"):
                trending.append(topic["Text"][:80])
    except Exception as e:
        log("topic_rotator", f"Trending fetch failed: {e}")

    return trending


def generate_fresh_topics() -> list:
    """Generate new research topics based on current date and trends."""
    now = datetime.now()
    month = now.strftime("%B %Y")

    # Base rotating topics — different angles each time
    rotating_pool = [
        f"most complained about productivity apps {month}",
        f"underserved SaaS niches {month}",
        f"fastest growing mobile app categories {month}",
        f"AI tools nobody has built yet {month}",
        f"what freelancers hate about their tools {month}",
        f"app ideas from Reddit complaints {month}",
        f"blue ocean opportunities in mobile apps {month}",
        f"failed apps and why they failed {month}",
        f"most requested features in productivity apps {month}",
        f"emerging markets for B2C apps {month}",
        f"niche communities underserved by apps {month}",
        f"tools developers wish existed {month}",
        f"pain points in note taking apps {month}",
        f"gaps in project management tools {month}",
        f"what students need that apps dont provide {month}",
    ]

    return rotating_pool


def should_rotate() -> bool:
    """Check if 24 hours have passed since last rotation."""
    if not Path(ROTATION_STATE).exists():
        return True
    with open(ROTATION_STATE) as f:
        state = json.load(f)
    last_rotation = datetime.fromisoformat(state.get("last_rotation", "2000-01-01"))
    return datetime.now() - last_rotation > timedelta(hours=24)


def rotate_topics():
    """Add fresh topics to the research queue daily."""
    if not should_rotate():
        return False

    log("topic_rotator", "Rotating topics — adding fresh research targets")

    # Load current topics
    current = {"topics": []}
    if Path(TOPICS_FILE).exists():
        with open(TOPICS_FILE) as f:
            current = json.load(f)

    # Get fresh topics
    fresh = generate_fresh_topics()

    # Keep core topics + add fresh ones, limit to 15 total
    core_topics = current.get("topics", [])[:5]
    all_topics = list(dict.fromkeys(core_topics + fresh))[:15]

    with open(TOPICS_FILE, "w") as f:
        json.dump({"topics": all_topics}, f, indent=2)

    # Save rotation state
    with open(ROTATION_STATE, "w") as f:
        json.dump({"last_rotation": datetime.now().isoformat()}, f)

    log("topic_rotator", f"Topics rotated: {len(all_topics)} topics loaded")
    return True
