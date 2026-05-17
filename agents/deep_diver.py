"""
AGENT 3: DEEP DIVER
Primary:   Nvidia Nemotron via OpenRouter
Fallback1: Groq QwQ-32B (reasoning model)
Fallback2: Cerebras (Llama 3.3 70B — separate quota)
Fallback3: Gemini Flash
Order: Nemotron → QwQ → Cerebras → Gemini
"""

import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log
from utils.memory_context import get_context_for_prompt
from utils.web_search import search_web, format_search_results


class DeepDiver(BaseAgent):
    NAME = "deep_diver"
    PROVIDER = "Nemotron + QwQ + Cerebras + Gemini Fallbacks"

    def __init__(self):
        super().__init__()
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_key_2 = os.getenv("OPENROUTER_API_KEY_2", "")
        self.openrouter_key_3 = os.getenv("OPENROUTER_API_KEY_3", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.cerebras_key = os.getenv("CEREBRAS_API_KEY", "")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")

        self.openrouter_endpoint = "https://openrouter.ai/api/v1/chat/completions"
        self.groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.cerebras_endpoint = "https://api.cerebras.ai/v1/chat/completions"
        self.gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

        self.primary_model = "nvidia/nemotron-3-super-120b-a12b:free"
        self.groq_model = "qwen-qwq-32b"
        self.cerebras_model = "llama-3.3-70b"

    def build_prompt(self, topic: str, agent_name: str = None) -> str:
        memory_context = get_context_for_prompt(topic, agent_name=agent_name or self.NAME)
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
        """Try all 3 OpenRouter keys in sequence."""
        keys = [k for k in [self.openrouter_key, self.openrouter_key_2, self.openrouter_key_3] if k]
        if not keys:
            return {"success": False, "error": "No OpenRouter keys"}
        for i, key in enumerate(keys):
            try:
                log(self.NAME, f"Trying OpenRouter key {i+1}...")
                resp = requests.post(
                    self.openrouter_endpoint,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://agent-system.local",
                        "X-Title": "Research Agent System"
                    },
                    json={
                        "model": self.primary_model,
                        "messages": [
                            {"role": "system", "content": "Deep strategic analyst. Think rigorously, go beyond surface level."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 2000,
                        "temperature": 0.5
                    },
                    timeout=45
                )
                if resp.status_code == 429:
                    log(self.NAME, f"OpenRouter key {i+1} rate limited, trying next...")
                    continue
                if resp.status_code != 200:
                    log(self.NAME, f"OpenRouter key {i+1} failed: HTTP {resp.status_code}")
                    continue
                text = resp.json()["choices"][0]["message"]["content"]
                log(self.NAME, f"✓ OpenRouter key {i+1} responded")
                return {"success": True, "text": text, "provider": f"nemotron-key{i+1}"}
            except Exception as e:
                log(self.NAME, f"OpenRouter key {i+1} error: {e}")
                continue
        return {"success": False, "rate_limited": True}

    def _call_openai_compat(self, prompt: str, endpoint: str, api_key: str, model: str, provider_name: str, system_msg: str = None) -> dict:
        """Generic caller for OpenAI-compatible endpoints (Groq, Cerebras, etc.)"""
        if not api_key:
            return {"success": False, "error": f"No {provider_name} key"}
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        system = system_msg or "Deep strategic analyst. Think rigorously, go beyond surface level."
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2000,
            "temperature": 0.5
        }
        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=60)
            if resp.status_code == 429:
                return {"success": False, "rate_limited": True}
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}"}
            text = resp.json()["choices"][0]["message"]["content"]
            return {"success": True, "text": text, "provider": provider_name}
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
        # 1. Try Nemotron
        log(self.NAME, "Trying Nemotron...")
        result = self._call_openrouter(prompt)
        if result["success"]:
            log(self.NAME, "✓ Nemotron responded")
            return result

        # 2. Nemotron failed — try QwQ-32B reasoning model
        reason = "rate limited" if result.get("rate_limited") else "failed"
        log(self.NAME, f"Nemotron {reason} → trying QwQ-32B (reasoning model)...")
        result = self._call_openai_compat(
            prompt, self.groq_endpoint, self.groq_key, self.groq_model, "qwq-32b",
            system_msg="You are a deep strategic analyst with strong reasoning. Think step by step before answering."
        )
        if result["success"]:
            log(self.NAME, "✓ QwQ-32B responded")
            return result

        # 3. QwQ failed — try Cerebras
        reason = "rate limited" if result.get("rate_limited") else "failed"
        log(self.NAME, f"QwQ {reason} → trying Cerebras fallback...")
        result = self._call_openai_compat(
            prompt, self.cerebras_endpoint, self.cerebras_key, self.cerebras_model, "cerebras"
        )
        if result["success"]:
            log(self.NAME, "✓ Cerebras fallback responded")
            return result

        # 4. Cerebras failed — last resort Gemini
        reason = "rate limited" if result.get("rate_limited") else "failed"
        log(self.NAME, f"Cerebras {reason} → trying Gemini last resort...")
        result = self._call_gemini(prompt)
        if result["success"]:
            log(self.NAME, "✓ Gemini last resort responded")
            return result

        log(self.NAME, "⚠️ All providers (Nemotron, QwQ, Cerebras, Gemini) exhausted")
        return {"success": False, "rate_limited": True}
