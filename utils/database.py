"""
Persistent SQLite database for storing research results.
Survives redeploys because Railway persists the /data volume.
Falls back to local DB if volume not available.
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

DB_DIR = "/data" if os.path.exists("/data") else "data"
Path(DB_DIR).mkdir(exist_ok=True)
DB_PATH = "/opt/render/project/src/research.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent TEXT NOT NULL,
            topic TEXT NOT NULL,
            content TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            tags TEXT DEFAULT '[]',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            source_topics TEXT DEFAULT '[]',
            novelty_score INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS do_not_repeat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT NOT NULL,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    conn.close()


def save_result(agent: str, topic: str, content: str, score: int = 0, tags: list = None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO results (agent, topic, content, score, tags, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (agent, topic, content, score, json.dumps(tags or []), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_results(limit: int = 50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM results ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_total_results():
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    conn.close()
    return count


def save_insight(content: str, source_topics: list, novelty_score: int):
    conn = get_conn()
    conn.execute(
        "INSERT INTO insights (content, source_topics, novelty_score, created_at) VALUES (?, ?, ?, ?)",
        (content, json.dumps(source_topics), novelty_score, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_insights(limit: int = 20):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM insights ORDER BY novelty_score DESC, created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_do_not_repeat():
    conn = get_conn()
    rows = conn.execute("SELECT pattern FROM do_not_repeat").fetchall()
    conn.close()
    return [r["pattern"] for r in rows]


def add_do_not_repeat(pattern: str):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO do_not_repeat (pattern, created_at) VALUES (?, ?)",
        (pattern, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def update_agent_status(agent: str, status: str, tasks_completed: int = None):
    conn = get_conn()
    conn.execute("""
        INSERT INTO agent_status (agent, status, last_run, tasks_completed)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(agent) DO UPDATE SET
            status=excluded.status,
            last_run=excluded.last_run,
            tasks_completed=COALESCE(excluded.tasks_completed, agent_status.tasks_completed)
    """, (agent, status, datetime.now().isoformat(), tasks_completed))
    conn.commit()
    conn.close()


def get_agent_statuses():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM agent_status").fetchall()
    conn.close()
    return {r["agent"]: dict(r) for r in rows}


def get_recent_topics(limit: int = 20):
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT topic FROM results ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [r["topic"] for r in rows]


def get_recent_contents(limit: int = 5):
    conn = get_conn()
    rows = conn.execute(
        "SELECT agent, topic, content FROM results ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_critic_feedback(agent: str, topic: str, score: int,
                          strength: str, weakness: str, improvement: str):
    """Save critic feedback per agent so they can learn from it."""
    conn = get_conn()
    conn.execute(
        """INSERT INTO critic_feedback
           (agent, topic, score, strength, weakness, improvement, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (agent, topic, score, strength, weakness, improvement,
         datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_critic_feedback_for_agent(agent: str, limit: int = 5) -> list:
    """Get the last N critic feedback entries for a specific agent."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM critic_feedback
           WHERE agent = ?
           ORDER BY created_at DESC LIMIT ?""",
        (agent, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_agent_average_score(agent: str) -> float:
    """Get average critic score for an agent."""
    conn = get_conn()
    row = conn.execute(
        "SELECT AVG(score) as avg FROM critic_feedback WHERE agent = ?",
        (agent,)
    ).fetchone()
    conn.close()
    return round(row["avg"] or 0, 1)


# Initialize on import
init_db()
