"""
PROVIDER POOL v2 — Global API key management with all your keys
================================================================
FIXED:
1. Loads GEMINI_BOT_KEY as gemini-2
2. Loads TELEGRAM_OPENROUTER_KEY as openrouter-3
3. Better adaptive cooldowns
4. Quota awareness methods for manager
"""

import os
import time
import threading
import requests
from datetime import datetime, timedelta
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
        """Record failed response with adaptive cooldown."""
        self.consecutive_failures += 1
        if is_rate_limit:
            # Adaptive cooldown: back off harder with consecutive failures
            base_cooldown = self.cooldown_minutes * 60
            multiplier = min(self.consecutive_failures, 5)
            cooldown = base_cooldown * multiplier
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
            
            # ── GEMINI (primary key) ───────────────────────────────
            gemini_key = os.getenv("GEMINI_API_KEY", "")
            if gemini_key:
                self._keys.append(ProviderKey(
                    provider="gemini", key=gemini_key, key_id="gemini-1",
                    endpoint="https://generativelanguage.googleapis.com",
                    model="gemini-2.0-flash",
                    **PROVIDER_LIMITS["gemini"]
                ))
            
            # ── GEMINI (bot key — YOUR EXTRA KEY) ──────────────────
            gemini_bot_key = os.getenv("GEMINI_BOT_KEY", "")
            if gemini_bot_key and gemini_bot_key != gemini_key:
                self._keys.append(ProviderKey(
                    provider="gemini", key=gemini_bot_key, key_id="gemini-2",
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
            
            # ── OPENROUTER (your 2 keys + telegram key) ────────────
            # FIXED: deepseek-r1:free was removed, using deepseek-v4-flash:free
            openrouter_keys_added = []
            for i, env_var in enumerate(["OPENROUTER_API_KEY", "OPENROUTER_API_KEY_2"], 1):
                key = os.getenv(env_var, "")
                if key:
                    self._keys.append(ProviderKey(
                        provider="openrouter", key=key, key_id=f"openrouter-{i}",
                        endpoint="https://openrouter.ai/api/v1/chat/completions",
                        model="deepseek/deepseek-v4-flash:free",
                        **PROVIDER_LIMITS["openrouter"]
                    ))
                    openrouter_keys_added.append(key)
            
            # ── OPENROUTER (telegram key — YOUR EXTRA KEY) ─────────
            tg_or_key = os.getenv("TELEGRAM_OPENROUTER_KEY", "")
            if tg_or_key and tg_or_key not in openrouter_keys_added:
                self._keys.append(ProviderKey(
                    provider="openrouter", key=tg_or_key, key_id="openrouter-3",
                    endpoint="https://openrouter.ai/api/v1/chat/completions",
                    model="deepseek/deepseek-v4-flash:free",
                    **PROVIDER_LIMITS["openrouter"]
                ))
            
            # ── CEREBRAS ───────────────────────────────────────────
            # Register two model variants — one will work
            cerebras_key = os.getenv("CEREBRAS_API_KEY", "")
            if cerebras_key:
                self._keys.append(ProviderKey(
                    provider="cerebras", key=cerebras_key, key_id="cerebras-1",
                    endpoint="https://api.cerebras.ai/v1/chat/completions",
                    model="qwen-3-32b",
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
                    model="command-r-plus",
                    **PROVIDER_LIMITS["cohere"]
                ))
            
            self._initialized = True
            log_info("provider_pool", f"Initialized with {len(self._keys)} API keys")
    
    def get_available_count(self) -> int:
        """Get count of currently available providers."""
        self.initialize()
        return len([k for k in self._keys if k.is_available()])
    
    def get_total_count(self) -> int:
        """Get total count of registered providers."""
        self.initialize()
        return len(self._keys)
    
    def get_best_key(self, preferred_providers: list = None):
        """Get the best available key for a request."""
        self.initialize()
        
        with self._lock:
            available = [k for k in self._keys if k.is_available()]
            
            if not available:
                return None
            
            # Filter by preferred providers if specified
            if preferred_providers:
                preferred = [k for k in available if k.provider in preferred_providers]
                if preferred:
                    available = preferred
            
            # Sort by usage score (lower is better)
            available.sort(key=lambda k: k.usage_score)
            
            return available[0]
    
    def call_llm(self, prompt: str, system_msg: str = "", 
                 preferred_providers: list = None,
                 max_tokens: int = 1500, temperature: float = 0.7,
                 timeout: int = 60, caller: str = "unknown") -> dict:
        """
        Call an LLM with automatic provider selection and fallback.
        Logs every attempt so we can diagnose failures.
        """
        self.initialize()
        
        tried_keys = set()
        last_error = None
        errors_detail = []
        
        for attempt in range(len(self._keys)):
            key = self.get_best_key(preferred_providers)
            
            if not key or key.key_id in tried_keys:
                # Try without preference filter
                all_available = [k for k in self._keys 
                               if k.is_available() and k.key_id not in tried_keys]
                if all_available:
                    all_available.sort(key=lambda k: k.usage_score)
                    key = all_available[0]
                else:
                    break
            
            if not key:
                break
            
            tried_keys.add(key.key_id)
            key.record_call()
            
            log_info("provider_pool", f"{caller} trying {key.key_id} ({key.provider}/{key.model})")
            
            try:
                result = self._make_request(key, prompt, system_msg, 
                                           max_tokens, temperature, timeout)
                
                if result.get("success"):
                    key.record_success()
                    result["key_id"] = key.key_id
                    result["provider"] = key.provider
                    return result
                
                # Log the specific error
                error = result.get("error", "unknown")
                log_warn("provider_pool", f"{key.key_id} failed: {error[:150]}")
                errors_detail.append(f"{key.key_id}: {error[:100]}")
                
                # Check if rate limited
                error_lower = error.lower()
                is_rate_limit = any(x in error_lower for x in 
                    ["rate", "limit", "quota", "429", "too many"])
                key.record_failure(is_rate_limit=is_rate_limit)
                last_error = error
                
                # Small delay before trying next provider
                time.sleep(1)
                
            except Exception as e:
                key.record_failure(is_rate_limit=False)
                last_error = str(e)
                errors_detail.append(f"{key.key_id}: EXCEPTION {str(e)[:80]}")
                log_warn("provider_pool", f"{key.key_id} exception: {e}")
                time.sleep(1)
        
        # All providers exhausted — log full detail so we can diagnose
        log_error("provider_pool", 
            f"{caller} ALL EXHAUSTED after trying {len(tried_keys)} providers: "
            + " | ".join(errors_detail))
        
        return {
            "success": False,
            "all_exhausted": True,
            "error": last_error or "All providers exhausted",
            "tried": list(tried_keys),
            "errors": errors_detail
        }
    
    def _make_request(self, key, prompt: str, system_msg: str,
                      max_tokens: int, temperature: float, timeout: int) -> dict:
        """Make the actual API request based on provider type."""
        
        try:
            if key.provider == "gemini":
                return self._call_gemini(key, prompt, system_msg, 
                                        max_tokens, temperature, timeout)
            elif key.provider == "cohere":
                return self._call_cohere(key, prompt, system_msg,
                                        max_tokens, temperature, timeout)
            else:
                # OpenAI-compatible: Groq, OpenRouter, Cerebras, Together
                return self._call_openai_compatible(key, prompt, system_msg,
                                                   max_tokens, temperature, timeout)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _call_openai_compatible(self, key, prompt: str, system_msg: str,
                                 max_tokens: int, temperature: float, timeout: int) -> dict:
        """Call OpenAI-compatible APIs (Groq, OpenRouter, Cerebras, Together)."""
        headers = {
            "Authorization": f"Bearer {key.key}",
            "Content-Type": "application/json"
        }
        
        # OpenRouter needs extra headers
        if key.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/Mrdoir/agent-system-v2"
            headers["X-Title"] = "Agent Research Hub"
        
        messages = []
        if system_msg:
            messages.append({"role": "system", "content": system_msg})
        messages.append({"role": "user", "content": prompt})
        
        try:
            resp = requests.post(
                key.endpoint,
                headers=headers,
                json={
                    "model": key.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=timeout
            )
        except requests.exceptions.Timeout:
            return {"success": False, "error": f"{key.provider} timeout after {timeout}s"}
        except requests.exceptions.ConnectionError as e:
            return {"success": False, "error": f"{key.provider} connection error: {e}"}
        
        if resp.status_code == 429:
            return {"success": False, "error": f"rate_limit_429 from {key.provider}"}
        
        if resp.status_code != 200:
            return {"success": False, "error": f"{key.provider} HTTP {resp.status_code}: {resp.text[:200]}"}
        
        try:
            data = resp.json()
        except Exception:
            return {"success": False, "error": f"{key.provider} invalid JSON response"}
        
        if "choices" in data and len(data["choices"]) > 0:
            text = data["choices"][0].get("message", {}).get("content", "")
            if text:
                return {"success": True, "text": text}
            return {"success": False, "error": f"{key.provider} empty response content"}
        
        # Some providers return errors in the body
        if "error" in data:
            err_msg = data["error"].get("message", str(data["error"]))[:200] if isinstance(data["error"], dict) else str(data["error"])[:200]
            return {"success": False, "error": f"{key.provider} API error: {err_msg}"}
        
        return {"success": False, "error": f"{key.provider} no choices in response: {str(data)[:150]}"}
    
    def _call_gemini(self, key, prompt: str, system_msg: str,
                     max_tokens: int, temperature: float, timeout: int) -> dict:
        """Call Google Gemini API."""
        full_prompt = f"{system_msg}\n\n{prompt}" if system_msg else prompt
        
        try:
            resp = requests.post(
                f"{key.endpoint}/v1beta/models/{key.model}:generateContent?key={key.key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": max_tokens,
                        "temperature": temperature
                    }
                },
                timeout=timeout
            )
        except requests.exceptions.Timeout:
            return {"success": False, "error": "gemini timeout"}
        except requests.exceptions.ConnectionError as e:
            return {"success": False, "error": f"gemini connection error: {e}"}
        
        if resp.status_code == 429:
            return {"success": False, "error": "rate_limit_429"}
        
        if resp.status_code != 200:
            return {"success": False, "error": f"gemini HTTP {resp.status_code}: {resp.text[:200]}"}
        
        data = resp.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return {"success": True, "text": text}
        except (KeyError, IndexError):
            # Log what we actually got back
            return {"success": False, "error": f"gemini bad response: {str(data)[:200]}"}
    
    def _call_cohere(self, key, prompt: str, system_msg: str,
                     max_tokens: int, temperature: float, timeout: int) -> dict:
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
                    "preamble": system_msg if system_msg else None,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=timeout
            )
        except requests.exceptions.Timeout:
            return {"success": False, "error": "cohere timeout"}
        except requests.exceptions.ConnectionError as e:
            return {"success": False, "error": f"cohere connection error: {e}"}
        
        if resp.status_code == 429:
            return {"success": False, "error": "rate_limit_429 from cohere"}
        
        if resp.status_code != 200:
            return {"success": False, "error": f"cohere HTTP {resp.status_code}: {resp.text[:200]}"}
        
        data = resp.json()
        if "text" in data:
            return {"success": True, "text": data["text"]}
        
        return {"success": False, "error": f"cohere no text in response: {str(data)[:150]}"}


# Global singleton
pool = ProviderPool()
