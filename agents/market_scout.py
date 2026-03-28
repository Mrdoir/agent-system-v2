"""
AGENT 1: MARKET SCOUT
Uses: Gemini 2.5 Flash-Lite + Groq fallback (free)
Now with REAL WEB SEARCH + full article reading!
"""

import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log
from utils.memory_context import get_context_for_prompt
from utils.web_search import search_and_fetch, search_reddit, format_search_results


class MarketScout(BaseAgent):
    NAME = "market_scout"
    PROVIDER = "Gemini + Groq fallback"

    def __init__(self):
        super().__init__()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.gemini_model = "gemini-2.5-flash-lite"
        self.gemini_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
        self.groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.groq_model = "llama-3.3-70b-versatile"

    def build_prompt(self, topic: str) -> str:
        memory_context = get_context_for_prompt(topic)
        web_results = search_and_fetch(f"{topic} app complaints 2026", max_results=3)
        reddit_results = search_reddit(topic)
        web_context = format_search_results(web_results, use_full_content=True)
        web_context += "\n\n## REDDIT DISCUSSIONS:\n" + format_search_results(reddit_results)

        return f"""You are a market research expert. You have access to REAL current web data below.

{memory_context}

## REAL WEB DATA (use this for specific, current insights):
{web_context}

NOW RESEARCH: {topic}

Use the web data above to find SPECIFIC, REAL insights. Quote real sources when possible.

## New Market Findings
[Based on real web data above — specific apps, real complaints, real numbers]

## Top Existing Solutions & Their SPECIFIC Weaknesses
[Real apps with evidence-backed weaknesses]

## Real User Complaints (from web data)
[Direct from web results — real language, real frustrations]

## Untapped Market Gaps
[Specific gaps with evidence from web data]

## Verdict
[What's genuinely worth noting based on real current data?]"""

    def call_gemini(self, prompt: str) -> dict:
        if not self.gemini_key:
            return {"success": False, "error": "No Gemini key"}
        try:
            resp = requests.post(
                f"{self.gemini_endpoint}?key={self.gemini_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.7}
                },
                timeout=30
            )
            if resp.status_code == 429:
                log("market_scout", "Gemini rate limited, switching to Groq...")
                return {"success": False, "rate_limited": True}
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}"}
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            log("market_scout", "Gemini succeeded")
            return {"success": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def call_groq(self, prompt: str) -> dict:
        if not self.groq_key:
            return {"success": False, "error": "No Groq key"}
        try:
            resp = requests.post(
                self.groq_endpoint,
                headers={
                    "Authorization": f"Bearer {self.groq_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.groq_model,
                    "messages": [
                        {"role": "system", "content": "You are a market research expert."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.7
                },
                timeout=30
            )
            if resp.status_code == 429:
                return {"success": False, "rate_limited": True}
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}"}
            text = resp.json()["choices"][0]["message"]["content"]
            log("market_scout", "Groq fallback succeeded")
            return {"success": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def call_api(self, prompt: str) -> dict:
        result = self.call_gemini(prompt)
        if result["success"]:
            return result
        log("market_scout", "Falling back to Groq...")
        return self.call_groq(prompt)
