"""
BASE AGENT v4 — Uses Global Provider Pool
==========================================
MAJOR CHANGE: Agents no longer manage their own API keys or fallback chains.
Instead, they declare their preferred providers and call the global pool.

The pool handles:
- Key selection (least-used first)
- Rate limit tracking (per-key, not per-agent)
- Fallback routing (automatic)
- Usage spreading (across all your keys)

This is the core of the rate limit fix.
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
    
    def __init__(self):
        self._current_provider = None
    
    # ═══════════════════════════════════════════════════════════════
    # THE KEY METHOD — replaces all the old call_api / fallback logic
    # ═══════════════════════════════════════════════════════════════
    
    def call_api(self, prompt: str, max_tokens: int = 1500, 
                 temperature: float = 0.7) -> dict:
        """
        Call the LLM via the global provider pool.
        The pool picks the best available key automatically.
        
        Returns: {"success": bool, "text": str|None, "provider": str, ...}
        """
        result = pool.call_llm(
            prompt=prompt,
            system_msg=self.SYSTEM_MSG,
            preferred_providers=self.PREFERRED_PROVIDERS,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=60,
            caller=self.NAME
        )
        
        if result["success"]:
            self._current_provider = result.get("key_id")
            log_api_call(self.NAME, result.get("key_id", "unknown"), True)
        else:
            if result.get("all_exhausted"):
                log_warn(self.NAME, "All providers exhausted")
            else:
                log_api_call(self.NAME, "pool", False, 
                    f"({result.get('error', 'unknown')})")
        
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # DATABASE OPERATIONS (unchanged from v3)
    # ═══════════════════════════════════════════════════════════════
    
    def save_to_db(self, topic: str, content: str, score: int = 0, 
                   tags: list = None) -> int:
        """Save research result to database."""
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
