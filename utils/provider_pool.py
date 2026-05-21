"""
PROVIDER POOL v3 — COMPLETE FIXED VERSION (May 2026)
=====================================================
FIXES:
1. Cerebras model: qwen-3-32b → llama-3.3-70b (free tier)
2. Cohere model: command-r-plus → command-r (free tier)  
3. Together AI: REMOVED (requires paid credits - HTTP 402)
4. Added ALL methods manager.py needs (get_total_count, etc.)
5. Better error handling for model-not-found errors

HOW TO DEPLOY:
1. Go to https://github.com/Mrdoir/agent-system-v2
2. Click utils/provider_pool.py → Edit (pencil icon)
3. Select ALL → Delete → Paste this ENTIRE file
4. Commit → Render auto-deploys
"""

import os
import time
import threading
import requests
from datetime import datetime, timedelta
from utils.logger import log_info, log_warn, log_debug, log_error


# ═══════════════════════════════════════════════════════════════════
# PROVIDER DEFINITIONS — rate limits per free tier (May 2026)
# ═══════════════════════════════════════════════════════════════════

PROVIDER_LIMITS = {
    "gemini":      {"rpm": 15, "rpd": 1500, "cooldown_minutes": 1},
    "groq":        {"rpm": 30, "rpd": 14400, "cooldown_minutes": 1},
    "openrouter":  {"rpm": 20, "rpd": 200, "cooldown_minutes": 3},
    "cerebras":    {"rpm": 30, "rpd": 14400, "cooldown_minutes": 1},
    "cohere":      {"rpm": 5, "rpd": 5000, "cooldown_minutes": 2},
}

# ═══════════════════════════════════════════════════════════════════
# CURRENT FREE MODELS (Updated May 2026)
# When models change, ONLY update this dictionary
# ═══════════════════════════════════════════════════════════════════

CURRENT_MODELS = {
    "gemini": "gemini-2.0-flash",
    "groq": "llama-3.3-70b-versatile",
    "openrouter": "deepseek/deepseek-v4-flash:free",
    "cerebras": "llama-3.3-70b",       # FIXED: was qwen-3-32b (404)
    "cohere": "command-r",             # FIXED: was command-r-plus (removed)
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
        
        if now >= self.minute_reset:
            self.calls_this_minute = 0
            self.minute_reset = now + 60
        if now >= self.hour_reset:
            self.calls_this_hour = 0
            self.hour_reset = now + 3600
        if now >= self.day_reset:
            self.calls_today = 0
            self.day_reset = now + 86400
        
        if now < self.rate_limited_until:
            return False
        if self.calls_this_minute >= int(self.rpm * 0.8):
            return False
        if self.calls_today >= int(self.rpd * 0.9):
            return False
        
        return True
    
    def record_call(self):
        """Record that we made a call with this key."""
        self.calls_this_minute += 1
        self.calls_this_hour += 1
        self.calls_today += 1
        self.total_calls += 1
        self.last_used = time.time()
    
    def record_success(self):
        """Record successful response."""
        self.consecutive_failures = 0
        self.total_successes += 1
        self.last_success = time.time()
    
    def record_failure(self, is_rate_limit: bool = False):
        """Record failed response with adaptive cooldown."""
        self.consecutive_failures += 1
        if is_rate_limit:
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
    
    # ═══════════════════════════════════════════════════════════════
    # INITIALIZATION
    # ═══════════════════════════════════════════════════════════════
    
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
                    model=CURRENT_MODELS["gemini"],
                    **PROVIDER_LIMITS["gemini"]
                ))
            
            # ── GEMINI (bot key) ───────────────────────────────────
            gemini_bot_key = os.getenv("GEMINI_BOT_KEY", "")
            if gemini_bot_key and gemini_bot_key != gemini_key:
                self._keys.append(ProviderKey(
                    provider="gemini", key=gemini_bot_key, key_id="gemini-2",
                    endpoint="https://generativelanguage.googleapis.com",
                    model=CURRENT_MODELS["gemini"],
                    **PROVIDER_LIMITS["gemini"]
                ))
            
            # ── GROQ (2 keys) ──────────────────────────────────────
            for i, env_var in enumerate(["GROQ_API_KEY", "GROQ_API_KEY_2"], 1):
                key = os.getenv(env_var, "")
                if key:
                    self._keys.append(ProviderKey(
                        provider="groq", key=key, key_id=f"groq-{i}",
                        endpoint="https://api.groq.com/openai/v1/chat/completions",
                        model=CURRENT_MODELS["groq"],
                        **PROVIDER_LIMITS["groq"]
                    ))
            
            # ── OPENROUTER (up to 3 keys) ──────────────────────────
            openrouter_keys_added = []
            for i, env_var in enumerate(["OPENROUTER_API_KEY", "OPENROUTER_API_KEY_2"], 1):
                key = os.getenv(env_var, "")
                if key:
                    self._keys.append(ProviderKey(
                        provider="openrouter", key=key, key_id=f"openrouter-{i}",
                        endpoint="https://openrouter.ai/api/v1/chat/completions",
                        model=CURRENT_MODELS["openrouter"],
                        **PROVIDER_LIMITS["openrouter"]
                    ))
                    openrouter_keys_added.append(key)
            
            # ── OPENROUTER (telegram key) ──────────────────────────
            tg_or_key = os.getenv("TELEGRAM_OPENROUTER_KEY", "")
            if tg_or_key and tg_or_key not in openrouter_keys_added:
                self._keys.append(ProviderKey(
                    provider="openrouter", key=tg_or_key, key_id="openrouter-3",
                    endpoint="https://openrouter.ai/api/v1/chat/completions",
                    model=CURRENT_MODELS["openrouter"],
                    **PROVIDER_LIMITS["openrouter"]
                ))
            
            # ── CEREBRAS (FIXED model) ─────────────────────────────
            cerebras_key = os.getenv("CEREBRAS_API_KEY", "")
            if cerebras_key:
                self._keys.append(ProviderKey(
                    provider="cerebras", key=cerebras_key, key_id="cerebras-1",
                    endpoint="https://api.cerebras.ai/v1/chat/completions",
                    model=CURRENT_MODELS["cerebras"],
                    **PROVIDER_LIMITS["cerebras"]
                ))
            
            # ── COHERE (FIXED model) ───────────────────────────────
            cohere_key = os.getenv("COHERE_API_KEY", "")
            if cohere_key:
                self._keys.append(ProviderKey(
                    provider="cohere", key=cohere_key, key_id="cohere-1",
                    endpoint="https://api.cohere.ai/v1/chat",
                    model=CURRENT_MODELS["cohere"],
                    **PROVIDER_LIMITS["cohere"]
                ))
            
            # ── TOGETHER (SKIPPED — needs paid credits) ────────────
            # together_key = os.getenv("TOGETHER_API_KEY", "")
            # HTTP 402: Credit limit exceeded
            
            self._initialized = True
            log_info("provider_pool", f"Initialized with {len(self._keys)} API keys")
    
    # ═══════════════════════════════════════════════════════════════
    # STATUS METHODS (used by manager.py)
    # ═══════════════════════════════════════════════════════════════
    
    def get_available_count(self) -> tuple:
        """Return (available_count, total_count). Used by manager."""
        with self._lock:
            available = sum(1 for k in self._keys if k.is_available())
            return available, len(self._keys)
    
    def get_total_count(self) -> int:
        """Return total number of registered keys. Used by manager."""
        return len(self._keys)
    
    def get_available_providers(self) -> list:
        """Return list of available provider key IDs. Used by manager."""
        with self._lock:
            return [k.key_id for k in self._keys if k.is_available()]
    
    def get_next_available_time(self) -> int:
        """Return seconds until next provider becomes available. Used by manager."""
        with self._lock:
            if not self._keys:
                return 60
            times = [k.time_until_available() for k in self._keys]
            return min(times) if times else 60
    
    def get_status_summary(self) -> dict:
        """Get summary of all providers for debugging."""
        self.initialize()
        summary = {}
        for key in self._keys:
            summary[key.key_id] = {
                "provider": key.provider,
                "model": key.model,
                "available": key.is_available(),
                "calls_today": key.calls_today,
                "calls_this_minute": key.calls_this_minute,
                "consecutive_failures": key.consecutive_failures,
                "time_until_available": key.time_until_available()
            }
        return summary
    
    # ═══════════════════════════════════════════════════════════════
    # MAIN LLM CALL METHOD
    # ═══════════════════════════════════════════════════════════════
    
    def call_llm(self, prompt: str, system_msg: str = "", 
                 preferred_providers: list = None, max_tokens: int = 1500,
                 temperature: float = 0.7, timeout: int = 60,
                 caller: str = "unknown") -> dict:
        """
        Call an LLM using the best available provider.
        Tries preferred providers first, then falls back to others.
        Returns: {"success": bool, "text": str|None, "provider": str, ...}
        """
        self.initialize()
        
        tried = []
        last_error = None
        
        # Build priority list
        if preferred_providers:
            priority_keys = []
            other_keys = []
            for k in self._keys:
                if k.is_available():
                    if k.provider in preferred_providers:
                        priority_keys.append(k)
                    else:
                        other_keys.append(k)
            priority_keys.sort(key=lambda k: (
                preferred_providers.index(k.provider) if k.provider in preferred_providers else 999,
                k.usage_score
            ))
            other_keys.sort(key=lambda k: k.usage_score)
            keys_to_try = priority_keys + other_keys
        else:
            keys_to_try = sorted(
                [k for k in self._keys if k.is_available()],
                key=lambda k: k.usage_score
            )
        
        for key in keys_to_try:
            log_info("provider_pool", f"{caller} trying {key.key_id} ({key.provider}/{key.model})")
            key.record_call()
            
            try:
                result = self._call_provider(key, prompt, system_msg, max_tokens, temperature, timeout)
                
                if result["success"]:
                    key.record_success()
                    return {
                        "success": True,
                        "text": result["text"],
                        "provider": key.provider,
                        "key_id": key.key_id,
                        "model": key.model
                    }
                else:
                    error = result.get("error", "unknown")
                    tried.append(f"{key.key_id}: {error[:80]}")
                    last_error = error
                    
                    is_rate_limit = "429" in str(error) or "rate" in str(error).lower()
                    key.record_failure(is_rate_limit=is_rate_limit)
                    
                    log_warn("provider_pool", f"{key.key_id} failed: {error[:100]}")
                    time.sleep(1)
                    
            except Exception as e:
                error = str(e)
                tried.append(f"{key.key_id}: {error[:80]}")
                last_error = error
                key.record_failure()
                log_error("provider_pool", f"{key.key_id} exception: {error}")
                time.sleep(1)
        
        # All exhausted
        log_warn("provider_pool", 
            f"{caller} ALL EXHAUSTED after trying {len(tried)} providers: {' | '.join(tried)}")
        
        return {
            "success": False,
            "error": last_error or "all_exhausted",
            "all_exhausted": True,
            "tried": tried
        }
    
    # ═══════════════════════════════════════════════════════════════
    # PROVIDER-SPECIFIC API CALLS
    # ═══════════════════════════════════════════════════════════════
    
    def _call_provider(self, key: ProviderKey, prompt: str, system_msg: str,
                       max_tokens: int, temperature: float, timeout: int) -> dict:
        """Route to the correct provider API."""
        try:
            if key.provider == "gemini":
                return self._call_gemini(key, prompt, system_msg, max_tokens, temperature, timeout)
            elif key.provider in ("groq", "cerebras"):
                return self._call_openai_compatible(key, prompt, system_msg, max_tokens, temperature, timeout)
            elif key.provider == "openrouter":
                return self._call_openrouter(key, prompt, system_msg, max_tokens, temperature, timeout)
            elif key.provider == "cohere":
                return self._call_cohere(key, prompt, system_msg, max_tokens, temperature, timeout)
            else:
                return {"success": False, "error": f"unknown_provider: {key.provider}"}
        except requests.exceptions.Timeout:
            return {"success": False, "error": f"{key.provider} timeout after {timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": f"{key.provider} connection error"}
        except Exception as e:
            return {"success": False, "error": f"{key.provider} error: {str(e)[:150]}"}
    
    def _call_gemini(self, key, prompt, system_msg, max_tokens, temperature, timeout):
        """Call Google Gemini API."""
        url = f"{key.endpoint}/v1beta/models/{key.model}:generateContent?key={key.key}"
        
        contents = []
        if system_msg:
            contents.append({"role": "user", "parts": [{"text": f"System: {system_msg}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        
        resp = requests.post(url, json={
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}
        }, timeout=timeout)
        
        if resp.status_code == 429:
            return {"success": False, "error": "rate_limit_429"}
        if resp.status_code != 200:
            return {"success": False, "error": f"gemini HTTP {resp.status_code}: {resp.text[:200]}"}
        
        data = resp.json()
        if "candidates" in data and data["candidates"]:
            text = data["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if text:
                return {"success": True, "text": text}
        
        return {"success": False, "error": f"gemini no candidates: {str(data)[:200]}"}
    
    def _call_openai_compatible(self, key, prompt, system_msg, max_tokens, temperature, timeout):
        """Call OpenAI-compatible API (Groq, Cerebras)."""
        headers = {
            "Authorization": f"Bearer {key.key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_msg:
            messages.append({"role": "system", "content": system_msg})
        messages.append({"role": "user", "content": prompt})
        
        resp = requests.post(key.endpoint, headers=headers, json={
            "model": key.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }, timeout=timeout)
        
        if resp.status_code == 429:
            return {"success": False, "error": f"rate_limit_429 from {key.provider}"}
        if resp.status_code == 404:
            return {"success": False, "error": f"{key.provider} HTTP 404: {resp.text[:200]}"}
        if resp.status_code != 200:
            return {"success": False, "error": f"{key.provider} HTTP {resp.status_code}: {resp.text[:200]}"}
        
        data = resp.json()
        if "choices" in data and data["choices"]:
            text = data["choices"][0].get("message", {}).get("content", "")
            if text:
                return {"success": True, "text": text}
        
        return {"success": False, "error": f"{key.provider} no choices: {str(data)[:200]}"}
    
    def _call_openrouter(self, key, prompt, system_msg, max_tokens, temperature, timeout):
        """Call OpenRouter API."""
        headers = {
            "Authorization": f"Bearer {key.key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://agent-system-v2.onrender.com",
            "X-Title": "Agent Research Hub"
        }
        
        messages = []
        if system_msg:
            messages.append({"role": "system", "content": system_msg})
        messages.append({"role": "user", "content": prompt})
        
        resp = requests.post(key.endpoint, headers=headers, json={
            "model": key.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }, timeout=timeout)
        
        if resp.status_code == 429:
            return {"success": False, "error": "rate_limit_429 from openrouter"}
        if resp.status_code != 200:
            return {"success": False, "error": f"openrouter HTTP {resp.status_code}: {resp.text[:200]}"}
        
        data = resp.json()
        if "choices" in data and data["choices"]:
            text = data["choices"][0].get("message", {}).get("content", "")
            if text:
                return {"success": True, "text": text}
        
        return {"success": False, "error": f"openrouter no choices: {str(data)[:200]}"}
    
    def _call_cohere(self, key, prompt, system_msg, max_tokens, temperature, timeout):
        """Call Cohere API."""
        headers = {
            "Authorization": f"Bearer {key.key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": key.model,
            "message": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        if system_msg:
            payload["preamble"] = system_msg
        
        resp = requests.post(key.endpoint, headers=headers, json=payload, timeout=timeout)
        
        if resp.status_code == 429:
            return {"success": False, "error": "rate_limit_429 from cohere"}
        if resp.status_code == 404:
            return {"success": False, "error": f"cohere HTTP 404: {resp.text[:200]}"}
        if resp.status_code != 200:
            return {"success": False, "error": f"cohere HTTP {resp.status_code}: {resp.text[:200]}"}
        
        data = resp.json()
        if "text" in data:
            return {"success": True, "text": data["text"]}
        
        return {"success": False, "error": f"cohere no text: {str(data)[:200]}"}


# ═══════════════════════════════════════════════════════════════════
# GLOBAL POOL INSTANCE — imported by all agents and manager
# ═══════════════════════════════════════════════════════════════════
pool = ProviderPool()
