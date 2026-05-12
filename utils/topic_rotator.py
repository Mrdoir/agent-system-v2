""" 
TOPIC ROTATOR v2 — rotation state stored in Postgres (not state/rotation_state.json)
Survives Render restarts. Everything else identical to original.
"""

import requests
from datetime import datetime, timedelta
from utils.logger import log
from utils.database import get_conn

TOPICS_FILE = "research_topics.json"


def _get_last_rotation() -> datetime:
    """Read last rotation timestamp from Postgres manager_state table."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT value FROM manager_state WHERE key = 'last_rotation'")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            import json
            return datetime.fromisoformat(json.loads(row[0]))
    except Exception as e:
        log("topic_rotator", f"_get_last_rotation error: {e}")
    return datetime(2000, 1, 1)


def _set_last_rotation():
    """Save current timestamp as last rotation in Postgres."""
    import json
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO manager_state (key, value)
            VALUES ('last_rotation', %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (json.dumps(datetime.now().isoformat()),))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log("topic_rotator", f"_set_last_rotation error: {e}")


def should_rotate() -> bool:
    """Check if 24 hours have passed since last rotation."""
    last = _get_last_rotation()
    return datetime.now() - last > timedelta(hours=24)


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
    month = datetime.now().strftime("%B %Y")
    return [
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


def rotate_topics():
    """Add fresh topics to Postgres research_topics table daily."""
    if not should_rotate():
        return False

    log("topic_rotator", "Rotating topics — adding fresh research targets")

    fresh = generate_fresh_topics()

    # Add to Postgres research_topics (db_add_topic handles duplicates gracefully)
    try:
        conn = get_conn()
        cur = conn.cursor()
        for topic in fresh:
            cur.execute("""
                INSERT INTO research_topics (topic, added_at)
                VALUES (%s, %s)
                ON CONFLICT (topic) DO NOTHING
            """, (topic, datetime.now().isoformat()))
        conn.commit()
        cur.close()
        conn.close()
        log("topic_rotator", f"Added {len(fresh)} fresh topics to Postgres")
    except Exception as e:
        log("topic_rotator", f"rotate_topics DB error: {e}")
        return False

    _set_last_rotation()
    return True
