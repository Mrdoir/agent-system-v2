"""
MANAGER AGENT - The Brain v5
Sequential pipeline: Scout → Analyst → Diver → Critic → Memory → Synthesis
Each agent reads critic feedback from last cycle and improves.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import json
import time
import schedule
import threading
from datetime import datetime, date
from pathlib import Path
from agents.market_scout import MarketScout
from agents.trend_analyst import TrendAnalyst
from agents.deep_diver import DeepDiver
from agents.critic import CriticAgent
from agents.memory_agent import MemoryAgent
from agents.synthesis_agent import SynthesisAgent
from utils.logger import log, log_manager
from utils.database import (
    init_db, save_result, get_total_results,
    update_agent_status, get_insights
)
from utils.topic_rotator import rotate_topics
from utils.notifier import notify_high_score, notify_daily_summary

RESEARCH_TOPICS_FILE = "research_topics.json"
STATE_FILE = "state/manager_state.json"
Path("state").mkdir(exist_ok=True)


class ManagerAgent:
    def __init__(self):
        init_db()
        self.state = self._load_state()
        self.agents = {
            "market_scout": MarketScout(),
            "trend_analyst": TrendAnalyst(),
            "deep_diver": DeepDiver(),
        }
        self.critic = CriticAgent()
        self.memory = MemoryAgent()
        self.synthesis = SynthesisAgent()
        self.task_queue = self.state.get("task_queue", [])
        self.completed = self.state.get("completed", [])
        self.last_summary_date = self.state.get("last_summary_date", "")
        log_manager("Manager v5 — Sequential Pipeline + Critic Feedback Loop + Weekly Synthesis")

    def _load_state(self):
        if Path(STATE_FILE).exists():
            with open(STATE_FILE) as f:
                return json.load(f)
        return {}

    def _save_state(self):
        with open(STATE_FILE, "w") as f:
            json.dump({
                "task_queue": self.task_queue,
                "completed": self.completed,
                "last_summary_date": self.last_summary_date
            }, f, indent=2)

    def load_topics(self):
        if not Path(RESEARCH_TOPICS_FILE).exists():
            default = {"topics": [
                "productivity apps market gaps 2025-2026",
                "top user complaints about note-taking apps 2025-2026",
                "emerging B2C SaaS trends 2025-2026",
                "what problems do freelancers still struggle with 2026",
                "underserved mobile app niches 2025-2026",
                "fastest growing app categories 2026",
                "AI app ideas that nobody has built yet 2026",
                "most complained about apps on Reddit 2026",
                "what features are users begging for in existing apps 2026",
                "blue ocean markets for mobile apps 2026"
            ]}
            with open(RESEARCH_TOPICS_FILE, "w") as f:
                json.dump(default, f, indent=2)
        with open(RESEARCH_TOPICS_FILE) as f:
            return json.load(f).get("topics", [])

    def build_task_queue(self):
        rotated = rotate_topics()
        if rotated:
            log_manager("📅 Topics rotated — fresh research targets loaded!")

        topics = self.load_topics()
        done_keys = {t["topic"] for t in self.completed}

        for topic in topics:
            if topic not in done_keys:
                if not any(t["topic"] == topic for t in self.task_queue):
                    self.task_queue.append({"topic": topic, "status": "pending"})

        pending = len([t for t in self.task_queue if t["status"] == "pending"])
        log_manager(f"Queue: {pending} pending topics")
        self._save_state()

    def run_sequential_pipeline(self, topic: str) -> dict:
        """
        Sequential pipeline — each agent builds on previous findings
        AND reads its own critic feedback to improve.
        Scout → Analyst → Deep Diver → Critic → Memory
        """
        log_manager(f"🔬 Starting pipeline for: {topic}")
        all_findings = []

        # STEP 1 — Market Scout
        scout = self.agents["market_scout"]
        if not scout.is_rate_limited():
            log_manager(f"[SCOUT] Researching (with critic feedback applied)...")
            scout_prompt = scout.build_prompt(topic)
            scout_result = scout.call_api(scout_prompt)
            if scout_result.get("success"):
                scout.save_to_db(topic, scout_result["text"])
                all_findings.append(f"## SCOUT FINDINGS:\n{scout_result['text']}")
                log_manager(f"[SCOUT] ✓ Done")
                time.sleep(3)
            elif scout_result.get("rate_limited"):
                scout.set_rate_limited()
                log_manager(f"[SCOUT] Rate limited")
        else:
            log_manager(f"[SCOUT] Rate limited, skipping")

        # STEP 2 — Trend Analyst: reads Scout findings + own critic feedback
        analyst = self.agents["trend_analyst"]
        if not analyst.is_rate_limited():
            log_manager(f"[ANALYST] Reading Scout + applying critic feedback...")
            scout_context = all_findings[0] if all_findings else "No prior research."
            analyst_prompt = analyst.build_prompt(topic) + f"""

## WHAT MARKET SCOUT ALREADY FOUND (go deeper, don't repeat):
{scout_context}

Based on Scout's findings, analyze TRENDS more deeply.
Focus on angles Scout missed."""

            analyst_result = analyst.call_api(analyst_prompt)
            if analyst_result.get("success"):
                analyst.save_to_db(topic, analyst_result["text"])
                all_findings.append(f"## ANALYST FINDINGS:\n{analyst_result['text']}")
                log_manager(f"[ANALYST] ✓ Done — built on Scout's research")
                time.sleep(3)
            elif analyst_result.get("rate_limited"):
                analyst.set_rate_limited()
                log_manager(f"[ANALYST] Rate limited")
        else:
            log_manager(f"[ANALYST] Rate limited, skipping")

        # STEP 3 — Deep Diver: reads Scout + Analyst + own critic feedback
        diver = self.agents["deep_diver"]
        if not diver.is_rate_limited():
            log_manager(f"[DIVER] Reading all findings + applying critic feedback...")
            prior_research = "\n\n".join(all_findings) if all_findings else "No prior research."
            diver_prompt = diver.build_prompt(topic) + f"""

## WHAT PREVIOUS AGENTS FOUND (go deeper, find what they missed):
{prior_research}

You are the FINAL researcher. Find HIDDEN insights and specific MVP opportunities
that neither Scout nor Analyst found. Be specific. Be contrarian. Be deep."""

            diver_result = diver.call_api(diver_prompt)
            if diver_result.get("success"):
                diver.save_to_db(topic, diver_result["text"])
                all_findings.append(f"## DEEP DIVER FINDINGS:\n{diver_result['text']}")
                log_manager(f"[DIVER] ✓ Done — built on all previous research")
                time.sleep(3)
            elif diver_result.get("rate_limited"):
                diver.set_rate_limited()
                log_manager(f"[DIVER] Rate limited")
        else:
            log_manager(f"[DIVER] Rate limited, skipping")

        if not all_findings:
            log_manager(f"No findings for {topic} — all agents rate limited")
            return {"success": False}

        # STEP 4 — Critic
        combined = "\n\n---\n\n".join(all_findings)
        log_manager(f"[CRITIC] Deep reasoning evaluation for: {topic}")

        if not self.critic.is_rate_limited():
            crit_result = self.critic.evaluate(topic, combined)
            if crit_result["success"]:
                score = crit_result["score"]
                save_result("critic", topic, crit_result["text"], score)
                log_manager(f"[CRITIC] ✓ Overall score: {score}/10 — feedback saved for all agents")
                notify_high_score("Critic", topic, score, crit_result["text"][:300])

                # STEP 5 — Memory
                if score >= 4 and not self.memory.is_rate_limited():
                    mem_result = self.memory.synthesize(
                        combined + "\n\n" + crit_result["text"], topic
                    )
                    if mem_result["success"]:
                        log_manager(f"[MEMORY] ✓ Learned (novelty: {mem_result.get('novelty_score','?')}/10)")

                return {"success": True, "score": score}

        return {"success": True, "score": 0}

    def run_cycle(self):
        log_manager("--- Starting sequential research cycle ---")
        pending = [t for t in self.task_queue if t["status"] == "pending"]

        if not pending:
            log_manager("All topics done! Resetting for next round...")
            self.task_queue = []
            self.completed = []
            self._save_state()
            self.build_task_queue()
            pending = [t for t in self.task_queue if t["status"] == "pending"]

        for task in pending:
            topic = task["topic"]
            result = self.run_sequential_pipeline(topic)

            if result["success"]:
                task["status"] = "done"
                self.completed.append({
                    "topic": topic,
                    "timestamp": datetime.now().isoformat(),
                    "score": result.get("score", 0)
                })
                log_manager(f"✅ Pipeline complete for: {topic}")
            else:
                task["status"] = "error"
                log_manager(f"❌ Pipeline failed for: {topic}")

            self._save_state()
            time.sleep(5)

        self.send_daily_summary()
        log_manager(f"--- Cycle complete. Total DB results: {get_total_results()} ---\n")

    def send_daily_summary(self):
        today = date.today().isoformat()
        if self.last_summary_date == today:
            return
        insights = get_insights(limit=3)
        previews = [i["content"][:100] for i in insights]
        notify_daily_summary(get_total_results(), len(self.completed), previews)
        self.last_summary_date = today
        self._save_state()
        log_manager("Daily summary sent")

    def start(self):
        log_manager("🚀 Manager v5 — Sequential Pipeline + Critic Feedback Loop active!")
        from telegram_bot import start_bot_thread
        start_bot_thread()
        self.build_task_queue()

        try:
            from dashboard import app
            port = int(os.environ.get("PORT", 8080))
            t = threading.Thread(
                target=lambda: app.run(host="0.0.0.0", port=port, use_reloader=False, threaded=True),
                daemon=True
            )
            t.start()
            log_manager(f"📊 Dashboard running on port {port}")
        except Exception as e:
            log_manager(f"Dashboard error: {e}")

        self.run_cycle()
        schedule.every(15).minutes.do(self.run_cycle)
        schedule.every().day.at("09:00").do(self.send_daily_summary)
        schedule.every().sunday.at("09:00").do(self.synthesis.synthesize)

        while True:
            schedule.run_pending()
            time.sleep(60)


if __name__ == "__main__":
    manager = ManagerAgent()
    try:
        manager.start()
    except KeyboardInterrupt:
        log_manager("Manager stopped.")
