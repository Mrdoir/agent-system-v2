"""
AGENT 2: TREND ANALYST
Primary:   Groq (Llama 3.3 70B)
Fallback1: Cerebras (Llama 3.3 70B — same model, different quota)
Fallback2: Gemini Flash
Order: Groq → Cerebras → Gemini
"""

import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log
from utils.memory_context import get_context_for_prompt
from utils.web_search import search_web, format_search_results


class TrendAnalyst(BaseAgent):
    NAME = "trend_analyst"
    PROVIDER = "Groq + Cerebras + Gemini Fallback"

    def __init__(self):
        super().__init__()
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.cerebras_key = os.getenv("CEREBRAS_API_KEY", "")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")

        self.groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.groq_model = "llama-3.3-70b-versatile"

        self.cerebras_endpoint = "https://api.cerebras.ai/v1/chat/completions"
        self.cerebras_model = "llama-3.3-70b"

        self.gemini_model = "gemini-2.0-flash"
        self.gemini_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"

    def build_prompt(self, topic: str, agent_name: str = None) -> str:
        memory_context = get_context_for_prompt(topic, agent_name=agent_name or self.NAME)
        web_results = search_web(f"{topic} trend growth 2026")
        web_context = format_search_results(web_results)

        return f"""You are a sharp trend analyst. Find EMERGING trends others haven't spotted.

{memory_context}

## REAL WEB DATA:
{web_context}

ANALYZE TRENDS FOR: {topic}

## New Trend Signals (not previously documented)
[Specific signals with evidence — growth rates, timing]

## Why NOW Matters
[What changed in last 6 months specifically?]

## Who Is Driving This
[Exact user segment — age, profession, behavior]

## 12-Month Prediction
[Specific prediction with reasoning]

## Contrarian Take
[What does everyone get wrong about this trend?]

## Build Timing Verdict
[Too early / perfect / too late? Why?]"""

    def _call_openai_compat(self, prompt: str, endpoint: str, api_key: str, model: str, provider_name: str) -> dict:
        """Generic caller for any OpenAI-compatible endpoint (Groq, Cerebras, Together, etc.)"""
        if not api_key:
            return {"success": False, "error": f"No {provider_name} key"}
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Sharp trend analyst. Be specific, use web data provided."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1500,
            "temperature": 0.6
        }
        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=30)
            if resp.status_code == 429:
                return {"success": False, "rate_limited": True}
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}"}
            text = resp.json()["choices"][0]["message"]["content"]
            return {"success": True, "text": text, "provider": provider_name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _call_gemini(self, prompt: str) -> dict:
        if not self.gemini_key:
            return {"success": False, "error": "No Gemini key"}
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.6}
        }
        try:
            resp = requests.post(
                f"{self.gemini_endpoint}?key={self.gemini_key}",
                headers=headers, json=payload, timeout=30
            )
            if resp.status_code == 429:
                return {"success": False, "rate_limited": True}
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}"}
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return {"success": True, "text": text, "provider": "gemini"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def call_api(self, prompt: str) -> dict:
        # 1. Try Groq
        log(self.NAME, "Trying Groq...")
        result = self._call_openai_compat(
            prompt, self.groq_endpoint, self.groq_key, self.groq_model, "groq"
        )
        if result["success"]:
            log(self.NAME, "✓ Groq responded")
            return result

        # 2. Groq failed — try Cerebras (same Llama model, separate quota)
        reason = "rate limited" if result.get("rate_limited") else "failed"
        log(self.NAME, f"Groq {reason} → trying Cerebras fallback...")
        result = self._call_openai_compat(
            prompt, self.cerebras_endpoint, self.cerebras_key, self.cerebras_model, "cerebras"
        )
        if result["success"]:
            log(self.NAME, "✓ Cerebras fallback responded")
            return result

        # 3. Cerebras failed — try Gemini
        reason = "rate limited" if result.get("rate_limited") else "failed"
        log(self.NAME, f"Cerebras {reason} → trying Gemini fallback...")
        result = self._call_gemini(prompt)
        if result["success"]:
            log(self.NAME, "✓ Gemini fallback responded")
            return result

        # All 3 exhausted
        log(self.NAME, "⚠️ All providers (Groq, Cerebras, Gemini) rate limited or failed")
        return {"success": False, "rate_limited": True}
