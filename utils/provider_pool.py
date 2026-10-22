"""
PROVIDER POOL v4 — validated outputs, Gemini model chain, real-model tracking
=============================================================================
What changed vs v3 (and why):
1. OUTPUT VALIDATION. v3 treated ANY non-empty text as success, so a safety
   classifier ("User Safety: safe") or an empty/tiny reply was saved as research.
   Now junk is rejected and the next provider is tried automatically.
2. GEMINI MODEL CHAIN. gemini-2.0-flash was retired by Google on 1 June 2026
   (all tiers) and gemini-2.5-flash has an October 2026 shutdown date. The pool
   now tries a chain of models and remembers the one that works. Override
   without touching code: set GEMINI_MODEL_CHAIN="model-a,model-b,model-c".
3. REAL MODEL TRACKING. 'openrouter/free' is a ROUTER that picks a different
   free model per request. We now return the model that actually answered
   (model_used) and reject guard/safety models.
4. DEAD KEYS STOP WASTING CALLS. HTTP 401/403/404 pauses that key for 6 hours.
5. FIXED: the old check `"rate" in error` matched the word "generateContent",
   so every Gemini error looked like a rate limit.
6. probe_all() — tiny live test of every key (used by /api/diag).

All models can be overridden from Render env vars:
GROQ_MODEL, OPENROUTER_MODEL, CEREBRAS_MODEL, COHERE_MODEL, GEMINI_MODEL_CHAIN
"""

import os
import re
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor
from utils.logger import log_info, log_warn, log_debug, log_error


# ═══════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════

def _env_list(name: str, default: str) -> list:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


PROVIDER_LIMITS = {
    "gemini":      {"rpm": 15, "rpd": 1500, "cooldown_minutes": 1},
    "groq":        {"rpm": 30, "rpd": 14400, "cooldown_minutes": 1},
    "openrouter":  {"rpm": 20, "rpd": 200, "cooldown_minutes": 3},
    "cerebras":    {"rpm": 30, "rpd": 14400, "cooldown_minutes": 1},
    "cohere":      {"rpm": 5, "rpd": 5000, "cooldown_minutes": 2},
}

# Tried in order; the first that works is remembered. Google retires models
# often, so keep this editable from the environment.
GEMINI_MODEL_CHAIN = _env_list(
    "GEMINI_MODEL_CHAIN", "gemini-3.5-flash,gemini-2.5-flash,gemini-3-flash-preview"
) or ["gemini-3.5-flash"]

CURRENT_MODELS = {
    "gemini": GEMINI_MODEL_CHAIN[0],
    "groq": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
    "openrouter": os.getenv("OPENROUTER_MODEL", "openrouter/free"),
    "cerebras": os.getenv("CEREBRAS_MODEL", "gpt-oss-120b"),
    "cohere": os.getenv("COHERE_MODEL", "command-r7b-12-2024"),
}

# ═══════════════════════════════════════════════════════════════════
# OUTPUT VALIDATION
# ═══════════════════════════════════════════════════════════════════

GUARD_MODEL_RE = re.compile(r"guard|safeguard|moderat|shield|safety", re.I)
SAFETY_OUTPUT_RE = re.compile(r'^\s*[\{\[]?\s*"?(user|response|prompt)[\s_]*safety"?\s*[:=]', re.I)
BARE_VERDICT_RE = re.compile(r"^\s*(safe|unsafe)\s*(\n\s*S\d+[\w,\s]*)?\s*$", re.I)
REASONING_LEAK_RE = re.compile(r"^\s*(here'?s|here is)\s+a\s+thinking\s+process", re.I)
THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.S | re.I)


def clean_text(text: str) -> str:
    """Strip <think>...</think> blocks some reasoning models put in the answer."""
    return THINK_BLOCK_RE.sub("", text or "").strip()


def junk_reason(text: str, model_used: str = "", min_chars: int = 0):
    """Return a reason string if the output is not usable, else None."""
    t = (text or "").strip()
    if not t:
        return "empty output"
    if model_used and GUARD_MODEL_RE.search(model_used):
        return f"safety/guard model ({model_used})"
    if SAFETY_OUTPUT_RE.match(t) or BARE_VERDICT_RE.match(t):
        return "safety-classifier output"
    if REASONING_LEAK_RE.match(t):
        return "leaked reasoning instead of an answer"
    if len(t) < min_chars:
        return f"too short ({len(t)} < {min_chars} chars)"
    return None


# ═══════════════════════════════════════════════════════════════════
# KEY OBJECT
# ═══════════════════════════════════════════════════════════════════

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

        self.calls_this_minute = 0
        self.calls_this_hour = 0
        self.calls_today = 0
        self.minute_reset = time.time() + 60
        self.hour_reset = time.time() + 3600
        self.day_reset = time.time() + 86400

        self.rate_limited_until = 0
        self.consecutive_failures = 0
        self.last_success = 0
        self.last_used = 0
        self.total_calls = 0
        self.total_successes = 0

    def is_available(self) -> bool:
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
        self.calls_this_minute += 1
        self.calls_this_hour += 1
        self.calls_today += 1
        self.total_calls += 1
        self.last_used = time.time()

    def record_success(self):
        self.consecutive_failures = 0
        self.total_successes += 1
        self.last_success = time.time()

    def record_failure(self, is_rate_limit: bool = False):
        self.consecutive_failures += 1
        if is_rate_limit:
            base_cooldown = self.cooldown_minutes * 60
            multiplier = min(self.consecutive_failures, 5)
            cooldown = base_cooldown * multiplier
            self.rate_limited_until = time.time() + cooldown
            log_debug("provider_pool",
                f"{self.key_id} rate limited for {cooldown}s "
                f"(failures: {self.consecutive_failures})")

    def disable_for(self, seconds: int, why: str = ""):
        """Pause a key that is clearly broken (bad key / retired model)."""
        self.rate_limited_until = max(self.rate_limited_until, time.time() + seconds)
        log_warn("provider_pool", f"{self.key_id} paused for {seconds // 3600}h — {why}")

    def time_until_available(self) -> int:
        now = time.time()
        if now >= self.rate_limited_until:
            if self.calls_this_minute >= int(self.rpm * 0.8):
                return max(0, int(self.minute_reset - now))
            return 0
        return max(0, int(self.rate_limited_until - now))

    @property
    def usage_score(self) -> float:
        now = time.time()
        recency_penalty = max(0, 60 - (now - self.last_used)) / 60
        minute_usage = self.calls_this_minute / max(self.rpm, 1)
        daily_usage = self.calls_today / max(self.rpd, 1)
        failure_penalty = min(self.consecutive_failures * 0.2, 1.0)
        return minute_usage + daily_usage + recency_penalty + failure_penalty


# ═══════════════════════════════════════════════════════════════════
# POOL
# ═══════════════════════════════════════════════════════════════════

class ProviderPool:
    """Global pool of all API provider keys. Thread-safe. Shared across agents."""

    def __init__(self):
        self._lock = threading.Lock()
        self._keys = []
        self._initialized = False
        self._gemini_working = None   # last Gemini model that answered

    # ── initialization ─────────────────────────────────────────────

    def initialize(self):
        """Load all API keys from environment and register them."""
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            # GEMINI (primary + bot key)
            gemini_key = os.getenv("GEMINI_API_KEY", "")
            if gemini_key:
                self._keys.append(ProviderKey(
                    provider="gemini", key=gemini_key, key_id="gemini-1",
                    endpoint="https://generativelanguage.googleapis.com",
                    model=CURRENT_MODELS["gemini"], **PROVIDER_LIMITS["gemini"]))

            gemini_bot_key = os.getenv("GEMINI_BOT_KEY", "")
            if gemini_bot_key and gemini_bot_key != gemini_key:
                self._keys.append(ProviderKey(
                    provider="gemini", key=gemini_bot_key, key_id="gemini-2",
                    endpoint="https://generativelanguage.googleapis.com",
                    model=CURRENT_MODELS["gemini"], **PROVIDER_LIMITS["gemini"]))

            # GROQ (2 keys)
            for i, env_var in enumerate(["GROQ_API_KEY", "GROQ_API_KEY_2"], 1):
                key = os.getenv(env_var, "")
                if key:
                    self._keys.append(ProviderKey(
                        provider="groq", key=key, key_id=f"groq-{i}",
                        endpoint="https://api.groq.com/openai/v1/chat/completions",
                        model=CURRENT_MODELS["groq"], **PROVIDER_LIMITS["groq"]))

            # OPENROUTER (2 keys + telegram key)
            openrouter_keys_added = []
            for i, env_var in enumerate(["OPENROUTER_API_KEY", "OPENROUTER_API_KEY_2"], 1):
                key = os.getenv(env_var, "")
                if key:
                    self._keys.append(ProviderKey(
                        provider="openrouter", key=key, key_id=f"openrouter-{i}",
                        endpoint="https://openrouter.ai/api/v1/chat/completions",
                        model=CURRENT_MODELS["openrouter"], **PROVIDER_LIMITS["openrouter"]))
                    openrouter_keys_added.append(key)

            tg_or_key = os.getenv("TELEGRAM_OPENROUTER_KEY", "")
            if tg_or_key and tg_or_key not in openrouter_keys_added:
                self._keys.append(ProviderKey(
                    provider="openrouter", key=tg_or_key, key_id="openrouter-3",
                    endpoint="https://openrouter.ai/api/v1/chat/completions",
                    model=CURRENT_MODELS["openrouter"], **PROVIDER_LIMITS["openrouter"]))

            # CEREBRAS
            cerebras_key = os.getenv("CEREBRAS_API_KEY", "")
            if cerebras_key:
                self._keys.append(ProviderKey(
                    provider="cerebras", key=cerebras_key, key_id="cerebras-1",
                    endpoint="https://api.cerebras.ai/v1/chat/completions",
                    model=CURRENT_MODELS["cerebras"], **PROVIDER_LIMITS["cerebras"]))

            # COHERE
            cohere_key = os.getenv("COHERE_API_KEY", "")
            if cohere_key:
                self._keys.append(ProviderKey(
                    provider="cohere", key=cohere_key, key_id="cohere-1",
                    endpoint="https://api.cohere.ai/v1/chat",
                    model=CURRENT_MODELS["cohere"], **PROVIDER_LIMITS["cohere"]))

            self._initialized = True
            log_info("provider_pool", f"Initialized with {len(self._keys)} API keys "
                                      f"(gemini chain: {', '.join(GEMINI_MODEL_CHAIN)})")

    # ── status (used by manager.py) ────────────────────────────────

    def get_available_count(self) -> int:
        with self._lock:
            return sum(1 for k in self._keys if k.is_available())

    def get_total_count(self) -> int:
        return len(self._keys)

    def get_available_providers(self) -> list:
        with self._lock:
            return [k.key_id for k in self._keys if k.is_available()]

    def get_next_available_time(self) -> int:
        with self._lock:
            if not self._keys:
                return 60
            times = [k.time_until_available() for k in self._keys]
            return min(times) if times else 60

    def get_status_summary(self) -> dict:
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

    def probe_all(self, timeout: int = 20) -> list:
        """Tiny live test of every key. Does not touch rate-limit counters."""
        self.initialize()

        def probe(k):
            t0 = time.time()
            try:
                r = self._call_provider(k, "Reply with exactly: OK", "", 20, 0.0, timeout)
            except Exception as e:
                r = {"success": False, "error": str(e)[:150]}
            model_used = r.get("model_used", k.model)
            problem = None
            if r.get("success"):
                problem = junk_reason(clean_text(r.get("text", "")), model_used, 0)
            else:
                problem = str(r.get("error", ""))[:160]
            return {
                "key_id": k.key_id,
                "provider": k.provider,
                "configured_model": k.model,
                "model_used": model_used,
                "ok": bool(r.get("success")) and not problem,
                "problem": problem,
                "sample": (r.get("text", "") or "")[:40],
                "seconds": round(time.time() - t0, 1),
            }

        with ThreadPoolExecutor(max_workers=8) as ex:
            return list(ex.map(probe, self._keys))

    # ── main LLM call ──────────────────────────────────────────────

    def call_llm(self, prompt: str, system_msg: str = "",
                 preferred_providers: list = None, max_tokens: int = 1500,
                 temperature: float = 0.7, timeout: int = 60,
                 caller: str = "unknown", min_chars: int = 0) -> dict:
        """
        Call an LLM using the best available provider.
        Tries preferred providers first, then falls back to others.
        Outputs that are junk (empty, too short, safety-classifier text,
        guard models) are rejected and the next provider is tried.
        """
        self.initialize()

        tried = []
        last_error = None

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
                    text = clean_text(result["text"])
                    model_used = result.get("model_used") or key.model
                    reason = junk_reason(text, model_used, min_chars)

                    if reason:
                        key.record_failure(is_rate_limit=False)
                        tried.append(f"{key.key_id}: junk ({reason})")
                        last_error = f"junk output: {reason}"
                        log_warn("provider_pool",
                                 f"{caller}: {key.key_id} [{model_used}] returned junk — {reason}. Trying next provider")
                        time.sleep(1)
                        continue

                    key.record_success()
                    return {
                        "success": True,
                        "text": text,
                        "provider": key.provider,
                        "key_id": key.key_id,
                        "model": key.model,
                        "model_used": model_used,
                    }

                error = result.get("error", "unknown")
                err_l = str(error).lower()
                tried.append(f"{key.key_id}: {str(error)[:80]}")
                last_error = error

                is_rate_limit = "429" in err_l or "rate_limit" in err_l or "rate limit" in err_l
                key.record_failure(is_rate_limit=is_rate_limit)

                if any(s in str(error) for s in ("HTTP 401", "HTTP 403", "HTTP 404")):
                    key.disable_for(6 * 3600, str(error)[:80])

                log_warn("provider_pool", f"{key.key_id} failed: {str(error)[:100]}")
                time.sleep(1)

            except Exception as e:
                error = str(e)
                tried.append(f"{key.key_id}: {error[:80]}")
                last_error = error
                key.record_failure()
                log_error("provider_pool", f"{key.key_id} exception: {error}")
                time.sleep(1)

        log_warn("provider_pool",
            f"{caller} ALL EXHAUSTED after trying {len(tried)} providers: {' | '.join(tried)}")

        return {
            "success": False,
            "error": last_error or "all_exhausted",
            "all_exhausted": True,
            "tried": tried
        }

    # ── provider-specific calls ────────────────────────────────────

    def _call_provider(self, key, prompt, system_msg, max_tokens, temperature, timeout):
        try:
            if key.provider == "gemini":
                return self._call_gemini(key, prompt, system_msg, max_tokens, temperature, timeout)
            elif key.provider in ("groq", "cerebras"):
                return self._call_openai_compatible(key, prompt, system_msg, max_tokens, temperature, timeout)
            elif key.provider == "openrouter":
                return self._call_openrouter(key, prompt, system_msg, max_tokens, temperature, timeout)
            elif key.provider == "cohere":
                return self._call_cohere(key, prompt, system_msg, max_tokens, temperature, timeout)
            return {"success": False, "error": f"unknown_provider: {key.provider}"}
        except requests.exceptions.Timeout:
            return {"success": False, "error": f"{key.provider} timeout after {timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": f"{key.provider} connection error"}
        except Exception as e:
            return {"success": False, "error": f"{key.provider} error: {str(e)[:150]}"}

    def _call_gemini(self, key, prompt, system_msg, max_tokens, temperature, timeout):
        """Gemini with a model chain: skips models Google has retired."""
        chain = list(GEMINI_MODEL_CHAIN)
        if self._gemini_working in chain:
            chain.remove(self._gemini_working)
            chain.insert(0, self._gemini_working)

        contents = []
        if system_msg:
            contents.append({"role": "user", "parts": [{"text": f"System: {system_msg}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        # extra headroom: newer Gemini models spend output tokens on "thinking"
        payload = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens + 1024, "temperature": temperature}
        }

        last_error = "gemini: empty model chain"
        for model in chain:
            url = f"{key.endpoint}/v1beta/models/{model}:generateContent?key={key.key}"
            resp = requests.post(url, json=payload, timeout=timeout)
            body = resp.text[:200]

            if resp.status_code == 429:
                return {"success": False, "error": f"rate_limit_429 from gemini ({model})"}

            gone = resp.status_code == 404 or (
                resp.status_code == 400 and re.search(r"not found|no longer|deprecated|not supported", body, re.I))
            if gone:
                last_error = f"gemini HTTP {resp.status_code} for {model}: {body}"
                log_warn("provider_pool", f"Gemini model {model} unavailable ({resp.status_code}) — trying next in chain")
                continue

            if resp.status_code != 200:
                return {"success": False, "error": f"gemini HTTP {resp.status_code} ({model}): {body}"}

            data = resp.json()
            cands = data.get("candidates") or []
            if cands:
                parts = (cands[0].get("content") or {}).get("parts") or []
                text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
                if text.strip():
                    self._gemini_working = model
                    key.model = model
                    return {"success": True, "text": text, "model_used": model}
            last_error = f"gemini no text from {model}: {str(data)[:150]}"

        return {"success": False, "error": last_error}

    def _call_openai_compatible(self, key, prompt, system_msg, max_tokens, temperature, timeout):
        """OpenAI-compatible API (Groq, Cerebras)."""
        headers = {"Authorization": f"Bearer {key.key}", "Content-Type": "application/json"}

        messages = []
        if system_msg:
            messages.append({"role": "system", "content": system_msg})
        messages.append({"role": "user", "content": prompt})

        resp = requests.post(key.endpoint, headers=headers, json={
            "model": key.model, "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature
        }, timeout=timeout)

        if resp.status_code == 429:
            return {"success": False, "error": f"rate_limit_429 from {key.provider}"}
        if resp.status_code != 200:
            return {"success": False, "error": f"{key.provider} HTTP {resp.status_code}: {resp.text[:200]}"}

        data = resp.json()
        if "choices" in data and data["choices"]:
            text = (data["choices"][0].get("message") or {}).get("content") or ""
            if text:
                return {"success": True, "text": text, "model_used": data.get("model") or key.model}

        return {"success": False, "error": f"{key.provider} no choices: {str(data)[:200]}"}

    def _call_openrouter(self, key, prompt, system_msg, max_tokens, temperature, timeout):
        """OpenRouter. With 'openrouter/free' the REAL model is in data['model']."""
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
            "model": key.model, "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature
        }, timeout=timeout)

        if resp.status_code == 429:
            return {"success": False, "error": "rate_limit_429 from openrouter"}
        if resp.status_code != 200:
            return {"success": False, "error": f"openrouter HTTP {resp.status_code}: {resp.text[:200]}"}

        data = resp.json()
        if "choices" in data and data["choices"]:
            text = (data["choices"][0].get("message") or {}).get("content") or ""
            if text:
                return {"success": True, "text": text, "model_used": data.get("model") or key.model}

        return {"success": False, "error": f"openrouter no choices: {str(data)[:200]}"}

    def _call_cohere(self, key, prompt, system_msg, max_tokens, temperature, timeout):
        headers = {"Authorization": f"Bearer {key.key}", "Content-Type": "application/json"}

        payload = {"model": key.model, "message": prompt,
                   "max_tokens": max_tokens, "temperature": temperature}
        if system_msg:
            payload["preamble"] = system_msg

        resp = requests.post(key.endpoint, headers=headers, json=payload, timeout=timeout)

        if resp.status_code == 429:
            return {"success": False, "error": "rate_limit_429 from cohere"}
        if resp.status_code != 200:
            return {"success": False, "error": f"cohere HTTP {resp.status_code}: {resp.text[:200]}"}

        data = resp.json()
        if "text" in data:
            return {"success": True, "text": data["text"], "model_used": key.model}

        return {"success": False, "error": f"cohere no text: {str(data)[:200]}"}


# ═══════════════════════════════════════════════════════════════════
# GLOBAL POOL INSTANCE — imported by all agents and manager
# ═══════════════════════════════════════════════════════════════════
pool = ProviderPool()
