"""
AGENT 2: TREND ANALYST
Uses: Groq (free, fast)
Now with REAL WEB SEARCH + full article reading!
"""

import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log
from utils.memory_context import get_context_for_prompt
from utils.web_search import search_and_fetch, search_reddit, format_search_results


class TrendAnalyst(BaseAgent):
    NAME = "trend_analyst"
    PROVIDER = "Groq (Llama 3.3 70B)"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile"

    def build_prompt(self, topic: str) -> str:
        memory_context = get_context_for_prompt(topic)
        web_results = search_and_fetch(f"{topic} trend growth 2026", max_results=3)
        reddit_results = search_reddit(topic)
        web_context = format_search_results(web_results, use_full_content=True)
        web_context += "\n\n## REDDIT DISCUSSIONS:\n" + format_search_results(reddit_results)

        return f"""You are a sharp trend analyst with access to real current web data.

{memory_context}

## REAL CURRENT WEB DATA:
{web_context}

ANALYZE TRENDS FOR: {topic}

Use web data for specific evidence. Only report NEW trends not in knowledge base.

## New Trend Signals
[From web data — specific growth signals with evidence]

## Why NOW Matters
[What changed in last 6 months? Use web data.]

## Who Is Driving This
[Specific user segments with evidence]

## 12-Month Prediction
[Specific, evidence-based prediction]

## Contrarian Take
[What does everyone get wrong?]

## Build Timing Verdict
[Too early / perfect / too late? Why?]"""

    def call_api(self, prompt: str) -> dict:
        if not self.api_key:
            return {"success": False, "error": "GROQ_API_KEY not set"}
        try:
            resp = requests.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "Sharp trend analyst. Be specific, use provided web data."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.6
                },
                timeout=30
            )
            if resp.status_code == 429:
                return {"success": False, "rate_limited": True}
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            text = resp.json()["choices"][0]["message"]["content"]
            return {"success": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}
