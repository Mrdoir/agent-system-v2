"""
BASE AGENT - Shared logic for all research agents.
Handles rate limit tracking, file saving, API calls.
Now saves to persistent SQLite database.
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from utils.logger import log
from utils.database import save_result, update_agent_status


class BaseAgent:
    NAME = "base_agent"
    PROVIDER = "unknown"
    RATE_LIMIT_FILE = "state/rate_limits.json"

    def __init__(self):
        Path("state").mkdir(exist_ok=True)
        self._load_rate_limit_state()

    def _load_rate_limit_state(self):
        if Path(self.RATE_LIMIT_FILE).exists():
            with open(self.RATE_LIMIT_FILE) as f:
                self._rl_state = json.load(f)
        else:
            self._rl_state = {}

    def _save_rate_limit_state(self):
        with open(self.RATE_LIMIT_FILE, "w") as f:
            json.dump(self._rl_state, f, indent=2)

    def set_rate_limited(self, reset_minutes=60):
        reset_at = (datetime.now() + timedelta(minutes=reset_minutes)).isoformat()
        self._rl_state[self.NAME] = {"limited": True, "reset_at": reset_at}
        self._save_rate_limit_state()
        update_agent_status(self.NAME, "rate_limited")
        log(self.NAME, f"Rate limited. Will auto-resume at {reset_at}")

    def clear_rate_limit(self):
        if self.NAME in self._rl_state:
            del self._rl_state[self.NAME]
            self._save_rate_limit_state()

    def is_rate_limited(self):
        self._load_rate_limit_state()
        entry = self._rl_state.get(self.NAME)
        if not entry:
            return False
        reset_at = datetime.fromisoformat(entry["reset_at"])
        if datetime.now() >= reset_at:
            self.clear_rate_limit()
            update_agent_status(self.NAME, "active")
            log(self.NAME, "Rate limit reset. Back online ✓")
            return False
        return True

    def minutes_until_reset(self):
        entry = self._rl_state.get(self.NAME)
        if not entry:
            return 0
        reset_at = datetime.fromisoformat(entry["reset_at"])
        delta = reset_at - datetime.now()
        return max(0, int(delta.total_seconds() / 60))

    def save_to_db(self, topic: str, content: str, score: int = 0) -> str:
        save_result(self.NAME, topic, content, score)
        update_agent_status(self.NAME, "active")
        return f"db:{self.NAME}:{topic}"

    def call_api(self, prompt: str) -> dict:
        raise NotImplementedError

    def build_prompt(self, topic: str) -> str:
        raise NotImplementedError

    def research(self, topic: str) -> dict:
        prompt = self.build_prompt(topic)
        result = self.call_api(prompt)

        if result.get("rate_limited"):
            self.set_rate_limited()
            return {"success": False, "rate_limited": True}

        if not result["success"]:
            update_agent_status(self.NAME, "error")
            return {"success": False, "error": result.get("error", "Unknown error")}

        self.save_to_db(topic, result["text"])
        return {"success": True, "content": result["text"], "file": f"db:{self.NAME}"}
