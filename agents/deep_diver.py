"""
AGENT 3: DEEP DIVER
Uses: OpenRouter → Nvidia Nemotron (free)
Job: Deep strategic analysis, why things fail, how to win
Now reads memory — goes deeper than previous cycles
"""

import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log
from utils.memory_context import get_context_for_prompt


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

        return f"""You are a deep strategic analyst. Your job is to go DEEPER than surface-level research and find insights others miss.

{memory_context}

NOW DEEP DIVE INTO: {topic}

RULES:
- Only explore angles NOT already covered in the knowledge base above
- Go deeper than previous research — if scouts found "what", you find "why" and "how"
- First-principles thinking: question assumptions
- Be specific: real examples, real failures, real opportunities

Format:

## Deeper "Why" Analysis
[Why do the problems in this space actually exist? Root causes, not symptoms]

## What Previous Research Missed
[What angle hasn't been explored yet based on the knowledge base above?]

## Hidden Opportunities
[Specific opportunities that emerge from combining known pain points in new ways]

## Why Current Solutions REALLY Fail
[Not surface reasons — the deep structural reasons incumbents can't fix this]

## The Unfair Advantage Needed
[What would give a new entrant an edge that can't be copied easily?]

## 3 Contrarian Takes
[What does everyone believe that is actually wrong about this space?]

## MVP Concept
[The simplest possible product that would solve the core problem. Be specific.]

If nothing new to add: "Deep analysis complete. No new angles beyond existing knowledge." """

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
                {"role": "system", "content": "You are a deep strategic analyst. Think rigorously, go beyond surface level."},
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
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
