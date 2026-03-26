"""
AGENT 5: MEMORY / SYNTHESIZER
Uses: Gemini Flash (free, high volume)
Job: Compare new findings with old ones, extract novel patterns,
     build a growing knowledge base, prevent repetition
"""

import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log
from utils.database import (
    get_recent_contents, get_insights, save_insight,
    add_do_not_repeat, get_do_not_repeat
)


class MemoryAgent(BaseAgent):
    NAME = "memory"
    PROVIDER = "Google Gemini Flash"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = "gemini-2.0-flash"
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def build_synthesis_prompt(self, new_content: str, existing_insights: list, do_not_repeat: list) -> str:
        existing_text = "\n---\n".join([
            f"[{i['created_at'][:10]}] {i['content'][:300]}"
            for i in existing_insights[:5]
        ]) if existing_insights else "No previous insights yet."

        dnr_text = "\n".join(f"- {p}" for p in do_not_repeat[:15]) if do_not_repeat else "None yet."

        return f"""You are a research memory synthesizer. Your job is to compare new research with what's already been found, extract only NOVEL patterns, and build a growing knowledge base.

NEW RESEARCH:
{new_content[:2000]}

EXISTING KNOWLEDGE BASE (what we already know):
{existing_text}

PATTERNS TO NEVER REPEAT:
{dnr_text}

Your task:

## NOVELTY CHECK
[Is this new research adding anything genuinely new? Yes/No + why]

## NEW PATTERNS FOUND
[List ONLY patterns NOT seen before in the knowledge base. Be specific. If nothing new, say "Nothing new."]

## UPDATED KNOWLEDGE BASE ENTRY
[Write a 3-5 bullet point summary of the most important UNIQUE insights to add to memory. Focus on:
- Specific pain points with real user language
- Underserved niches with evidence
- Market gaps that keep appearing
Skip anything generic.]

## NOVELTY SCORE: [0-10]
[How novel is this compared to what we already know?]

## PATTERNS TO BLACKLIST
[2-3 generic phrases from this research to add to do-not-repeat list]

Only output what's genuinely new and valuable."""

    def synthesize(self, new_content: str, topic: str) -> dict:
        """Compare new research with memory, extract novel insights."""
        if self.is_rate_limited():
            return {"success": False, "rate_limited": True}

        existing_insights = get_insights(limit=10)
        do_not_repeat = get_do_not_repeat()

        prompt = self.build_synthesis_prompt(new_content, existing_insights, do_not_repeat)

        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 1000, "temperature": 0.3}
        }

        try:
            resp = requests.post(
                f"{self.endpoint}?key={self.api_key}",
                headers=headers,
                json=payload,
                timeout=30
            )

            if resp.status_code == 429:
                self.set_rate_limited(reset_minutes=60)
                return {"success": False, "rate_limited": True}

            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}"}

            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]

            # Extract novelty score
            novelty_score = 5
            for line in text.split("\n"):
                if "NOVELTY SCORE:" in line:
                    try:
                        novelty_score = int(''.join(filter(str.isdigit, line.split(":")[-1][:3])))
                        novelty_score = min(10, max(0, novelty_score))
                    except:
                        pass

            # Save to knowledge base if novel enough
            if novelty_score >= 5:
                save_insight(text, [topic], novelty_score)
                log(self.NAME, f"Saved new insight (novelty: {novelty_score}/10)")

            # Extract and save blacklist patterns
            in_blacklist = False
            for line in text.split("\n"):
                if "PATTERNS TO BLACKLIST" in line:
                    in_blacklist = True
                    continue
                if in_blacklist and line.strip().startswith("-"):
                    pattern = line.strip("- ").strip()
                    if len(pattern) > 10:
                        add_do_not_repeat(pattern)

            return {"success": True, "text": text, "novelty_score": novelty_score}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def research(self, topic: str) -> dict:
        return {"success": False, "error": "Use synthesize() instead"}

    def call_api(self, prompt: str) -> dict:
        return {"success": False, "error": "Use synthesize() instead"}

    def build_prompt(self, topic: str) -> str:
        return ""
