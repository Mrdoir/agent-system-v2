"""
AGENT 3: DEEP DIVER
Uses: OpenRouter → DeepSeek R1 (free tier available, strong reasoning)
Job: Deep analysis, why things fail, how to build smarter
"""

import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log


class DeepDiver(BaseAgent):
    NAME = "deep_diver"
    PROVIDER = "DeepSeek R1 via OpenRouter"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "deepseek/deepseek-r1:free"  # Free on OpenRouter

    def build_prompt(self, topic: str) -> str:
        return f"""You are a deep research analyst. Your job is to go beyond surface-level analysis 
and uncover the real strategic insights that others miss.

RESEARCH TOPIC: {topic}

Conduct a deep analysis using this format:

## Core Problem Being Solved
[What fundamental human/business problem does this topic address?]

## Why Most Attempts Fail
[What mistakes do builders/companies repeatedly make in this space?]

## The Insight Others Miss
[What non-obvious insight would give a new entrant an edge?]

## Monetization Models That Work
[What revenue models succeed here and why? Include real examples if possible]

## Tech Stack Considerations
[What technical choices matter most for building in this space?]

## Unfair Advantage Needed
[What would a founder need to have (network, data, skill) to win here?]

## Build vs Buy vs Partner
[What should be built from scratch, what should use existing tools, what needs partnerships?]

## 3 Contrarian Takes
[What does conventional wisdom get wrong about this space?]

Go deep. Be specific. Think like a first-principles builder."""

    def call_api(self, prompt: str) -> dict:
        if not self.api_key:
            return {"success": False, "error": "OPENROUTER_API_KEY not set in .env"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://agent-system.local",
            "X-Title": "Research Agent System"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a deep strategic analyst. Think rigorously and go beyond surface level."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2000,
            "temperature": 0.5
        }

        try:
            resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=45)

            if resp.status_code == 429:
                log(self.NAME, "Rate limit hit (429)")
                return {"success": False, "rate_limited": True}

            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return {"success": True, "text": text}

        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
