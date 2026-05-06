"""
AGENT 1: MARKET SCOUT
Primary: Google Gemini
Fallback: Groq (Llama 3.3 70B)
Auto-switches when rate limited — never stops working!
"""

import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log
from utils.memory_context import get_context_for_prompt
from utils.web_search import search_web, search_reddit, format_search_results


class MarketScout(BaseAgent):
    NAME = "market_scout"
    PROVIDER = "Google Gemini + Groq Fallback"

    def __init__(self):
        super().__init__()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.model = "gemini-2.0-flash"
        self.gemini_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        self.groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.groq_model = "llama-3.3-70b-versatile"

    def build_prompt(self, topic: str) -> str:
        memory_context = get_context_for_prompt(topic)
        web_results = search_web(f"{topic} app complaints 2026")
        reddit_results = search_reddit(topic)
        web_context = format_search_results(web_results + reddit_results)

        return f"""You are a market research expert finding SPECIFIC, NON-OBVIOUS market insights.

{memory_context}

## REAL WEB DATA:
{web_context}

RESEARCH: {topic}

## New Market Findings
[Specific apps, real complaints, real numbers — nothing generic]

## Top Existing Solutions & Specific Weaknesses
[Real app names with evidence-backed weaknesses]

## Real User Complaints
[Direct from web data — real language, real frustrations]

## Untapped Market Gaps
[Specific gaps with evidence — why does this gap exist?]

## Verdict
[What's genuinely new and worth noting?]"""

    def _call_gemini(self, prompt: str) -> dict:
        if not self.gemini_key:
            return {"success": False, "error": "No Gemini key"}
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.7}
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
                {"role": "system", "content": "Expert market researcher. Be specific, avoid generic statements."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1500,
            "temperature": 0.7
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

    def call_api(self, prompt: str) -> dict:
        # Try Gemini first
        log(self.NAME, "Trying Gemini...")
        result = self._call_gemini(prompt)
        if result["success"]:
            log(self.NAME, "✓ Gemini responded")
            return result

        # Gemini failed — try Groq fallback
        if result.get("rate_limited"):
            log(self.NAME, "Gemini rate limited → switching to Groq fallback")
        else:
            log(self.NAME, f"Gemini failed ({result.get('error')}) → switching to Groq fallback")

        result = self._call_groq(prompt)
        if result["success"]:
            log(self.NAME, "✓ Groq fallback responded")
            return result

        # Both failed
        if result.get("rate_limited"):
            log(self.NAME, "Both Gemini and Groq rate limited")
            return {"success": False, "rate_limited": True}

        return {"success": False, "error": "Both providers failed"}
