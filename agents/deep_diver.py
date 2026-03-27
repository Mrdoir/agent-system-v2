"""
AGENT 3: DEEP DIVER
Uses: Nvidia Nemotron via OpenRouter (free)
Now with REAL WEB SEARCH — grounds strategy in real data!
"""

import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log
from utils.memory_context import get_context_for_prompt
from utils.web_search import search_web, format_search_results


class DeepDiver(BaseAgent):
    NAME = "deep_diver"
    PROVIDER = "Nvidia Nemotron via OpenRouter"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "nvidia/nemotron-3-super-120b-a12b:free"

    def build_prompt(self, topic: str) -> str:
        memory_context = get_context_for_prompt(topic)
        web_results = search_web(f"{topic} why fails opportunity 2026")
        web_context = format_search_results(web_results)

        return f"""You are a deep strategic analyst with real web data.

{memory_context}

## REAL WEB DATA:
{web_context}

DEEP DIVE: {topic}

Go deeper than surface level. Use web data for evidence.

## Deeper Why Analysis
[Root causes from web evidence — not symptoms]

## What Previous Research Missed
[New angle not in knowledge base]

## Hidden Opportunities
[From combining web data with known pain points]

## Why Current Solutions REALLY Fail
[Structural reasons with evidence]

## Unfair Advantage Needed
[What gives a new entrant an uncopyable edge?]

## 3 Contrarian Takes
[What does everyone believe that's wrong?]

## MVP Concept
[Simplest possible product — be very specific]"""

    def call_api(self, prompt: str) -> dict:
        if not self.api_key:
            return {"success": False, "error": "OPENROUTER_API_KEY not set"}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://agent-system.local",
            "X-Title": "Research Agent System"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Deep strategic analyst. Use web data for evidence."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2000,
            "temperature": 0.5
        }
        try:
            resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=45)
            if resp.status_code == 429:
                return {"success": False, "rate_limited": True}
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            text = resp.json()["choices"][0]["message"]["content"]
            return {"success": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}
