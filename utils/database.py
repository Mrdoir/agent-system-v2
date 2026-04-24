"""
PostgreSQL database for storing research results.
Uses Render's free PostgreSQL — survives forever, never resets.
"""

import psycopg2
import psycopg2.extras
import json
import os
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
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
    """)
    conn.commit()
    cur.close()
    conn.close()


def save_result(agent: str, topic: str, content: str, score: int = 0, tags: list = None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO results (agent, topic, content, score, tags, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
        (agent, topic, content, score, json.dumps(tags or []), datetime.now().isoformat())
    )
    conn.commit()
    cur.close()
    conn.close()


def get_results(limit: int = 50):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM results ORDER BY created_at DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def get_total_results():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM results")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count


def save_insight(content: str, source_topics: list, novelty_score: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO insights (content, source_topics, novelty_score, created_at) VALUES (%s, %s, %s, %s)",
        (content, json.dumps(source_topics), novelty_score, datetime.now().isoformat())
    )
    conn.commit()
    cur.close()
    conn.close()


def get_insights(limit: int = 20):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM insights ORDER BY novelty_score DESC, created_at DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def get_do_not_repeat():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT pattern FROM do_not_repeat")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r[0] for r in rows]


def add_do_not_repeat(pattern: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO do_not_repeat (pattern, created_at) VALUES (%s, %s) ON CONFLICT (pattern) DO NOTHING",
        (pattern, datetime.now().isoformat())
    )
    conn.commit()
    cur.close()
    conn.close()


def update_agent_status(agent: str, status: str, tasks_completed: int = None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO agent_status (agent, status, last_run, tasks_completed)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (agent) DO UPDATE SET
            status=EXCLUDED.status,
            last_run=EXCLUDED.last_run,
            tasks_completed=COALESCE(EXCLUDED.tasks_completed, agent_status.tasks_completed)
    """, (agent, status, datetime.now().isoformat(), tasks_completed))
    conn.commit()
    cur.close()
    conn.close()


def get_agent_statuses():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM agent_status")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {r["agent"]: dict(r) for r in rows}


def get_recent_topics(limit: int = 20):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT topic FROM results ORDER BY topic DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r[0] for r in rows]


def get_recent_contents(limit: int = 5):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT agent, topic, content FROM results ORDER BY created_at DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def save_critic_feedback(agent: str, topic: str, score: int,
                          strength: str, weakness: str, improvement: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO critic_feedback
           (agent, topic, score, strength, weakness, improvement, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (agent, topic, score, strength, weakness, improvement, datetime.now().isoformat())
    )
    conn.commit()
    cur.close()
    conn.close()


def get_critic_feedback_for_agent(agent: str, limit: int = 5) -> list:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM critic_feedback WHERE agent = %s ORDER BY created_at DESC LIMIT %s",
        (agent, limit)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def get_agent_average_score(agent: str) -> float:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT AVG(score) FROM critic_feedback WHERE agent = %s", (agent,))
    avg = cur.fetchone()[0]
    cur.close()
    conn.close()
    return round(float(avg or 0), 1)


# Initialize on import
init_db()
