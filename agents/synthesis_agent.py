"""
AGENT 6: WEEKLY SYNTHESIS AGENT
Runs every Sunday automatically.
Reads ALL results from the past week, finds patterns,
generates top opportunities and sends to Telegram.
"""

import os
import requests
from datetime import datetime, timedelta
from utils.logger import log
from utils.notifier import send_telegram


class SynthesisAgent:
    NAME = "synthesis"
    PROVIDER = "Groq (Llama 3.3 70B)"

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile"

    def get_weekly_results(self) -> list:
        try:
            from utils.database import get_results
            all_results = get_results(limit=500)
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            return [r for r in all_results if r.get("created_at", "") >= week_ago]
        except Exception as e:
            log(self.NAME, f"Error fetching results: {e}")
            return []

    def get_top_insights(self) -> list:
        try:
            from utils.database import get_insights
            insights = get_insights(limit=20)
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            weekly = [i for i in insights if i.get("created_at", "") >= week_ago]
            return sorted(weekly, key=lambda x: x.get("novelty_score", 0), reverse=True)[:5]
        except Exception as e:
            log(self.NAME, f"Error fetching insights: {e}")
            return []

    def build_synthesis_prompt(self, results: list, insights: list) -> str:
        high_scored = sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:20]
        results_text = "\n\n".join([
            f"[{r.get('agent','?')} | Score:{r.get('score',0)}/10 | {r.get('topic','')}]\n{r.get('content','')[:400]}"
            for r in high_scored
        ])
        insights_text = "\n\n".join([
            f"[Novelty:{i.get('novelty_score',0)}/10]\n{i.get('content','')[:300]}"
            for i in insights
        ])

        return f"""You are a strategic research synthesizer. Analyze this week's research and extract the most valuable actionable insights.

THIS WEEK'S TOP RESEARCH ({len(results)} total results):
{results_text}

THIS WEEK'S TOP INSIGHTS:
{insights_text}

Generate a weekly synthesis report in this EXACT format:

## 🏆 TOP 3 MARKET OPPORTUNITIES THIS WEEK
[For each: specific problem, who has it, why current solutions fail, opportunity size]

## 😤 TOP 3 MOST COMPLAINED ABOUT PROBLEMS
[Real specific complaints that keep appearing — with evidence]

## 💡 TOP 3 APP IDEAS (based on research)
[For each: name, one-line description, target user, why now, competition LOW/MED/HIGH]

## 📈 STRONGEST TREND THIS WEEK
[One specific trend with the most evidence — why it matters]

## ⚠️ WHAT TO AVOID
[Markets or ideas research shows are oversaturated or failing]

## 🎯 WEEKLY VERDICT
[2-3 sentences: the single biggest opportunity found this week and why]

Be specific. Use real examples from the research. No generic statements."""

    def synthesize(self) -> dict:
        log(self.NAME, "Starting weekly synthesis...")
        results = self.get_weekly_results()
        insights = self.get_top_insights()

        if len(results) < 5:
            log(self.NAME, f"Not enough data ({len(results)} results). Skipping.")
            return {"success": False, "reason": "Not enough data"}

        log(self.NAME, f"Synthesizing {len(results)} results + {len(insights)} insights")
        prompt = self.build_synthesis_prompt(results, insights)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Strategic research synthesizer. Be specific and actionable."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2000,
            "temperature": 0.4
        }

        try:
            resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=60)
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}"}

            text = resp.json()["choices"][0]["message"]["content"]

            # Save to database
            try:
                from utils.database import save_result
                save_result("synthesis", f"Weekly Report {datetime.now().strftime('%Y-%m-%d')}", text, score=10)
            except Exception as e:
                log(self.NAME, f"Save error: {e}")

            # Send to Telegram
            self._send_to_telegram(text, len(results))
            log(self.NAME, "Weekly synthesis complete!")
            return {"success": True, "text": text}

        except Exception as e:
            log(self.NAME, f"Error: {e}")
            return {"success": False, "error": str(e)}

    def _send_to_telegram(self, text: str, result_count: int):
        header = (
            f"📊 *WEEKLY RESEARCH SYNTHESIS*\n"
            f"_{datetime.now().strftime('%B %d, %Y')}_\n"
            f"_Based on {result_count} research results_\n\n"
        )
        full_message = header + text
        chunks = [full_message[i:i+4000] for i in range(0, len(full_message), 4000)]
        for i, chunk in enumerate(chunks):
            send_telegram(chunk if i == 0 else f"_(part {i+1}/{len(chunks)})_\n\n{chunk}")
        log(self.NAME, f"Sent {len(chunks)} Telegram message(s)")
