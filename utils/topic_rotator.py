"""
TOPIC ROTATOR v3 — Smart topic generation and rotation
Improvements:
- Generate follow-up topics from high-scoring research
- Detect and skip saturated topics
- Trending topics from Hacker News
- Date-aware topic generation
- Topic clustering to avoid redundancy
"""

import os
import requests
from datetime import datetime, timedelta
from utils.logger import log_info, log_debug, log_warn
from utils.database import (
    get_conn, is_topic_saturated, get_insights, 
    get_results, get_fresh_topics, get_topic_stats
)


def _get_last_rotation() -> datetime:
    """Get last rotation timestamp from Postgres."""
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
        log_debug("topic_rotator", f"_get_last_rotation error: {e}")
    
    return datetime(2000, 1, 1)


def _set_last_rotation():
    """Save current time as last rotation."""
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
        log_debug("topic_rotator", f"_set_last_rotation error: {e}")


def should_rotate() -> bool:
    """Check if 24 hours have passed since last rotation."""
    last = _get_last_rotation()
    return datetime.now() - last > timedelta(hours=24)


def get_trending_from_hackernews() -> list:
    """Get trending topics from Hacker News."""
    try:
        resp = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={
                "tags": "story",
                "hitsPerPage": 10,
                "numericFilters": "points>100"
            },
            timeout=10
        )
        
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        topics = []
        
        for hit in data.get("hits", []):
            title = hit.get("title", "")
            # Extract potential research topics from titles
            if any(kw in title.lower() for kw in ["app", "startup", "product", "tool", "ai", "saas"]):
                # Convert to research topic format
                topic = f"{title} market analysis"
                topics.append(topic[:80])
        
        log_debug("topic_rotator", f"Found {len(topics)} trending topics from HN")
        return topics[:5]
        
    except Exception as e:
        log_debug("topic_rotator", f"HN trending error: {e}")
        return []


def generate_followup_topics() -> list:
    """Generate follow-up topics from high-scoring research."""
    topics = []
    
    try:
        # Get high-scoring results
        results = get_results(limit=50, min_score=7)
        
        if not results:
            return []
        
        # Extract unique topics that scored well
        seen = set()
        for r in results:
            topic = r.get("topic", "")
            if topic and topic not in seen:
                seen.add(topic)
                
                # Generate follow-up variations
                followups = [
                    f"{topic} deeper analysis",
                    f"{topic} competitor comparison",
                    f"{topic} user complaints 2026",
                    f"{topic} emerging solutions",
                ]
                
                for f in followups:
                    if not is_topic_saturated(f):
                        topics.append(f)
                        break  # Only one follow-up per original topic
        
        log_debug("topic_rotator", f"Generated {len(topics)} follow-up topics")
        return topics[:10]
        
    except Exception as e:
        log_debug("topic_rotator", f"Follow-up generation error: {e}")
        return []


def generate_fresh_topics() -> list:
    """Generate new research topics with current date context."""
    month_year = datetime.now().strftime("%B %Y")
    
    # Base topics with date context
    topics = [
        f"most complained about productivity apps {month_year}",
        f"underserved SaaS niches {month_year}",
        f"fastest growing mobile app categories {month_year}",
        f"AI tools nobody has built yet {month_year}",
        f"what freelancers hate about their tools {month_year}",
        f"app ideas from Reddit complaints {month_year}",
        f"blue ocean opportunities in mobile apps {month_year}",
        f"failed apps and why they failed {month_year}",
        f"most requested features in productivity apps {month_year}",
        f"emerging markets for B2C apps {month_year}",
        f"niche communities underserved by apps {month_year}",
        f"tools developers wish existed {month_year}",
        f"pain points in note taking apps {month_year}",
        f"gaps in project management tools {month_year}",
        f"what students need that apps dont provide {month_year}",
        f"subscription fatigue solutions {month_year}",
        f"local business software gaps {month_year}",
        f"creator economy tool gaps {month_year}",
        f"health app privacy concerns {month_year}",
        f"remote work tool frustrations {month_year}",
    ]
    
    # Filter out saturated topics
    fresh = [t for t in topics if not is_topic_saturated(t)]
    
    log_debug("topic_rotator", f"Generated {len(fresh)} fresh topics")
    return fresh


def generate_insight_based_topics() -> list:
    """Generate topics based on patterns in existing insights."""
    topics = []
    
    try:
        insights = get_insights(limit=10, min_novelty=6)
        
        for insight in insights:
            content = insight.get("content", "").lower()
            
            # Extract potential topic seeds from insights
            if "pain point" in content or "complaint" in content:
                # Find mentioned apps/categories
                import re
                apps = re.findall(r'(?:app|tool|software|platform)\s+(?:called\s+)?([A-Z][a-z]+)', insight.get("content", ""))
                for app in apps[:2]:
                    topics.append(f"{app} alternatives and gaps {datetime.now().strftime('%B %Y')}")
            
            if "opportunity" in content or "gap" in content:
                source_topics = insight.get("source_topics", [])
                if isinstance(source_topics, str):
                    import json
                    try:
                        source_topics = json.loads(source_topics)
                    except:
                        source_topics = []
                
                for st in source_topics[:2]:
                    topics.append(f"{st} implementation strategies")
        
        # Filter saturated
        fresh = [t for t in topics if not is_topic_saturated(t)]
        return fresh[:5]
        
    except Exception as e:
        log_debug("topic_rotator", f"Insight-based topics error: {e}")
        return []


def get_next_topic(exclude: list = None) -> str:
    """Get the next best topic to research."""
    exclude = exclude or []
    
    # Priority order:
    # 1. Fresh topics that haven't been researched recently
    # 2. Follow-up topics from high-scoring research
    # 3. Trending topics from HN
    # 4. Generated fresh topics
    
    # Try fresh topics first
    fresh = get_fresh_topics(days=3)
    for topic in fresh:
        if topic not in exclude and not is_topic_saturated(topic):
            return topic
    
    # Try follow-ups
    followups = generate_followup_topics()
    for topic in followups:
        if topic not in exclude:
            return topic
    
    # Try trending
    trending = get_trending_from_hackernews()
    for topic in trending:
        if topic not in exclude and not is_topic_saturated(topic):
            return topic
    
    # Fall back to fresh generated
    generated = generate_fresh_topics()
    for topic in generated:
        if topic not in exclude:
            return topic
    
    # Last resort: return any non-saturated topic
    return generated[0] if generated else "emerging app market gaps 2026"


def rotate_topics() -> bool:
    """
    Daily topic rotation:
    - Add fresh topics to the pool
    - Mark saturated topics
    - Clean up old topics
    """
    if not should_rotate():
        return False
    
    log_info("topic_rotator", "Starting daily topic rotation...")
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Ensure manager_state table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS manager_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        # Ensure research_topics table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS research_topics (
                topic TEXT PRIMARY KEY,
                added_at TEXT NOT NULL,
                priority INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        
        # Generate all types of topics
        fresh = generate_fresh_topics()
        followups = generate_followup_topics()
        trending = get_trending_from_hackernews()
        insight_based = generate_insight_based_topics()
        
        all_topics = []
        
        # Add with priorities
        for t in trending:
            all_topics.append((t, 3))  # Highest priority
        for t in followups:
            all_topics.append((t, 2))
        for t in insight_based:
            all_topics.append((t, 2))
        for t in fresh:
            all_topics.append((t, 1))
        
        # Insert topics
        added = 0
        for topic, priority in all_topics:
            try:
                cur.execute("""
                    INSERT INTO research_topics (topic, added_at, priority)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (topic) DO UPDATE SET priority = GREATEST(research_topics.priority, EXCLUDED.priority)
                """, (topic, datetime.now().isoformat(), priority))
                added += 1
            except:
                pass
        
        conn.commit()
        cur.close()
        conn.close()
        
        _set_last_rotation()
        
        log_info("topic_rotator", f"Rotation complete: added/updated {added} topics")
        return True
        
    except Exception as e:
        log_warn("topic_rotator", f"Rotation error: {e}")
        return False


def get_prioritized_topics(limit: int = 10) -> list:
    """Get topics sorted by priority (higher = more urgent)."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT topic FROM research_topics
            WHERE topic NOT IN (
                SELECT topic FROM topic_stats WHERE is_saturated = TRUE
            )
            ORDER BY priority DESC, added_at DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        log_debug("topic_rotator", f"get_prioritized_topics error: {e}")
        return generate_fresh_topics()[:limit]
