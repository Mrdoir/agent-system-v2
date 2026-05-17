"""
AGENT 1: MARKET SCOUT
Primary:   Google Gemini
Fallback1: Groq (Llama 3.3 70B)
Fallback2: Cerebras (Llama 3.3 70B — separate quota)
Fallback3: Gemini skipped if primary, so chain is:
Order: Gemini → Groq → Cerebras
"""

import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log
from utils.memory_context import get_context_for_prompt
from utils.web_search import search_web, search_reddit, format_search_results


class MarketScout(BaseAgent):
    NAME = "market_scout"
    PROVIDER = "Gemini + Groq + Cerebras Fallback"

    def __init__(self):
        super().__init__()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.groq_key_2 = os.getenv("GROQ_API_KEY_2", "")
        self.cerebras_key = os.getenv("CEREBRAS_API_KEY", "")

        self.model = "gemini-2.0-flash"
        self.gemini_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

        self.groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.groq_model = "llama-3.3-70b-versatile"

        self.cerebras_endpoint = "https://api.cerebras.ai/v1/chat/completions"
        self.cerebras_model = "llama-3.3-70b"

    def build_prompt(self, topic: str, agent_name: str = None) -> str:
        memory_context = get_context_for_prompt(topic, agent_name=agent_name or self.NAME)
        web_results = search_web(f"{topic} app complaints 2026")
        reddit_results = search_reddit(topic)
        web_context = format_search_results(web_results + reddit_results)

        return f"""You are a market research expert finding SPECIFIC, NON-OBVIOUS market insights.

{memory_context}

## REAL WEB DATA:
{web_context}

RESEARCH: {topic}

## New Market Findings
[Specific apps, real complaints, real numbers — nothing generic]

## Top Existing Solutions & Specific Weaknesses
[Real app names with evidence-backed weaknesses]

## Real User Complaints
[Direct from web data — real language, real frustrations]

## Untapped Market Gaps
[Specific gaps with evidence — why does this gap exist?]

## Verdict
[What's genuinely new and worth noting?]"""

    def _call_gemini(self, prompt: str) -> dict:
        if not self.gemini_key:
            return {"success": False, "error": "No Gemini key"}
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.7}
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

    def _call_openai_compat(self, prompt: str, endpoint: str, api_key: str, model: str, provider_name: str) -> dict:
        """Generic caller for OpenAI-compatible endpoints (Groq, Cerebras, etc.)"""
        if not api_key:
            return {"success": False, "error": f"No {provider_name} key"}
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Expert market researcher. Be specific, avoid generic statements."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1500,
            "temperature": 0.7
        }
        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=30)
            if resp.status_code == 429:
                return {"success": False, "rate_limited": True}
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}"}
            text = resp.json()["choices"][0]["message"]["content"]
            return {"success": True, "text": text, "provider": provider_name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def call_api(self, prompt: str) -> dict:
        # 1. Try Gemini
        log(self.NAME, "Trying Gemini...")
        result = self._call_gemini(prompt)
        if result["success"]:
            log(self.NAME, "✓ Gemini responded")
            return result

        # 2. Gemini failed — try Groq
        reason = "rate limited" if result.get("rate_limited") else f"failed ({result.get('error')})"
        log(self.NAME, f"Gemini {reason} → trying Groq fallback...")
        result = self._call_openai_compat(
            prompt, self.groq_endpoint, self.groq_key, self.groq_model, "groq"
        )
        if result["success"]:
            log(self.NAME, "✓ Groq fallback responded")
            return result

        # 3. Groq key 1 failed — try Groq key 2
        reason = "rate limited" if result.get("rate_limited") else "failed"
        log(self.NAME, f"Groq {reason} → trying Groq key 2...")
        result = self._call_openai_compat(
            prompt, self.groq_endpoint, self.groq_key_2, self.groq_model, "groq-key2"
        )
        if result["success"]:
            log(self.NAME, "✓ Groq key 2 responded")
            return result

        # 4. Groq key 2 failed — try Cerebras
        reason = "rate limited" if result.get("rate_limited") else "failed"
        log(self.NAME, f"Groq key 2 {reason} → trying Cerebras fallback...")
        result = self._call_openai_compat(
            prompt, self.cerebras_endpoint, self.cerebras_key, self.cerebras_model, "cerebras"
        )
        if result["success"]:
            log(self.NAME, "✓ Cerebras fallback responded")
            return result

        # All exhausted
        log(self.NAME, "⚠️ All providers (Gemini, Groq, Cerebras) rate limited or failed")
        return {"success": False, "rate_limited": True}
