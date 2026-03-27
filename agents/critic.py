"""
AGENT 4: CRITIC
Uses: Groq (fast, free) 
Job: Score research quality, filter generic insights, rank findings
Runs AFTER the 3 research agents to improve output quality
"""
import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log
from utils.database import save_result, get_do_not_repeat

class CriticAgent(BaseAgent):
    NAME = "critic"
    PROVIDER = "Groq (Llama 3.3 70B)"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile"

    def build_prompt(self, topic: str, research_content: str = "") -> str:
        do_not_repeat = get_do_not_repeat()
        dnr_list = "\n".join(f"- {p}" for p in do_not_repeat[:20]) if do_not_repeat else "None yet"
        return f"""You are a brutal research critic. Your job is to evaluate AI research outputs and filter out generic, useless insights.

TOPIC: {topic}

RESEARCH TO EVALUATE:
{research_content}

OVERUSED PATTERNS TO PENALIZE (mark these as WEAK):
{dnr_list}

Evaluate this research and respond in this EXACT format:

## QUALITY SCORE: [0-10]
[One sentence explaining the score]

## STRONG INSIGHTS (keep these)
[List only genuinely specific, actionable, non-obvious findings. If none, say "None found."]

## WEAK INSIGHTS (cut these)
[List generic, vague, or obvious statements that add no value]

## TOP 3 ACTIONABLE TAKEAWAYS
[The 3 most useful, specific things someone could act on from this research]

## PATTERNS TO ADD TO DO-NOT-REPEAT LIST
[List 2-3 generic phrases from this output that should never appear again]

## VERDICT
[1 sentence: Is this research useful? Why?]

Be ruthless. Generic = worthless. Specific = valuable."""

    def evaluate(self, topic: str, research_content: str) -> dict:
        """Evaluate research and return score + filtered content."""
        if self.is_rate_limited():
            return {"success": False, "rate_limited": True}

        if not research_content or len(research_content.strip()) < 50:
            return {"success": False, "error": "No research content provided"}

        prompt = self.build_prompt(topic, research_content)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a ruthless research quality critic. Be specific and harsh."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1000,
            "temperature": 0.3
        }
        try:
            resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=30)
            if resp.status_code == 429:
                self.set_rate_limited(reset_minutes=30)
                return {"success": False, "rate_limited": True}
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}"}
            text = resp.json()["choices"][0]["message"]["content"]
            score = 5
            for line in text.split("\n"):
                if "QUALITY SCORE:" in line:
                    try:
                        score = int(''.join(filter(str.isdigit, line.split(":")[-1][:3])))
                        score = min(10, max(0, score))
                    except:
                        pass
            return {"success": True, "text": text, "score": score}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def research(self, topic: str) -> dict:
        """Required by base class — not used directly for critic."""
        return {"success": False, "error": "Use evaluate() instead"}

    def call_api(self, prompt: str) -> dict:
        return {"success": False, "error": "Use evaluate() instead"}
