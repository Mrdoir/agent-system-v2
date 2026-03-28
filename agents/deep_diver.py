"""
AGENT 3: DEEP DIVER
Uses: Multiple free models via OpenRouter with fallback
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
    PROVIDER = "OpenRouter (with fallback)"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"
        self.models = [
    "nvidia/nemotron-3-super-120b-a12b:free",  # Best, try first
    "meta-llama/llama-3.3-70b-instruct:free",   # GPT-4 level, very reliable
    "qwen/qwen-2-7b-instruct:free",              # Fast fallback
]
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

        for model in self.models:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "Deep strategic analyst. Use web data for evidence."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.5
            }
            try:
                log("deep_diver", f"Trying model: {model}")
                resp = requests.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                if resp.status_code == 429:
                    log("deep_diver", f"Model {model} rate limited, trying next...")
                    continue
                if resp.status_code != 200:
                    log("deep_diver", f"Model {model} failed: HTTP {resp.status_code}")
                    continue
                data = resp.json()
                if "choices" not in data:
                    log("deep_diver", f"Model {model} bad response: {data}")
                    continue
                text = data["choices"][0]["message"]["content"]
                log("deep_diver", f"Success with model: {model}")
                return {"success": True, "text": text}
            except Exception as e:
                log("deep_diver", f"Model {model} error: {e}")
                continue

        return {"success": False, "error": "All models failed"}
