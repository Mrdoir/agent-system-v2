"""
BASE AGENT v3 — Enhanced base class with retry logic and metrics
Improvements:
- Automatic retry with exponential backoff
- Better rate limit handling with provider tracking
- Success/failure metrics per provider
- Standardized response format
- Provider rotation on failure
"""

import time
from datetime import datetime, timedelta
from utils.logger import log_info, log_warn, log_error, log_debug, log_api_call, log_rate_limit
from utils.database import (
    save_result, update_agent_status, 
    set_agent_rate_limited, clear_agent_rate_limit, is_agent_rate_limited,
    get_conn
)


class BaseAgent:
    NAME = "base_agent"
    PROVIDER = "unknown"
    
    # Override in subclasses
    PROVIDERS = []  # List of provider configs for fallback
    
    def __init__(self):
        self._current_provider = None
        self._retry_count = 0
        self._max_retries = 2
    
    # ═══════════════════════════════════════════════════════════════
    # RATE LIMIT MANAGEMENT (Postgres-backed)
    # ═══════════════════════════════════════════════════════════════
    
    def set_rate_limited(self, reset_minutes: int = 60, provider: str = None):
        """Mark this agent as rate limited."""
        set_agent_rate_limited(self.NAME, reset_minutes)
        log_rate_limit(self.NAME, provider or self.PROVIDER, reset_minutes)
    
    def clear_rate_limit(self):
        """Clear rate limit status."""
        clear_agent_rate_limit(self.NAME)
        log_info(self.NAME, "Rate limit cleared, back online ✓")
    
    def is_rate_limited(self) -> bool:
        """Check if currently rate limited."""
        return is_agent_rate_limited(self.NAME)
    
    def minutes_until_reset(self) -> int:
        """Get minutes until rate limit resets."""
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
    
    # ═══════════════════════════════════════════════════════════════
    # DATABASE OPERATIONS
    # ═══════════════════════════════════════════════════════════════
    
    def save_to_db(self, topic: str, content: str, score: int = 0, tags: list = None) -> int:
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
    
    # ═══════════════════════════════════════════════════════════════
    # API CALL HELPERS
    # ═══════════════════════════════════════════════════════════════
    
    def _make_request(self, method: str, url: str, **kwargs) -> dict:
        """
        Make HTTP request with standard error handling.
        Returns: {"success": bool, "data": any, "status_code": int, "error": str}
        """
        import requests
        
        kwargs.setdefault("timeout", 45)
        
        try:
            if method.upper() == "GET":
                resp = requests.get(url, **kwargs)
            else:
                resp = requests.post(url, **kwargs)
            
            return {
                "success": resp.status_code == 200,
                "data": resp.json() if resp.status_code == 200 else None,
                "status_code": resp.status_code,
                "error": None if resp.status_code == 200 else f"HTTP {resp.status_code}"
            }
            
        except requests.Timeout:
            return {"success": False, "data": None, "status_code": 0, "error": "Timeout"}
        except requests.RequestException as e:
            return {"success": False, "data": None, "status_code": 0, "error": str(e)}
        except Exception as e:
            return {"success": False, "data": None, "status_code": 0, "error": str(e)}
    
    def _handle_response(self, result: dict, provider: str) -> dict:
        """
        Standardize API response handling.
        Returns: {"success": bool, "text": str, "provider": str, "rate_limited": bool, "error": str}
        """
        if result["status_code"] == 429:
            return {
                "success": False,
                "text": None,
                "provider": provider,
                "rate_limited": True,
                "error": "Rate limited"
            }
        
        if not result["success"]:
            return {
                "success": False,
                "text": None,
                "provider": provider,
                "rate_limited": False,
                "error": result.get("error", "Unknown error")
            }
        
        # Provider-specific text extraction (override in subclass if needed)
        text = self._extract_text(result["data"], provider)
        
        if not text:
            return {
                "success": False,
                "text": None,
                "provider": provider,
                "rate_limited": False,
                "error": "Empty response"
            }
        
        return {
            "success": True,
            "text": text,
            "provider": provider,
            "rate_limited": False,
            "error": None
        }
    
    def _extract_text(self, data: dict, provider: str) -> str:
        """Extract text from API response. Override for custom providers."""
        if not data:
            return None
        
        # OpenAI-compatible format (Groq, Cerebras, Together, etc.)
        if "choices" in data:
            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                pass
        
        # Gemini format
        if "candidates" in data:
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                pass
        
        return None
    
    # ═══════════════════════════════════════════════════════════════
    # RETRY LOGIC
    # ═══════════════════════════════════════════════════════════════
    
    def _call_with_retry(self, call_fn, provider: str, max_retries: int = 2) -> dict:
        """
        Call a function with exponential backoff retry.
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            if attempt > 0:
                wait_time = 2 ** attempt  # 2, 4, 8 seconds
                log_debug(self.NAME, f"Retry {attempt}/{max_retries} in {wait_time}s...")
                time.sleep(wait_time)
            
            try:
                result = call_fn()
                
                if result.get("success"):
                    return result
                
                if result.get("rate_limited"):
                    return result  # Don't retry rate limits
                
                last_error = result.get("error", "Unknown error")
                
            except Exception as e:
                last_error = str(e)
        
        return {
            "success": False,
            "text": None,
            "provider": provider,
            "rate_limited": False,
            "error": f"All retries failed: {last_error}"
        }
    
    # ═══════════════════════════════════════════════════════════════
    # MAIN API INTERFACE (override in subclasses)
    # ═══════════════════════════════════════════════════════════════
    
    def call_api(self, prompt: str) -> dict:
        """
        Call AI API with fallback chain.
        Override in subclasses to implement specific provider logic.
        
        Returns: {
            "success": bool,
            "text": str or None,
            "provider": str,
            "rate_limited": bool,
            "error": str or None
        }
        """
        raise NotImplementedError("Subclasses must implement call_api()")
    
    def build_prompt(self, topic: str, agent_name: str = None) -> str:
        """
        Build the prompt for research.
        Override in subclasses.
        """
        raise NotImplementedError("Subclasses must implement build_prompt()")
    
    # ═══════════════════════════════════════════════════════════════
    # RESEARCH EXECUTION
    # ═══════════════════════════════════════════════════════════════
    
    def research(self, topic: str) -> dict:
        """
        Execute research on a topic.
        
        Returns: {
            "success": bool,
            "content": str or None,
            "provider": str,
            "rate_limited": bool,
            "error": str or None
        }
        """
        # Check if rate limited
        if self.is_rate_limited():
            mins = self.minutes_until_reset()
            return {
                "success": False,
                "content": None,
                "provider": None,
                "rate_limited": True,
                "error": f"Rate limited for {mins} more minutes"
            }
        
        # Build prompt
        prompt = self.build_prompt(topic, agent_name=self.NAME)
        
        # Call API
        result = self.call_api(prompt)
        
        # Handle rate limit
        if result.get("rate_limited"):
            self.set_rate_limited(provider=result.get("provider"))
            return {
                "success": False,
                "content": None,
                "provider": result.get("provider"),
                "rate_limited": True,
                "error": "Rate limited"
            }
        
        # Handle error
        if not result.get("success"):
            update_agent_status(self.NAME, "error", tasks_failed=1)
            return {
                "success": False,
                "content": None,
                "provider": result.get("provider"),
                "rate_limited": False,
                "error": result.get("error", "Unknown error")
            }
        
        # Save successful result
        self._current_provider = result.get("provider")
        self.save_to_db(topic, result["text"])
        
        return {
            "success": True,
            "content": result["text"],
            "provider": result.get("provider"),
            "rate_limited": False,
            "error": None
        }


class OpenAICompatibleMixin:
    """
    Mixin for OpenAI-compatible APIs (Groq, Cerebras, Together, etc.)
    """
    
    def _call_openai_compatible(
        self, 
        prompt: str, 
        endpoint: str, 
        api_key: str, 
        model: str, 
        provider_name: str,
        system_message: str = None,
        max_tokens: int = 1500,
        temperature: float = 0.7
    ) -> dict:
        """Generic caller for OpenAI-compatible endpoints."""
        
        if not api_key:
            return {
                "success": False,
                "text": None,
                "provider": provider_name,
                "rate_limited": False,
                "error": f"No API key for {provider_name}"
            }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        result = self._make_request("POST", endpoint, headers=headers, json=payload)
        return self._handle_response(result, provider_name)


class GeminiMixin:
    """
    Mixin for Google Gemini API.
    """
    
    def _call_gemini(
        self,
        prompt: str,
        api_key: str,
        model: str = "gemini-2.0-flash",
        max_tokens: int = 1500,
        temperature: float = 0.7
    ) -> dict:
        """Call Gemini API."""
        
        if not api_key:
            return {
                "success": False,
                "text": None,
                "provider": "gemini",
                "rate_limited": False,
                "error": "No Gemini API key"
            }
        
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature
            }
        }
        
        result = self._make_request(
            "POST", 
            f"{endpoint}?key={api_key}", 
            headers=headers, 
            json=payload
        )
        
        return self._handle_response(result, "gemini")
