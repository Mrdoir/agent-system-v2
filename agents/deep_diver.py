"""
AGENT 3: DEEP DIVER
Uses: OpenRouter (dual key rotation) + Groq fallback
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
    PROVIDER = "OpenRouter dual key + Groq fallback"

    def __init__(self):
        super().__init__()
        self.api_keys = [
            k for k in [
                os.getenv("OPENROUTER_API_KEY", ""),
                os.getenv("OPENROUTER_API_KEY_2", ""),
            ] if k
        ]
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"
        self.groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.openrouter_models = [
            "nvidia/nemotron-3-super-120b-a12b:free",
            "meta-llama/llama-3.3-70b-instruct:free",
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

    def call_openrouter(self, prompt: str) -> dict:
        if not self.api_keys:
            return {"success": False, "error": "No OpenRouter keys"}

        # Try every combination of key + model
        for api_key in self.api_keys:
            for model in self.openrouter_models:
                try:
                    log("deep_diver", f"Trying key ...{api_key[-6:]} + model: {model}")
                    resp = requests.post(
                        self.endpoint,
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://agent-system.local",
                            "X-Title": "Research Agent System"
                        },
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": "Deep strategic analyst. Use web data for evidence."},
                                {"role": "user", "content": prompt}
                            ],
                            "max_tokens": 1500,
                            "temperature": 0.5
                        },
                        timeout=60
                    )
                    if resp.status_code == 429:
                        log("deep_diver", f"Rate limited on key ...{api_key[-6:]} + {model}, trying next...")
                        continue
                    if resp.status_code != 200:
                        log("deep_diver", f"Failed: HTTP {resp.status_code}")
                        continue
                    data = resp.json()
                    if "choices" not in data:
                        log("deep_diver", f"Bad response: {data}")
                        continue
                    text = data["choices"][0]["message"]["content"]
                    log("deep_diver", f"Success with key ...{api_key[-6:]} + {model}")
                    return {"success": True, "text": text}
                except Exception as e:
                    log("deep_diver", f"Error: {e}")
                    continue

        return {"success": False, "error": "All OpenRouter key+model combos failed"}

    def call_groq(self, prompt: str) -> dict:
        if not self.groq_key:
            return {"success": False, "error": "No Groq key"}
        try:
            log("deep_diver", "Trying Groq fallback...")
            resp = requests.post(
                self.groq_endpoint,
                headers={
                    "Authorization": f"Bearer {self.groq_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": "Deep strategic analyst. Use web data for evidence."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.5
                },
                timeout=30
            )
            if resp.status_code == 429:
                return {"success": False, "rate_limited": True}
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}"}
            text = resp.json()["choices"][0]["message"]["content"]
            log("deep_diver", "Groq fallback succeeded!")
            return {"success": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def call_api(self, prompt: str) -> dict:
        # Try all OpenRouter key+model combos first
        result = self.call_openrouter(prompt)
        if result["success"]:
            return result

        # Groq as final fallback
        log("deep_diver", "All OpenRouter failed, falling back to Groq...")
        return self.call_groq(prompt)
