"""
AGENT 2: TREND ANALYST
Primary: Groq (Llama 3.3 70B)
Fallback: Gemini Flash
Auto-switches when rate limited!
"""

import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log
from utils.memory_context import get_context_for_prompt
from utils.web_search import search_web, format_search_results


class TrendAnalyst(BaseAgent):
    NAME = "trend_analyst"
    PROVIDER = "Groq + Gemini Fallback"

    def __init__(self):
        super().__init__()
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.groq_model = "llama-3.3-70b-versatile"
        self.gemini_model = "gemini-2.0-flash"
        self.gemini_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"

    def build_prompt(self, topic: str) -> str:
        memory_context = get_context_for_prompt(topic)
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

    def _call_groq(self, prompt: str) -> dict:
        if not self.groq_key:
            return {"success": False, "error": "No Groq key"}
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.groq_model,
            "messages": [
                {"role": "system", "content": "Sharp trend analyst. Be specific, use web data provided."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1500,
            "temperature": 0.6
        }
        try:
            resp = requests.post(self.groq_endpoint, headers=headers, json=payload, timeout=30)
            if resp.status_code == 429:
                return {"success": False, "rate_limited": True}
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}"}
            text = resp.json()["choices"][0]["message"]["content"]
            return {"success": True, "text": text, "provider": "groq"}
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
        # Try Groq first
        log(self.NAME, "Trying Groq...")
        result = self._call_groq(prompt)
        if result["success"]:
            log(self.NAME, "✓ Groq responded")
            return result

        # Groq failed — try Gemini fallback
        if result.get("rate_limited"):
            log(self.NAME, "Groq rate limited → switching to Gemini fallback")
        else:
            log(self.NAME, f"Groq failed → switching to Gemini fallback")

        result = self._call_gemini(prompt)
        if result["success"]:
            log(self.NAME, "✓ Gemini fallback responded")
            return result

        if result.get("rate_limited"):
            log(self.NAME, "Both Groq and Gemini rate limited")
            return {"success": False, "rate_limited": True}

        return {"success": False, "error": "Both providers failed"}
