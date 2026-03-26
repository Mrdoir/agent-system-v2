"""
AGENT 1: MARKET SCOUT
Uses: Google Gemini (free, 1000 req/day on Flash)
Job: Find competitors, user complaints, market gaps
"""

import os
import json
import requests
from agents.base_agent import BaseAgent
from utils.logger import log


class MarketScout(BaseAgent):
    NAME = "market_scout"
    PROVIDER = "Google Gemini"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = "gemini-1.5-flash"  # Free tier: 1000 req/day
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def build_prompt(self, topic: str) -> str:
        return f"""You are a market research expert. Research the following topic and provide a structured analysis.

TOPIC: {topic}

Provide your research in this exact format:

## Market Overview
[2-3 sentences on current state of this market/space]

## Top Existing Solutions
[List 3-5 existing apps/tools with their main strengths]

## Key User Complaints
[List the most common complaints users have about existing solutions - be specific]

## Market Gaps & Opportunities
[What is missing? What could be built better? Be specific about opportunities]

## Competitive Moat Ideas
[What would make a new entrant hard to copy or beat?]

## Verdict
[1 paragraph: Is this worth building in? Why or why not?]

Be specific, data-driven, and actionable. Focus on real opportunities."""

    def call_api(self, prompt: str) -> dict:
        if not self.api_key:
            return {"success": False, "error": "GEMINI_API_KEY not set in .env"}

        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.7}
        }

        try:
            resp = requests.post(
                f"{self.endpoint}?key={self.api_key}",
                headers=headers,
                json=payload,
                timeout=30
            )

            if resp.status_code == 429:
                log(self.NAME, "Rate limit hit (429)")
                return {"success": False, "rate_limited": True}

            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return {"success": True, "text": text}

        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
