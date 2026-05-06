"""
AGENT 3: DEEP DIVER
Primary: Nvidia Nemotron via OpenRouter
Fallback 1: Groq (QwQ-32B reasoning model)
Fallback 2: Gemini Flash
Triple fallback — almost never stops!
"""

import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log
from utils.memory_context import get_context_for_prompt
from utils.web_search import search_web, format_search_results


class DeepDiver(BaseAgent):
    NAME = "deep_diver"
    PROVIDER = "Nemotron + Groq + Gemini Fallbacks"

    def __init__(self):
        super().__init__()
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.openrouter_endpoint = "https://openrouter.ai/api/v1/chat/completions"
        self.groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        self.primary_model = "nvidia/nemotron-3-super-120b-a12b:free"
        self.groq_model = "qwen-qwq-32b"  # Reasoning model on Groq!

    def build_prompt(self, topic: str) -> str:
        memory_context = get_context_for_prompt(topic)
        web_results = search_web(f"{topic} why fails opportunity 2026")
        web_context = format_search_results(web_results)

        return f"""You are a deep strategic analyst. Go beyond surface level. Find what others miss.

{memory_context}

## REAL WEB DATA:
{web_context}

DEEP DIVE: {topic}

## Deeper Why Analysis
[Root causes — not symptoms. Why does this problem actually exist?]

## What Previous Research Missed
[New angle not in knowledge base above]

## Hidden Opportunities
[Specific opportunities from combining pain points in new ways]

## Why Current Solutions REALLY Fail
[Structural reasons incumbents can't fix this]

## Unfair Advantage Needed
[What gives a new entrant an uncopyable edge?]

## 3 Contrarian Takes
[What does everyone believe that's actually wrong?]

## MVP Concept
[Simplest possible product — be very specific about features]"""

    def _call_openrouter(self, prompt: str) -> dict:
        if not self.openrouter_key:
            return {"success": False, "error": "No OpenRouter key"}
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://agent-system.local",
            "X-Title": "Research Agent System"
        }
        payload = {
            "model": self.primary_model,
            "messages": [
                {"role": "system", "content": "Deep strategic analyst. Think rigorously, go beyond surface level."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2000,
            "temperature": 0.5
        }
        try:
            resp = requests.post(self.openrouter_endpoint, headers=headers, json=payload, timeout=45)
            if resp.status_code == 429:
                return {"success": False, "rate_limited": True}
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}"}
            text = resp.json()["choices"][0]["message"]["content"]
            return {"success": True, "text": text, "provider": "nemotron"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _call_groq_reasoning(self, prompt: str) -> dict:
        """Uses QwQ-32B — a reasoning model that thinks before answering!"""
        if not self.groq_key:
            return {"success": False, "error": "No Groq key"}
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.groq_model,
            "messages": [
                {"role": "system", "content": "You are a deep strategic analyst with strong reasoning. Think step by step before answering."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2000,
            "temperature": 0.5
        }
        try:
            resp = requests.post(self.groq_endpoint, headers=headers, json=payload, timeout=60)
            if resp.status_code == 429:
                return {"success": False, "rate_limited": True}
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}"}
            text = resp.json()["choices"][0]["message"]["content"]
            return {"success": True, "text": text, "provider": "qwq-32b-reasoning"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _call_gemini(self, prompt: str) -> dict:
        if not self.gemini_key:
            return {"success": False, "error": "No Gemini key"}
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 2000, "temperature": 0.5}
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

    def call_api(self, prompt: str) -> dict:
        # Try Nemotron first
        log(self.NAME, "Trying Nemotron...")
        result = self._call_openrouter(prompt)
        if result["success"]:
            log(self.NAME, "✓ Nemotron responded")
            return result

        # Nemotron failed — try QwQ-32B reasoning model
        log(self.NAME, "Nemotron failed → trying QwQ-32B (reasoning model)...")
        result = self._call_groq_reasoning(prompt)
        if result["success"]:
            log(self.NAME, "✓ QwQ-32B reasoning model responded")
            return result

        # QwQ failed — try Gemini
        log(self.NAME, "QwQ failed → trying Gemini fallback...")
        result = self._call_gemini(prompt)
        if result["success"]:
            log(self.NAME, "✓ Gemini fallback responded")
            return result

        # All failed
        if result.get("rate_limited"):
            return {"success": False, "rate_limited": True}
        return {"success": False, "error": "All 3 providers failed"}
