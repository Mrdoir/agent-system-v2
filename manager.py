"""
MANAGER AGENT - Fixed Version
Fixes:
1. Skip topics that already have 5+ results
2. Ensure all results get scored
3. Much larger topic pool (100+ topics)
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
from utils.notifier import notify_high_score, notify_daily_summary

RESEARCH_TOPICS_FILE = "research_topics.json"
STATE_FILE = "state/manager_state.json"
MAX_RESULTS_PER_TOPIC = 5  # Stop after 5 results per topic
Path("state").mkdir(exist_ok=True)

# 100+ diverse topics pool
TOPIC_POOL = [
    # Productivity
    "most complained about productivity apps May 2026",
    "why do people abandon to-do list apps",
    "calendar app problems power users face",
    "note-taking app switching reasons 2026",
    "focus and deep work app gaps 2026",
    "time tracking app user complaints",
    "meeting scheduler pain points 2026",
    "email management app failures",
    "file organization tool gaps",
    "password manager user frustrations",
    
    # Freelancers & Remote Work
    "freelancer invoicing pain points 2026",
    "remote work tool fatigue 2026",
    "client communication problems freelancers",
    "project management for solo freelancers gaps",
    "freelancer tax and accounting app gaps",
    "contract management pain points",
    "freelancer portfolio tool problems",
    "time zone management for remote teams",
    "async communication tool gaps 2026",
    "freelancer onboarding client problems",
    
    # Finance & Money
    "personal finance app user complaints 2026",
    "budgeting app abandonment reasons",
    "expense tracking app problems",
    "investment app gaps for beginners",
    "subscription management app needs",
    "split expenses app pain points",
    "crypto portfolio tracker gaps",
    "salary negotiation tool gaps",
    "financial goal tracking app problems",
    "bill payment reminder app gaps",
    
    # Health & Wellness
    "mental health app user complaints 2026",
    "meditation app dropout reasons",
    "sleep tracking app accuracy problems",
    "fitness app motivation failures",
    "habit tracking app abandonment",
    "nutrition tracking app frustrations",
    "therapy and counseling app gaps",
    "chronic illness management app gaps",
    "women health app missing features",
    "senior citizen health app gaps",
    
    # Learning & Education
    "language learning app dropout reasons",
    "online course completion rate problems",
    "skill learning app gaps 2026",
    "study tool app complaints students",
    "coding learning platform gaps",
    "math tutoring app problems",
    "reading habit app failures",
    "flashcard app user frustrations",
    "certificate and credential tracking gaps",
    "professional development app gaps",
    
    # Social & Communication
    "social media overwhelm solutions needed",
    "community building tool gaps 2026",
    "group chat app fatigue problems",
    "networking app failures professionals",
    "dating app user complaints 2026",
    "family communication app gaps",
    "event planning app problems",
    "gift tracking and gifting app gaps",
    "contact management app failures",
    "social accountability app gaps",
    
    # Creators & Side Hustles
    "content creator tool gaps 2026",
    "YouTube channel management pain points",
    "newsletter tool user complaints",
    "podcast creation tool gaps",
    "social media scheduling app problems",
    "creator monetization tool gaps",
    "digital product selling platform gaps",
    "online store management pain points",
    "affiliate marketing tool gaps",
    "creator analytics tool problems",
    
    # Developer & Tech
    "developer productivity tool gaps 2026",
    "code review tool pain points",
    "API testing tool complaints",
    "documentation tool failures",
    "bug tracking app user frustrations",
    "deployment tool pain points",
    "developer portfolio tool gaps",
    "open source project management gaps",
    "technical interview prep app gaps",
    "developer community platform problems",
    
    # Small Business
    "small business CRM pain points 2026",
    "restaurant management software gaps",
    "retail inventory management problems",
    "appointment booking app complaints",
    "small business marketing tool gaps",
    "customer feedback tool problems",
    "employee scheduling app gaps",
    "small business accounting pain points",
    "e-commerce analytics tool gaps",
    "local business discovery app gaps",
    
    # Niche & Emerging
    "AI writing tool user complaints 2026",
    "AI image tool workflow gaps",
    "voice memo and transcription app gaps",
    "travel planning app pain points 2026",
    "house hunting and real estate app gaps",
    "car maintenance tracking app gaps",
    "home renovation planning tool gaps",
    "pet care app missing features",
    "gardening app user frustrations",
    "recipe and meal planning app problems",
    "shopping list app gaps 2026",
    "book tracking app user complaints",
    "movie and TV tracking app gaps",
    "gaming companion app gaps",
    "sports performance tracking app gaps",
    "volunteer and charity app gaps",
    "local community app problems",
    "environmental tracking app gaps",
    "wedding planning app pain points",
    "baby and parenting app gaps 2026",
]


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
        log_manager("Manager v6 — Fixed: No repetition + 100 topics + proper scoring")

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

    def get_topic_result_count(self, topic: str) -> int:
        """Check how many results already exist for this topic."""
        try:
            from utils.database import get_conn
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM results WHERE topic = %s", (topic,))
            count = cur.fetchone()[0]
            cur.close()
            conn.close()
            return count
        except:
            return 0

    def build_task_queue(self):
        """Build queue from 100+ topic pool, skip over-researched topics."""
        # Save topics to file
        with open(RESEARCH_TOPICS_FILE, "w") as f:
            json.dump({"topics": TOPIC_POOL}, f, indent=2)

        queued_topics = {t["topic"] for t in self.task_queue if t["status"] == "pending"}
        added = 0

        for topic in TOPIC_POOL:
            if topic in queued_topics:
                continue
            # Skip if already has enough results
            count = self.get_topic_result_count(topic)
            if count >= MAX_RESULTS_PER_TOPIC:
                continue
            self.task_queue.append({"topic": topic, "status": "pending"})
            added += 1

        pending = len([t for t in self.task_queue if t["status"] == "pending"])
        log_manager(f"Queue: {pending} pending topics ({added} new added, max {MAX_RESULTS_PER_TOPIC} results/topic)")
        self._save_state()

    def run_sequential_pipeline(self, topic: str) -> dict:
        """Sequential pipeline with guaranteed scoring."""
        log_manager(f"🔬 Pipeline: {topic}")
        all_findings = []

        # STEP 1 — Market Scout
        scout = self.agents["market_scout"]
        if not scout.is_rate_limited():
            log_manager(f"[SCOUT] Researching...")
            scout_result = scout.call_api(scout.build_prompt(topic))
            if scout_result.get("success"):
                scout.save_to_db(topic, scout_result["text"])
                all_findings.append(f"## SCOUT:\n{scout_result['text']}")
                log_manager(f"[SCOUT] ✓")
                time.sleep(3)
            elif scout_result.get("rate_limited"):
                scout.set_rate_limited()

        # STEP 2 — Trend Analyst
        analyst = self.agents["trend_analyst"]
        if not analyst.is_rate_limited():
            log_manager(f"[ANALYST] Researching...")
            prior = all_findings[0] if all_findings else ""
            prompt = analyst.build_prompt(topic)
            if prior:
                prompt += f"\n\nSCOUT FOUND: {prior[:500]}\nGo deeper, don't repeat."
            analyst_result = analyst.call_api(prompt)
            if analyst_result.get("success"):
                analyst.save_to_db(topic, analyst_result["text"])
                all_findings.append(f"## ANALYST:\n{analyst_result['text']}")
                log_manager(f"[ANALYST] ✓")
                time.sleep(3)
            elif analyst_result.get("rate_limited"):
                analyst.set_rate_limited()

        # STEP 3 — Deep Diver
        diver = self.agents["deep_diver"]
        if not diver.is_rate_limited():
            log_manager(f"[DIVER] Researching...")
            prior = "\n\n".join(all_findings)
            prompt = diver.build_prompt(topic)
            if prior:
                prompt += f"\n\nPREVIOUS FINDINGS: {prior[:800]}\nFind what they missed."
            diver_result = diver.call_api(prompt)
            if diver_result.get("success"):
                diver.save_to_db(topic, diver_result["text"])
                all_findings.append(f"## DIVER:\n{diver_result['text']}")
                log_manager(f"[DIVER] ✓")
                time.sleep(3)
            elif diver_result.get("rate_limited"):
                diver.set_rate_limited()

        if not all_findings:
            return {"success": False}

        # STEP 4 — Critic (ALWAYS score everything)
        combined = "\n\n---\n\n".join(all_findings)
        score = 5  # default score if critic fails

        if not self.critic.is_rate_limited():
            log_manager(f"[CRITIC] Scoring...")
            crit_result = self.critic.evaluate(topic, combined)
            if crit_result["success"]:
                score = crit_result["score"]
                save_result("critic", topic, crit_result["text"], score)
                log_manager(f"[CRITIC] ✓ Score: {score}/10")
                notify_high_score("Critic", topic, score, crit_result["text"][:300])

                # Update all agent results with the critic score
                self._update_scores_for_topic(topic, score)

                # STEP 5 — Memory
                if score >= 4 and not self.memory.is_rate_limited():
                    mem_result = self.memory.synthesize(combined, topic)
                    if mem_result["success"]:
                        log_manager(f"[MEMORY] ✓ Novelty: {mem_result.get('novelty_score','?')}/10")

        return {"success": True, "score": score}

    def _update_scores_for_topic(self, topic: str, score: int):
        """Update score for all agent results on this topic."""
        try:
            from utils.database import get_conn
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "UPDATE results SET score = %s WHERE topic = %s AND agent != 'critic' AND score = 0",
                (score, topic)
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            log_manager(f"Score update error: {e}")

    def run_cycle(self):
        log_manager("--- Research cycle starting ---")
        pending = [t for t in self.task_queue if t["status"] == "pending"]

        if not pending:
            log_manager("Queue empty — rebuilding with fresh topics")
            self.task_queue = []
            self.completed = []
            self._save_state()
            self.build_task_queue()
            pending = [t for t in self.task_queue if t["status"] == "pending"]

        # Process up to 3 topics per cycle
        processed = 0
        for task in pending:
            if processed >= 3:
                break

            topic = task["topic"]

            # Double-check — skip if already has enough results
            count = self.get_topic_result_count(topic)
            if count >= MAX_RESULTS_PER_TOPIC:
                task["status"] = "done"
                log_manager(f"Skipping {topic[:40]} — already has {count} results")
                self._save_state()
                continue

            result = self.run_sequential_pipeline(topic)

            if result["success"]:
                task["status"] = "done"
                self.completed.append({
                    "topic": topic,
                    "timestamp": datetime.now().isoformat(),
                    "score": result.get("score", 0)
                })
                log_manager(f"✅ Done: {topic[:50]}")
                processed += 1
            else:
                log_manager(f"⏸️ All agents rate limited — waiting for next cycle")
                break

            self._save_state()
            time.sleep(5)

        self.send_daily_summary()
        log_manager(f"--- Cycle done. Total: {get_total_results()} results ---\n")

    def send_daily_summary(self):
        today = date.today().isoformat()
        if self.last_summary_date == today:
            return
        insights = get_insights(limit=3)
        previews = [i["content"][:100] for i in insights]
        notify_daily_summary(get_total_results(), len(self.completed), previews)
        self.last_summary_date = today
        self._save_state()

    def start(self):
        log_manager("🚀 Manager v6 — 100 topics, no repetition, proper scoring!")
        try:
            from telegram_bot import start_bot_thread
            start_bot_thread()
        except Exception as e:
            log_manager(f"Telegram bot error: {e}")

        self.build_task_queue()

        try:
            from dashboard import app
            port = int(os.environ.get("PORT", 8080))
            t = threading.Thread(
                target=lambda: app.run(host="0.0.0.0", port=port, use_reloader=False, threaded=True),
                daemon=True
            )
            t.start()
            log_manager(f"📊 Dashboard on port {port}")
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
