"""
AGENT 2: TREND ANALYST
Uses: Groq (free tier, fast)
Job: Spot emerging trends, timing signals
Now reads memory before researching — avoids repeating old trends
"""

import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log
from utils.memory_context import get_context_for_prompt


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

        return f"""You are a sharp trend analyst. Your job is to find EMERGING trends that others haven't spotted yet.

{memory_context}

NOW ANALYZE TRENDS FOR: {topic}

RULES:
- Only report trends NOT already in the knowledge base above
- Focus on signals from the LAST 3-6 months specifically
- Give evidence: numbers, growth rates, real examples
- Skip any trend already documented above

Format:

## NEW Trend Signals (not previously documented)
[Only trends not in knowledge base. Include growth signals, timing, evidence]

## Why NOW Matters
[What specifically changed in the last 6 months that makes this topic timely?]

## Who Is Driving This (be specific)
[Which exact user segment? Age, profession, behavior — be precise]

## 12-Month Prediction
[Specific prediction with reasoning — not generic "AI will grow"]

## Contrarian Take
[What does everyone get wrong about this trend?]

## Build Timing Verdict
[Specific window: too early / perfect timing / too late? Why?]

If nothing new beyond existing knowledge: say "Trends already documented. No new signals this cycle." """

    def call_api(self, prompt: str) -> dict:
        if not self.api_key:
            return {"success": False, "error": "GROQ_API_KEY not set"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a sharp trend analyst. Be specific, avoid generic statements."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1500,
            "temperature": 0.6
        }

        try:
            resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=30)
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
