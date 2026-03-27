"""
AGENT 1: MARKET SCOUT
Uses: Google Gemini (free)
Now with REAL WEB SEARCH — finds actual current data!
"""

import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log
from utils.memory_context import get_context_for_prompt
from utils.web_search import search_web, search_reddit, format_search_results


class MarketScout(BaseAgent):
    NAME = "market_scout"
    PROVIDER = "Google Gemini"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = "gemini-2.0-flash"
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def build_prompt(self, topic: str) -> str:
        memory_context = get_context_for_prompt(topic)

        # Get real web data
        web_results = search_web(f"{topic} app complaints 2026")
        reddit_results = search_reddit(topic)
        web_context = format_search_results(web_results + reddit_results)

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

    def call_api(self, prompt: str) -> dict:
        if not self.api_key:
            return {"success": False, "error": "GEMINI_API_KEY not set"}
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.7}
        }
        try:
            resp = requests.post(
                f"{self.endpoint}?key={self.api_key}",
                headers=headers, json=payload, timeout=30
            )
            if resp.status_code == 429:
                return {"success": False, "rate_limited": True}
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return {"success": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}
