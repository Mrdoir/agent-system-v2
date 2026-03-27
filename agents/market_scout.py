"""
AGENT 1: MARKET SCOUT
Uses: Google Gemini (free, 1000 req/day on Flash)
Job: Find competitors, user complaints, market gaps
Now reads memory before researching — gets smarter every cycle
"""

import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log
from utils.memory_context import get_context_for_prompt


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

        return f"""You are a market research expert finding SPECIFIC, NON-OBVIOUS market insights.

{memory_context}

NOW RESEARCH THIS TOPIC: {topic}

RULES:
- Only report what is NOT already in the knowledge base above
- Be specific: name real apps, real complaints, real numbers
- No vague statements like "users want better UX"
- If a point is already covered above, skip it entirely

Provide your research in this format:

## NEW Market Findings (not in knowledge base)
[Only genuinely new findings. Real app names, real user complaints with specifics]

## Top Existing Solutions & Their SPECIFIC Weaknesses
[Name 3-5 real apps. For each: one specific weakness with evidence]

## Specific User Complaints (with source if possible)
[Real complaints, real language users use. Not generic.]

## Untapped Market Gaps
[Specific gaps with evidence — why does this gap exist? Who is affected?]

## Verdict
[Is there something genuinely new here worth noting?]

If you find nothing new beyond what's already known, say: "No new findings this cycle." """

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
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
