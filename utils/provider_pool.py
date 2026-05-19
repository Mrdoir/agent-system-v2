"""
PROVIDER POOL v1 — Global API key management across all agents
===============================================================
THE CORE FIX for rate limiting. Instead of each agent owning its own
keys and burning through them independently, this pool:

1. Tracks every key's usage across ALL agents
2. Routes requests to least-used provider
3. Respects per-key rate limits with precise cooldowns
4. Spreads load via round-robin with usage awareness
5. Thread-safe for concurrent agent execution

Your keys (from .env):
- 3 OpenRouter keys
- 2 Groq keys  
- 1 Cerebras key
- 1 Together key (if set)
- 1 Gemini key
- 1 Cohere key
"""

import os
import time
import threading
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from utils.logger import log_info, log_warn, log_debug, log_error


# ═══════════════════════════════════════════════════════════════════
# PROVIDER DEFINITIONS — rate limits per free tier
# ═══════════════════════════════════════════════════════════════════

PROVIDER_LIMITS = {
    "gemini":      {"rpm": 15, "rpd": 1500, "cooldown_minutes": 1},
    "groq":        {"rpm": 30, "rpd": 14400, "cooldown_minutes": 1},
    "openrouter":  {"rpm": 20, "rpd": 200, "cooldown_minutes": 3},
    "cerebras":    {"rpm": 30, "rpd": 14400, "cooldown_minutes": 1},
    "together":    {"rpm": 60, "rpd": 1000, "cooldown_minutes": 1},
    "cohere":      {"rpm": 5, "rpd": 5000, "cooldown_minutes": 2},
}


class ProviderKey:
    """Represents a single API key with usage tracking."""
    
    def __init__(self, provider: str, key: str, key_id: str, endpoint: str, 
                 model: str, rpm: int = 30, rpd: int = 1000, cooldown_minutes: int = 1):
        self.provider = provider
        self.key = key
        self.key_id = key_id
        self.endpoint = endpoint
        self.model = model
        self.rpm = rpm
        self.rpd = rpd
        self.cooldown_minutes = cooldown_minutes
        
        # Usage tracking
        self.calls_this_minute = 0
        self.calls_this_hour = 0
        self.calls_today = 0
        self.minute_reset = time.time() + 60
        self.hour_reset = time.time() + 3600
        self.day_reset = time.time() + 86400
        
        # Rate limit tracking
        self.rate_limited_until = 0
        self.consecutive_failures = 0
        self.last_success = 0
        self.last_used = 0
        self.total_calls = 0
        self.total_successes = 0
    
    def is_available(self) -> bool:
        """Check if this key can accept a request right now."""
        now = time.time()
        
        # Reset counters if windows expired
        if now >= self.minute_reset:
            self.calls_this_minute = 0
            self.minute_reset = now + 60
        if now >= self.hour_reset:
            self.calls_this_hour = 0
            self.hour_reset = now + 3600
        if now >= self.day_reset:
            self.calls_today = 0
            self.day_reset = now + 86400
        
        # Check rate limit
        if now < self.rate_limited_until:
            return False
        
        # Check per-minute limit (use 80% threshold for safety)
        if self.calls_this_minute >= int(self.rpm * 0.8):
            return False
        
        # Check daily limit (use 90% threshold)
        if self.calls_today >= int(self.rpd * 0.9):
            return False
        
        return True
    
    def record_call(self):
        """Record that we made a call with this key."""
        now = time.time()
        self.calls_this_minute += 1
        self.calls_this_hour += 1
        self.calls_today += 1
        self.total_calls += 1
        self.last_used = now
    
    def record_success(self):
        """Record successful response."""
        self.consecutive_failures = 0
        self.total_successes += 1
        self.last_success = time.time()
    
    def record_failure(self, is_rate_limit: bool = False):
        """Record failed response."""
        self.consecutive_failures += 1
        if is_rate_limit:
            cooldown = self.cooldown_minutes * 60
            if self.consecutive_failures > 2:
                cooldown *= min(self.consecutive_failures - 1, 4)
            self.rate_limited_until = time.time() + cooldown
            log_debug("provider_pool", 
                f"{self.key_id} rate limited for {cooldown}s "
                f"(failures: {self.consecutive_failures})")
    
    def time_until_available(self) -> int:
        """Seconds until this key becomes available."""
        now = time.time()
        if now >= self.rate_limited_until:
            if self.calls_this_minute >= int(self.rpm * 0.8):
                return max(0, int(self.minute_reset - now))
            return 0
        return max(0, int(self.rate_limited_until - now))
    
    @property
    def usage_score(self) -> float:
        """Lower = less used = preferred. Used for smart routing."""
        now = time.time()
        recency_penalty = max(0, 60 - (now - self.last_used)) / 60
        minute_usage = self.calls_this_minute / max(self.rpm, 1)
        daily_usage = self.calls_today / max(self.rpd, 1)
        failure_penalty = min(self.consecutive_failures * 0.2, 1.0)
        return minute_usage + daily_usage + recency_penalty + failure_penalty


class ProviderPool:
    """
    Global pool of all API provider keys.
    Thread-safe. Shared across all agents.
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._keys = []
        self._initialized = False
    
    def initialize(self):
        """Load all API keys from environment and register them."""
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            # ── GEMINI ─────────────────────────────────────────────
            gemini_key = os.getenv("GEMINI_API_KEY", "")
            if gemini_key:
                self._keys.append(ProviderKey(
                    provider="gemini", key=gemini_key, key_id="gemini-1",
                    endpoint="https://generativelanguage.googleapis.com",
                    model="gemini-2.0-flash",
                    **PROVIDER_LIMITS["gemini"]
                ))
            
            # ── GROQ (2 keys) ──────────────────────────────────────
            for i, env_var in enumerate(["GROQ_API_KEY", "GROQ_API_KEY_2"], 1):
                key = os.getenv(env_var, "")
                if key:
                    self._keys.append(ProviderKey(
                        provider="groq", key=key, key_id=f"groq-{i}",
                        endpoint="https://api.groq.com/openai/v1/chat/completions",
                        model="llama-3.3-70b-versatile",
                        **PROVIDER_LIMITS["groq"]
                    ))
            
            # ── OPENROUTER (3 keys) ────────────────────────────────
            for i, env_var in enumerate(["OPENROUTER_API_KEY", "OPENROUTER_API_KEY_2", "OPENROUTER_API_KEY_3"], 1):
                key = os.getenv(env_var, "")
                if key:
                    self._keys.append(ProviderKey(
                        provider="openrouter", key=key, key_id=f"openrouter-{i}",
                        endpoint="https://openrouter.ai/api/v1/chat/completions",
                        model="deepseek/deepseek-r1:free",
                        **PROVIDER_LIMITS["openrouter"]
                    ))
            
            # ── CEREBRAS ───────────────────────────────────────────
            cerebras_key = os.getenv("CEREBRAS_API_KEY", "")
            if cerebras_key:
                self._keys.append(ProviderKey(
                    provider="cerebras", key=cerebras_key, key_id="cerebras-1",
                    endpoint="https://api.cerebras.ai/v1/chat/completions",
                    model="llama-3.3-70b",
                    **PROVIDER_LIMITS["cerebras"]
                ))
            
            # ── TOGETHER ───────────────────────────────────────────
            together_key = os.getenv("TOGETHER_API_KEY", "")
            if together_key:
                self._keys.append(ProviderKey(
                    provider="together", key=together_key, key_id="together-1",
                    endpoint="https://api.together.xyz/v1/chat/completions",
                    model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
                    **PROVIDER_LIMITS["together"]
                ))
            
            # ── COHERE ─────────────────────────────────────────────
            cohere_key = os.getenv("COHERE_API_KEY", "")
            if cohere_key:
                self._keys.append(ProviderKey(
                    provider="cohere", key=cohere_key, key_id="cohere-1",
                    endpoint="https://api.cohere.ai/v1/chat",
                    model="command-r",
                    **PROVIDER_LIMITS["cohere"]
                ))
            
            self._initialized = True
            log_info("provider_pool", 
                f"Initialized with {len(self._keys)} keys: "
                f"{', '.join(k.key_id for k in self._keys)}")
    
    def get_best_key(self, preferred_providers=None, exclude_ids=None):
        """
        Get the best available key, considering:
        1. Availability (not rate limited)
        2. Provider preference (agent-specific)
        3. Usage score (least-used first)
        """
        with self._lock:
            candidates = []
            
            for key in self._keys:
                if not key.is_available():
                    continue
                if exclude_ids and key.key_id in exclude_ids:
                    continue
                candidates.append(key)
            
            if not candidates:
                return None
            
            def sort_key(k):
                pref_bonus = 0
                if preferred_providers and k.provider in preferred_providers:
                    try:
                        pref_bonus = -10 + preferred_providers.index(k.provider)
                    except ValueError:
                        pref_bonus = 0
                return (pref_bonus, k.usage_score)
            
            candidates.sort(key=sort_key)
            return candidates[0]
    
    def get_available_count(self) -> int:
        """How many keys are currently available."""
        with self._lock:
            return sum(1 for k in self._keys if k.is_available())
    
    def get_total_count(self) -> int:
        """Total registered keys."""
        return len(self._keys)
    
    def get_next_available_time(self) -> int:
        """Seconds until the next key becomes available. 0 if one is ready."""
        with self._lock:
            if any(k.is_available() for k in self._keys):
                return 0
            times = [k.time_until_available() for k in self._keys]
            return min(times) if times else 0
    
    def get_status(self) -> dict:
        """Full pool status for dashboard/logging."""
        with self._lock:
            status = {
                "total_keys": len(self._keys),
                "available_keys": sum(1 for k in self._keys if k.is_available()),
                "keys": []
            }
            for k in self._keys:
                status["keys"].append({
                    "key_id": k.key_id,
                    "provider": k.provider,
                    "available": k.is_available(),
                    "calls_this_minute": k.calls_this_minute,
                    "calls_today": k.calls_today,
                    "rpm_limit": k.rpm,
                    "rpd_limit": k.rpd,
                    "consecutive_failures": k.consecutive_failures,
                    "total_calls": k.total_calls,
                    "total_successes": k.total_successes,
                    "seconds_until_available": k.time_until_available(),
                    "usage_score": round(k.usage_score, 3),
                })
            return status
    
    def call_llm(self, prompt: str, system_msg: str = "",
                 preferred_providers=None,
                 exclude_providers=None,
                 model_override=None,
                 max_tokens: int = 1500,
                 temperature: float = 0.7,
                 timeout: int = 60,
                 caller: str = "unknown") -> dict:
        """
        Make an LLM API call using the best available key.
        Handles routing, retries, rate limit tracking automatically.
        """
        self.initialize()
        
        tried = set()
        
        for attempt in range(min(3, len(self._keys))):
            key = self.get_best_key(
                preferred_providers=preferred_providers,
                exclude_ids=tried
            )
            
            if key is None:
                break
            
            tried.add(key.key_id)
            
            log_debug("provider_pool", 
                f"[{caller}] attempt {attempt+1}: {key.key_id} "
                f"(usage: {key.usage_score:.2f})")
            
            key.record_call()
            
            if key.provider == "gemini":
                result = self._call_gemini(key, prompt, max_tokens, temperature, timeout)
            elif key.provider == "cohere":
                result = self._call_cohere(key, prompt, max_tokens, temperature, timeout)
            else:
                model = model_override or key.model
                result = self._call_openai_compat(
                    key, prompt, system_msg, model, 
                    max_tokens, temperature, timeout
                )
            
            if result["success"]:
                key.record_success()
                log_debug("provider_pool", f"[{caller}] {key.key_id} success")
                return {
                    "success": True,
                    "text": result["text"],
                    "provider": key.provider,
                    "key_id": key.key_id,
                    "error": None,
                    "all_exhausted": False
                }
            
            is_rate_limit = result.get("status_code") == 429
            key.record_failure(is_rate_limit=is_rate_limit)
            
            if is_rate_limit:
                log_debug("provider_pool", f"[{caller}] {key.key_id} rate limited, trying next")
            else:
                log_debug("provider_pool", f"[{caller}] {key.key_id} failed: {result.get('error')}")
        
        next_available = self.get_next_available_time()
        log_warn("provider_pool", 
            f"[{caller}] all keys exhausted. Next available in {next_available}s")
        
        return {
            "success": False,
            "text": None,
            "provider": None,
            "key_id": None,
            "error": "All provider keys exhausted",
            "all_exhausted": True,
            "retry_after_seconds": next_available
        }
    
    # ═══════════════════════════════════════════════════════════════
    # API FORMAT HANDLERS
    # ═══════════════════════════════════════════════════════════════
    
    def _call_openai_compat(self, key, prompt, system_msg, model, max_tokens, temperature, timeout):
        """Call OpenAI-compatible API (Groq, OpenRouter, Cerebras, Together)."""
        try:
            headers = {
                "Authorization": f"Bearer {key.key}",
                "Content-Type": "application/json"
            }
            if key.provider == "openrouter":
                headers["HTTP-Referer"] = "https://agent-research-hub.local"
                headers["X-Title"] = "Research Agent"
            
            messages = []
            if system_msg:
                messages.append({"role": "system", "content": system_msg})
            messages.append({"role": "user", "content": prompt})
            
            resp = requests.post(
                key.endpoint,
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=timeout
            )
            
            if resp.status_code == 429:
                return {"success": False, "status_code": 429, "error": "Rate limited"}
            if resp.status_code != 200:
                return {"success": False, "status_code": resp.status_code, "error": f"HTTP {resp.status_code}"}
            
            data = resp.json()
            if "choices" in data:
                text = data["choices"][0]["message"]["content"]
                if text:
                    return {"success": True, "text": text}
            
            return {"success": False, "status_code": 200, "error": "Empty response"}
        except requests.Timeout:
            return {"success": False, "status_code": 0, "error": "Timeout"}
        except Exception as e:
            return {"success": False, "status_code": 0, "error": str(e)}
    
    def _call_gemini(self, key, prompt, max_tokens, temperature, timeout):
        """Call Google Gemini API."""
        try:
            resp = requests.post(
                f"{key.endpoint}/v1beta/models/{key.model}:generateContent?key={key.key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": max_tokens,
                        "temperature": temperature
                    }
                },
                timeout=timeout
            )
            
            if resp.status_code == 429:
                return {"success": False, "status_code": 429, "error": "Rate limited"}
            if resp.status_code != 200:
                return {"success": False, "status_code": resp.status_code, "error": f"HTTP {resp.status_code}"}
            
            data = resp.json()
            if "candidates" in data:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                if text:
                    return {"success": True, "text": text}
            
            return {"success": False, "status_code": 200, "error": "Empty response"}
        except requests.Timeout:
            return {"success": False, "status_code": 0, "error": "Timeout"}
        except Exception as e:
            return {"success": False, "status_code": 0, "error": str(e)}
    
    def _call_cohere(self, key, prompt, max_tokens, temperature, timeout):
        """Call Cohere API."""
        try:
            resp = requests.post(
                key.endpoint,
                headers={
                    "Authorization": f"Bearer {key.key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": key.model,
                    "message": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=timeout
            )
            
            if resp.status_code == 429:
                return {"success": False, "status_code": 429, "error": "Rate limited"}
            if resp.status_code != 200:
                return {"success": False, "status_code": resp.status_code, "error": f"HTTP {resp.status_code}"}
            
            data = resp.json()
            text = data.get("text", "")
            if text:
                return {"success": True, "text": text}
            
            return {"success": False, "status_code": 200, "error": "Empty response"}
        except requests.Timeout:
            return {"success": False, "status_code": 0, "error": "Timeout"}
        except Exception as e:
            return {"success": False, "status_code": 0, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════
# GLOBAL SINGLETON — import this everywhere
# ═══════════════════════════════════════════════════════════════════

pool = ProviderPool()
