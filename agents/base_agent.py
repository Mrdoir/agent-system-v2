"""
BASE AGENT v2 — rate limit state stored in Postgres (not state/rate_limits.json)
Survives Render restarts. Everything else identical to original.
"""

import os
from datetime import datetime, timedelta
from utils.logger import log
from utils.database import save_result, update_agent_status, get_conn


class BaseAgent:
    NAME = "base_agent"
    PROVIDER = "unknown"

    def __init__(self):
        pass  # No more JSON file setup needed

    # ── RATE LIMIT (Postgres) ─────────────────────────────────────

    def set_rate_limited(self, reset_minutes=60):
        reset_at = (datetime.now() + timedelta(minutes=reset_minutes)).isoformat()
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO agent_status (agent, status, rate_limit_until, last_run)
                VALUES (%s, 'rate_limited', %s, %s)
                ON CONFLICT (agent) DO UPDATE SET
                    status = 'rate_limited',
                    rate_limit_until = EXCLUDED.rate_limit_until
            """, (self.NAME, reset_at, datetime.now().isoformat()))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            log(self.NAME, f"set_rate_limited DB error: {e}")
        log(self.NAME, f"Rate limited. Will auto-resume at {reset_at}")

    def clear_rate_limit(self):
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""
                UPDATE agent_status SET status = 'active', rate_limit_until = NULL
                WHERE agent = %s
            """, (self.NAME,))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            log(self.NAME, f"clear_rate_limit DB error: {e}")

    def is_rate_limited(self) -> bool:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT status, rate_limit_until FROM agent_status WHERE agent = %s",
                (self.NAME,)
            )
            row = cur.fetchone()
            cur.close()
            conn.close()

            if not row:
                return False
            status, reset_at = row
            if status != "rate_limited" or not reset_at:
                return False

            if datetime.now() >= datetime.fromisoformat(reset_at):
                self.clear_rate_limit()
                update_agent_status(self.NAME, "active")
                log(self.NAME, "Rate limit reset. Back online ✓")
                return False
            return True
        except Exception as e:
            log(self.NAME, f"is_rate_limited DB error: {e}")
            return False  # Don't block agents on DB errors

    def minutes_until_reset(self) -> int:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT rate_limit_until FROM agent_status WHERE agent = %s",
                (self.NAME,)
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            if not row or not row[0]:
                return 0
            delta = datetime.fromisoformat(row[0]) - datetime.now()
            return max(0, int(delta.total_seconds() / 60))
        except:
            return 0

    # ── SAVE / API ────────────────────────────────────────────────

    def save_to_db(self, topic: str, content: str, score: int = 0) -> str:
        save_result(self.NAME, topic, content, score)
        update_agent_status(self.NAME, "active")
        return f"db:{self.NAME}:{topic}"

    def call_api(self, prompt: str) -> dict:
        raise NotImplementedError

    def build_prompt(self, topic: str, agent_name: str = None) -> str:
        raise NotImplementedError

    def research(self, topic: str) -> dict:
        prompt = self.build_prompt(topic, agent_name=self.NAME)
        result = self.call_api(prompt)
        if result.get("rate_limited"):
            self.set_rate_limited()
            return {"success": False, "rate_limited": True}
        if not result["success"]:
            update_agent_status(self.NAME, "error")
            return {"success": False, "error": result.get("error", "Unknown error")}
        self.save_to_db(topic, result["text"])
        return {"success": True, "content": result["text"], "file": f"db:{self.NAME}"}
