"""
DATABASE v3 — PostgreSQL with connection pooling and analytics
Improvements:
- Simple connection pooling (reuse connections)
- Topic saturation detection
- Analytics queries for dashboard
- Full-text search support
- Agent performance tracking
- Better error handling with retries
"""

import os
import json
import time
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from contextlib import contextmanager
from utils.logger import log_debug, log_error

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Simple connection pool
_connection_pool = []
_pool_size = 3


def get_conn():
    """Get a database connection (with simple pooling)."""
    global _connection_pool
    
    # Try to reuse an existing connection
    while _connection_pool:
        conn = _connection_pool.pop()
        try:
            # Test if connection is still alive
            conn.cursor().execute("SELECT 1")
            return conn
        except:
            try:
                conn.close()
            except:
                pass
    
    # Create new connection
    return psycopg2.connect(DATABASE_URL)


def return_conn(conn):
    """Return connection to pool for reuse."""
    global _connection_pool
    if len(_connection_pool) < _pool_size:
        try:
            conn.rollback()  # Clear any pending transaction
            _connection_pool.append(conn)
        except:
            try:
                conn.close()
            except:
                pass
    else:
        try:
            conn.close()
        except:
            pass


@contextmanager
def db_connection():
    """Context manager for database connections."""
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        return_conn(conn)


def init_db():
    """Create all tables if they don't exist, and migrate existing tables."""
    with db_connection() as conn:
        cur = conn.cursor()
        
        # ── Create tables ────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id SERIAL PRIMARY KEY,
                agent TEXT NOT NULL,
                topic TEXT NOT NULL,
                content TEXT NOT NULL,
                score INTEGER DEFAULT 0,
                tags TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS insights (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                source_topics TEXT DEFAULT '[]',
                novelty_score INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS do_not_repeat (
                id SERIAL PRIMARY KEY,
                pattern TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS agent_status (
                agent TEXT PRIMARY KEY,
                status TEXT DEFAULT 'active',
                tasks_completed INTEGER DEFAULT 0,
                last_run TEXT,
                rate_limit_until TEXT
            );

            CREATE TABLE IF NOT EXISTS critic_feedback (
                id SERIAL PRIMARY KEY,
                agent TEXT NOT NULL,
                topic TEXT NOT NULL,
                score INTEGER DEFAULT 0,
                strength TEXT DEFAULT '',
                weakness TEXT DEFAULT '',
                improvement TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS topic_stats (
                topic TEXT PRIMARY KEY,
                research_count INTEGER DEFAULT 0,
                total_score INTEGER DEFAULT 0,
                avg_score FLOAT DEFAULT 0,
                last_researched TEXT,
                is_saturated BOOLEAN DEFAULT FALSE
            );

            CREATE INDEX IF NOT EXISTS idx_results_agent ON results(agent);
            CREATE INDEX IF NOT EXISTS idx_results_topic ON results(topic);
            CREATE INDEX IF NOT EXISTS idx_results_score ON results(score DESC);
            CREATE INDEX IF NOT EXISTS idx_results_created ON results(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_insights_novelty ON insights(novelty_score DESC);
        """)
        
        # ── Migrate: add new columns to existing tables safely ───
        migrations = [
            ("agent_status", "tasks_failed", "INTEGER DEFAULT 0"),
            ("agent_status", "total_score", "INTEGER DEFAULT 0"),
            ("agent_status", "current_provider", "TEXT"),
        ]
        for table, column, col_type in migrations:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            except Exception:
                conn.rollback()  # Column already exists, ignore
        
        cur.close()


# ═══════════════════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════════════════

def save_result(agent: str, topic: str, content: str, score: int = 0, tags: list = None):
    """Save a research result and update topic stats."""
    with db_connection() as conn:
        cur = conn.cursor()
        
        # Save the result
        cur.execute(
            """INSERT INTO results (agent, topic, content, score, tags, created_at) 
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
            (agent, topic, content, score, json.dumps(tags or []), datetime.now().isoformat())
        )
        result_id = cur.fetchone()[0]
        
        # Update topic stats
        cur.execute("""
            INSERT INTO topic_stats (topic, research_count, total_score, avg_score, last_researched)
            VALUES (%s, 1, %s, %s, %s)
            ON CONFLICT (topic) DO UPDATE SET
                research_count = topic_stats.research_count + 1,
                total_score = topic_stats.total_score + EXCLUDED.total_score,
                avg_score = (topic_stats.total_score + EXCLUDED.total_score)::float / (topic_stats.research_count + 1),
                last_researched = EXCLUDED.last_researched
        """, (topic, score, float(score), datetime.now().isoformat()))
        
        cur.close()
        return result_id


def get_results(limit: int = 50, min_score: int = None, agent: str = None):
    """Get results with optional filtering."""
    with db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = "SELECT id, agent, topic, content, score, created_at FROM results WHERE 1=1"
        params = []
        
        if min_score is not None:
            query += " AND score >= %s"
            params.append(min_score)
        
        if agent:
            query += " AND agent = %s"
            params.append(agent)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]


def get_total_results():
    """Get total count of results."""
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM results")
        count = cur.fetchone()[0]
        cur.close()
        return count


def search_results(query: str, limit: int = 30):
    """Full-text search across results."""
    with db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id, agent, topic, content, score, created_at
            FROM results
            WHERE content ILIKE %s OR topic ILIKE %s
            ORDER BY score DESC, created_at DESC
            LIMIT %s
        """, (f"%{query}%", f"%{query}%", limit))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════
# INSIGHTS
# ═══════════════════════════════════════════════════════════════════

def save_insight(content: str, source_topics: list, novelty_score: int):
    """Save a synthesized insight."""
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO insights (content, source_topics, novelty_score, created_at) 
               VALUES (%s, %s, %s, %s)""",
            (content, json.dumps(source_topics), novelty_score, datetime.now().isoformat())
        )
        cur.close()


def get_insights(limit: int = 20, min_novelty: int = None):
    """Get insights with optional novelty filter."""
    with db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        if min_novelty:
            cur.execute("""
                SELECT * FROM insights 
                WHERE novelty_score >= %s
                ORDER BY novelty_score DESC, created_at DESC 
                LIMIT %s
            """, (min_novelty, limit))
        else:
            cur.execute("""
                SELECT * FROM insights 
                ORDER BY novelty_score DESC, created_at DESC 
                LIMIT %s
            """, (limit,))
        
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════
# DO NOT REPEAT (learned patterns to avoid)
# ═══════════════════════════════════════════════════════════════════

def get_do_not_repeat():
    """Get patterns that should not be repeated."""
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT pattern FROM do_not_repeat ORDER BY created_at DESC LIMIT 100")
        rows = cur.fetchall()
        cur.close()
        return [r[0] for r in rows]


def add_do_not_repeat(pattern: str):
    """Add a pattern to avoid."""
    if len(pattern) < 10:  # Skip too-short patterns
        return
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO do_not_repeat (pattern, created_at) 
               VALUES (%s, %s) ON CONFLICT (pattern) DO NOTHING""",
            (pattern, datetime.now().isoformat())
        )
        cur.close()


# ═══════════════════════════════════════════════════════════════════
# AGENT STATUS
# ═══════════════════════════════════════════════════════════════════

def update_agent_status(agent: str, status: str, tasks_completed: int = None, 
                        tasks_failed: int = None, score: int = None, provider: str = None):
    """Update agent status with optional metrics. Safe for old and new DB schemas."""
    with db_connection() as conn:
        cur = conn.cursor()
        now = datetime.now().isoformat()
        
        try:
            # Try the simple safe path first (works with old schema)
            cur.execute("""
                INSERT INTO agent_status (agent, status, last_run, tasks_completed)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (agent) DO UPDATE SET
                    status = EXCLUDED.status,
                    last_run = EXCLUDED.last_run,
                    tasks_completed = COALESCE(agent_status.tasks_completed, 0) + 1
            """, (agent, status, now, tasks_completed or 0))
        except Exception as e:
            conn.rollback()
            # Absolute fallback — just update status
            try:
                cur.execute("""
                    INSERT INTO agent_status (agent, status, last_run)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (agent) DO UPDATE SET
                        status = EXCLUDED.status,
                        last_run = EXCLUDED.last_run
                """, (agent, status, now))
            except Exception:
                conn.rollback()
        
        # Try updating new columns separately (won't crash if they don't exist)
        if score is not None:
            try:
                cur.execute("""
                    UPDATE agent_status 
                    SET total_score = COALESCE(total_score, 0) + %s 
                    WHERE agent = %s
                """, (score, agent))
            except Exception:
                conn.rollback()
        
        if provider:
            try:
                cur.execute("""
                    UPDATE agent_status SET current_provider = %s WHERE agent = %s
                """, (provider, agent))
            except Exception:
                conn.rollback()
        
        if tasks_failed is not None:
            try:
                cur.execute("""
                    UPDATE agent_status 
                    SET tasks_failed = COALESCE(tasks_failed, 0) + 1 
                    WHERE agent = %s
                """, (agent,))
            except Exception:
                conn.rollback()
        
        cur.close()


def set_agent_rate_limited(agent: str, reset_minutes: int = 60):
    """Mark agent as rate limited."""
    reset_at = (datetime.now() + timedelta(minutes=reset_minutes)).isoformat()
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO agent_status (agent, status, rate_limit_until, last_run)
            VALUES (%s, 'rate_limited', %s, %s)
            ON CONFLICT (agent) DO UPDATE SET
                status = 'rate_limited',
                rate_limit_until = EXCLUDED.rate_limit_until,
                last_run = EXCLUDED.last_run
        """, (agent, reset_at, datetime.now().isoformat()))
        cur.close()


def clear_agent_rate_limit(agent: str):
    """Clear rate limit for agent."""
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE agent_status 
            SET status = 'active', rate_limit_until = NULL
            WHERE agent = %s
        """, (agent,))
        cur.close()


def is_agent_rate_limited(agent: str) -> bool:
    """Check if agent is currently rate limited."""
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT status, rate_limit_until FROM agent_status WHERE agent = %s",
            (agent,)
        )
        row = cur.fetchone()
        cur.close()
        
        if not row:
            return False
        
        status, reset_at = row
        if status != "rate_limited" or not reset_at:
            return False
        
        # Check if rate limit has expired
        if datetime.now() >= datetime.fromisoformat(reset_at):
            clear_agent_rate_limit(agent)
            return False
        
        return True


def get_agent_statuses():
    """Get all agent statuses."""
    with db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM agent_status")
        rows = cur.fetchall()
        cur.close()
        return {r["agent"]: dict(r) for r in rows}


def get_agent_stats(agent: str) -> dict:
    """Get detailed stats for an agent."""
    with db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT 
                COUNT(*) as total_results,
                AVG(score) as avg_score,
                MAX(score) as best_score,
                COUNT(CASE WHEN score >= 7 THEN 1 END) as high_quality_count
            FROM results WHERE agent = %s
        """, (agent,))
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else {}


# ═══════════════════════════════════════════════════════════════════
# CRITIC FEEDBACK
# ═══════════════════════════════════════════════════════════════════

def save_critic_feedback(agent: str, topic: str, score: int,
                         strength: str, weakness: str, improvement: str):
    """Save critic feedback for an agent."""
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO critic_feedback (agent, topic, score, strength, weakness, improvement, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (agent, topic, score, strength, weakness, improvement, datetime.now().isoformat()))
        cur.close()


def get_critic_feedback_for_agent(agent: str, limit: int = 5) -> list:
    """Get recent critic feedback for an agent."""
    with db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT * FROM critic_feedback 
            WHERE agent = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        """, (agent, limit))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]


def get_agent_average_score(agent: str) -> float:
    """Get average critic score for an agent."""
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT AVG(score) FROM critic_feedback WHERE agent = %s", (agent,))
        avg = cur.fetchone()[0]
        cur.close()
        return round(float(avg or 0), 1)


def get_common_weaknesses(agent: str, limit: int = 3) -> list:
    """Get most common weaknesses for an agent."""
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT weakness, COUNT(*) as cnt
            FROM critic_feedback
            WHERE agent = %s AND weakness != ''
            GROUP BY weakness
            ORDER BY cnt DESC
            LIMIT %s
        """, (agent, limit))
        rows = cur.fetchall()
        cur.close()
        return [r[0] for r in rows]


# ═══════════════════════════════════════════════════════════════════
# TOPIC SATURATION
# ═══════════════════════════════════════════════════════════════════

def is_topic_saturated(topic: str, max_count: int = 5, min_avg_score: float = 6.0) -> bool:
    """
    Check if a topic has been over-researched with diminishing returns.
    Saturated = researched many times but scores are declining/low.
    """
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT research_count, avg_score, is_saturated
            FROM topic_stats
            WHERE topic = %s
        """, (topic,))
        row = cur.fetchone()
        cur.close()
        
        if not row:
            return False
        
        count, avg_score, is_saturated = row
        
        # Already marked saturated
        if is_saturated:
            return True
        
        # Check if saturated: many researches but low average score
        if count >= max_count and (avg_score or 0) < min_avg_score:
            mark_topic_saturated(topic)
            return True
        
        return False


def mark_topic_saturated(topic: str):
    """Mark a topic as saturated."""
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE topic_stats SET is_saturated = TRUE WHERE topic = %s",
            (topic,)
        )
        cur.close()


def get_topic_stats(limit: int = 50) -> list:
    """Get topic statistics for analytics."""
    with db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT topic, research_count, avg_score, last_researched, is_saturated
            FROM topic_stats
            ORDER BY research_count DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]


def get_fresh_topics(days: int = 7) -> list:
    """Get topics that haven't been researched recently."""
    with db_connection() as conn:
        cur = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cur.execute("""
            SELECT topic FROM topic_stats
            WHERE (last_researched < %s OR last_researched IS NULL)
              AND is_saturated = FALSE
            ORDER BY avg_score DESC NULLS LAST
            LIMIT 20
        """, (cutoff,))
        rows = cur.fetchall()
        cur.close()
        return [r[0] for r in rows]


# ═══════════════════════════════════════════════════════════════════
# ANALYTICS
# ═══════════════════════════════════════════════════════════════════

def get_analytics_summary() -> dict:
    """Get analytics summary for dashboard."""
    with db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Overall stats
        cur.execute("""
            SELECT 
                COUNT(*) as total_results,
                AVG(score) as avg_score,
                COUNT(CASE WHEN score >= 7 THEN 1 END) as high_quality,
                COUNT(DISTINCT topic) as unique_topics,
                COUNT(DISTINCT agent) as active_agents
            FROM results
        """)
        overall = dict(cur.fetchone())
        
        # Per-agent stats
        cur.execute("""
            SELECT agent, COUNT(*) as count, AVG(score) as avg_score
            FROM results
            GROUP BY agent
        """)
        agents = {r["agent"]: {"count": r["count"], "avg_score": round(r["avg_score"] or 0, 1)} 
                  for r in cur.fetchall()}
        
        # Recent activity (last 24h)
        cur.execute("""
            SELECT COUNT(*) as last_24h
            FROM results
            WHERE created_at > %s
        """, ((datetime.now() - timedelta(hours=24)).isoformat(),))
        recent = cur.fetchone()["last_24h"]
        
        # Top topics
        cur.execute("""
            SELECT topic, COUNT(*) as count, AVG(score) as avg_score
            FROM results
            GROUP BY topic
            ORDER BY count DESC
            LIMIT 10
        """)
        top_topics = [dict(r) for r in cur.fetchall()]
        
        cur.close()
        
        return {
            "overall": overall,
            "agents": agents,
            "last_24h": recent,
            "top_topics": top_topics
        }


def get_score_trends(days: int = 30) -> list:
    """Get daily score trends."""
    with db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT 
                DATE(created_at) as date,
                agent,
                AVG(score) as avg_score,
                COUNT(*) as count
            FROM results
            WHERE created_at > %s
            GROUP BY DATE(created_at), agent
            ORDER BY date
        """, ((datetime.now() - timedelta(days=days)).isoformat(),))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]


def get_recent_contents(limit: int = 5):
    """Get recent research content for context."""
    with db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT agent, topic, content 
            FROM results 
            ORDER BY created_at DESC 
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]


def get_recent_topics(limit: int = 20):
    """Get recently researched topics."""
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT topic 
            FROM results 
            ORDER BY topic DESC 
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        cur.close()
        return [r[0] for r in rows]


# Initialize database on import
try:
    init_db()
except Exception as e:
    log_error("database", f"Failed to initialize database: {e}")
