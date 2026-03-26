"""
AGENT 2: TREND ANALYST
Uses: Groq (free tier, very fast - 370 tokens/sec)
Job: Spot emerging trends, timing signals, what's growing NOW
"""

import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log


class TrendAnalyst(BaseAgent):
    NAME = "trend_analyst"
    PROVIDER = "Groq (Llama 4)"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "meta-llama/llama-4-scout-17b-16e-instruct"  # Free on Groq

    def build_prompt(self, topic: str) -> str:
        return f"""You are a trend analyst specializing in technology and business trends. 
Your job is to identify what's trending RIGHT NOW and where things are heading.

TOPIC: {topic}

Analyze this topic and respond in this exact format:

## Trend Signal (1-10)
[Score how strong the trend signal is, with reasoning]

## What's Growing Right Now
[Specific signals, behaviors, search trends, or shifts happening in this space]

## Why This Moment Matters
[Why is NOW a good or bad time to enter this space?]

## Who Is Driving Demand
[Demographics, industries, or user types fueling growth]

## 12-Month Outlook
[Where will this space be in 1 year? What changes are coming?]

## Build Timing Verdict
[Should someone build in this space now, wait, or avoid? Why?]

Be specific. Avoid vague statements. Think like a VC analyst."""

    def call_api(self, prompt: str) -> dict:
        if not self.api_key:
            return {"success": False, "error": "GROQ_API_KEY not set in .env"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a sharp trend analyst. Be specific, data-driven, and concise."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1500,
            "temperature": 0.6
        }

        try:
            resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=30)

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
