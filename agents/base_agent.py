"""
BASE AGENT v5 — Uses Global Provider Pool
==========================================
Agents declare their preferred providers and call the global pool.
The pool handles key selection, rate limits, fallbacks and (new in v5)
rejects junk outputs.

Changes vs v4:
- call_api() asks the pool for at least MIN_CHARS characters, so empty /
  one-line / safety-classifier replies are retried on another provider
  instead of being saved as research.
- Every saved row is tagged with the provider and the model that actually
  produced it (e.g. ["provider:openrouter-2", "model:some/model:free"]),
  so bad models can be found from the data later.
"""

import time
from datetime import datetime
from utils.logger import (
    log_info, log_warn, log_error, log_debug,
    log_api_call, log_rate_limit
)
from utils.database import (
    save_result, update_agent_status, get_conn
)
from utils.provider_pool import pool


class BaseAgent:
    NAME = "base_agent"

    # Override in subclasses — ordered by preference
    PREFERRED_PROVIDERS = ["gemini", "groq", "openrouter", "cerebras", "together", "cohere"]

    # Override in subclasses — system message for LLM
    SYSTEM_MSG = ""

    # Research outputs shorter than this are treated as failures and retried
    MIN_CHARS = 300

    def __init__(self):
        self._current_provider = None
        self._current_model = None

    def call_api(self, prompt: str, max_tokens: int = 1500,
                 temperature: float = 0.7, min_chars: int = None) -> dict:
        """
        Call the LLM via the global provider pool.
        Returns: {"success": bool, "text": str|None, "provider": str, ...}
        """
        result = pool.call_llm(
            prompt=prompt,
            system_msg=self.SYSTEM_MSG,
            preferred_providers=self.PREFERRED_PROVIDERS,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=60,
            caller=self.NAME,
            min_chars=self.MIN_CHARS if min_chars is None else min_chars
        )

        if result["success"]:
            self._current_provider = result.get("key_id")
            self._current_model = result.get("model_used") or result.get("model")
            log_api_call(self.NAME, result.get("key_id", "unknown"), True)
        else:
            if result.get("all_exhausted"):
                log_warn(self.NAME, "All providers exhausted")
            else:
                log_api_call(self.NAME, "pool", False,
                    f"({result.get('error', 'unknown')})")

        return result

    def save_to_db(self, topic: str, content: str, score: int = 0,
                   tags: list = None) -> int:
        """Save research result to database (tagged with provider + model)."""
        if tags is None:
            tags = []
            if self._current_provider:
                tags.append(f"provider:{self._current_provider}")
            if self._current_model:
                tags.append(f"model:{self._current_model}")

        result_id = save_result(self.NAME, topic, content, score, tags)
        update_agent_status(
            self.NAME,
            status="active",
            tasks_completed=1,
            score=score,
            provider=self._current_provider
        )
        log_debug(self.NAME, f"Saved result #{result_id}")
        return result_id
