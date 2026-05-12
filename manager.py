"""
MANAGER AGENT v7
All fixes based on reading every file in the codebase:

1. task_queue / completed / last_summary_date → Postgres (manager_state table)
2. rate limits → Postgres (via base_agent.py fix — agent_status.rate_limit_until)
3. rotation state → Postgres (via topic_rotator.py fix)
4. logs/ writes removed → stdout only (Render captures it)
5. agent_name passed to build_prompt() → critic feedback injected per-agent
   (memory_context.get_context_for_prompt already supports agent_name= param)
6. 100-topic TOPIC_POOL preserved + seeded into Postgres research_topics table
7. MAX_RESULTS_PER_TOPIC guard preserved
8. Weekly synthesis agent preserved
9. rotate_topics() now returns bool — handled correctly
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
    update_agent_status, get_insights, get_conn
)
from utils.notifier import notify_high_score, notify_daily_summary
from utils.topic_rotator import rotate_topics

Path("state").mkdir(exist_ok=True)

MAX_RESULTS_PER_TOPIC = 5

TOPIC_POOL = [
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


# ─────────────────────────────────────────────
# POSTGRES STATE  (replaces all state/*.json files)
# ─────────────────────────────────────────────

def init_manager_tables():
    """Create manager_state and research_topics tables if not exist."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS manager_state (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS research_topics (
                topic    TEXT PRIMARY KEY,
                added_at TEXT NOT NULL
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        log_manager("Postgres state tables ready")
    except Exception as e:
        log_manager(f"init_manager_tables error: {e}")


def db_get(key: str, default=None):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT value FROM manager_state WHERE key = %s", (key,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return json.loads(row[0]) if row else default
    except Exception as e:
        log_manager(f"db_get({key}) error: {e}")
        return default


def db_set(key: str, value):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO manager_state (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (key, json.dumps(value, default=str)))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log_manager(f"db_set({key}) error: {e}")


def db_get_topics() -> list:
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT topic FROM research_topics ORDER BY added_at")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        log_manager(f"db_get_topics error: {e}")
        return []


def db_add_topic(topic: str):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO research_topics (topic, added_at)
            VALUES (%s, %s)
            ON CONFLICT (topic) DO NOTHING
        """, (topic, datetime.now().isoformat()))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log_manager(f"db_add_topic error: {e}")


def seed_topics_to_db():
    """Seed TOPIC_POOL into Postgres on first run."""
    existing = db_get_topics()
    if len(existing) >= len(TOPIC_POOL):
        return
    for t in TOPIC_POOL:
        db_add_topic(t)
    log_manager(f"Seeded {len(TOPIC_POOL)} topics into Postgres")


# ─────────────────────────────────────────────
# MANAGER
# ─────────────────────────────────────────────

class ManagerAgent:

    def __init__(self):
        init_db()
        init_manager_tables()
        seed_topics_to_db()

        self.agents = {
            "market_scout": MarketScout(),
            "trend_analyst": TrendAnalyst(),
            "deep_diver": DeepDiver(),
        }
        self.critic = CriticAgent()
        self.memory = MemoryAgent()
        self.synthesis = SynthesisAgent()

        # ALL state from Postgres — survives Render restarts
        self.task_queue = db_get("task_queue", [])
        self.completed = db_get("completed", [])
        self.last_summary_date = db_get("last_summary_date", "")

        log_manager("Manager v7 — Postgres state + per-agent critic feedback + 100 topics")

    def _save_state(self):
        db_set("task_queue", self.task_queue)
        db_set("completed", self.completed)
        db_set("last_summary_date", self.last_summary_date)

    def get_topic_result_count(self, topic: str) -> int:
        try:
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
        """Build queue from Postgres topics, skip over-researched ones."""
        rotated = rotate_topics()
        if rotated:
            log_manager("Topics rotated — fresh research targets added!")

        topics = db_get_topics()
        if not topics:
            seed_topics_to_db()
            topics = db_get_topics()

        queued_topics = {t["topic"] for t in self.task_queue if t["status"] == "pending"}
        added = 0

        for topic in topics:
            if topic in queued_topics:
                continue
            count = self.get_topic_result_count(topic)
            if count >= MAX_RESULTS_PER_TOPIC:
                continue
            self.task_queue.append({"topic": topic, "status": "pending"})
            added += 1

        pending = len([t for t in self.task_queue if t["status"] == "pending"])
        log_manager(f"Queue: {pending} pending ({added} new added, max {MAX_RESULTS_PER_TOPIC}/topic)")
        self._save_state()

    def run_sequential_pipeline(self, topic: str) -> dict:
        """
        Sequential pipeline: Scout → Analyst → Diver → Critic → Memory
        KEY FIX: agent_name passed to build_prompt() so
        memory_context.get_context_for_prompt(topic, agent_name=NAME)
        injects each agent's personal critic feedback into their prompt.
        """
        log_manager(f"🔬 Pipeline: {topic}")
        all_findings = []

        # ── STEP 1 — Market Scout ──
        scout = self.agents["market_scout"]
        if not scout.is_rate_limited():
            log_manager("[SCOUT] Researching...")
            # agent_name="market_scout" → critic feedback injected via memory_context
            prompt = scout.build_prompt(topic, agent_name="market_scout")
            result = scout.call_api(prompt)
            if result.get("success"):
                scout.save_to_db(topic, result["text"])
                all_findings.append(f"## SCOUT:\n{result['text']}")
                log_manager("[SCOUT] ✓")
                time.sleep(3)
            elif result.get("rate_limited"):
                scout.set_rate_limited()
                log_manager("[SCOUT] Rate limited")
        else:
            log_manager("[SCOUT] Rate limited, skipping")

        # ── STEP 2 — Trend Analyst ──
        analyst = self.agents["trend_analyst"]
        if not analyst.is_rate_limited():
            log_manager("[ANALYST] Researching...")
            prior = all_findings[0] if all_findings else ""
            prompt = analyst.build_prompt(topic, agent_name="trend_analyst")
            if prior:
                prompt += f"\n\nSCOUT ALREADY FOUND:\n{prior[:600]}\nDon't repeat. Go deeper on trends."
            result = analyst.call_api(prompt)
            if result.get("success"):
                analyst.save_to_db(topic, result["text"])
                all_findings.append(f"## ANALYST:\n{result['text']}")
                log_manager("[ANALYST] ✓")
                time.sleep(3)
            elif result.get("rate_limited"):
                analyst.set_rate_limited()
                log_manager("[ANALYST] Rate limited")
        else:
            log_manager("[ANALYST] Rate limited, skipping")

        # ── STEP 3 — Deep Diver ──
        diver = self.agents["deep_diver"]
        if not diver.is_rate_limited():
            log_manager("[DIVER] Researching...")
            prior = "\n\n".join(all_findings) if all_findings else ""
            prompt = diver.build_prompt(topic, agent_name="deep_diver")
            if prior:
                prompt += f"\n\nPREVIOUS AGENTS FOUND:\n{prior[:900]}\nFind what they missed. Be contrarian."
            result = diver.call_api(prompt)
            if result.get("success"):
                diver.save_to_db(topic, result["text"])
                all_findings.append(f"## DIVER:\n{result['text']}")
                log_manager("[DIVER] ✓")
                time.sleep(3)
            elif result.get("rate_limited"):
                diver.set_rate_limited()
                log_manager("[DIVER] Rate limited")
        else:
            log_manager("[DIVER] Rate limited, skipping")

        if not all_findings:
            log_manager("No findings — all agents rate limited")
            return {"success": False}

        # ── STEP 4 — Critic ──
        combined = "\n\n---\n\n".join(all_findings)
        score = 5  # default if critic fails

        if not self.critic.is_rate_limited():
            log_manager("[CRITIC] Scoring...")
            # critic.evaluate() handles its own prompt building
            crit_result = self.critic.evaluate(topic, combined)
            if crit_result["success"]:
                score = crit_result["score"]
                save_result("critic", topic, crit_result["text"], score)
                log_manager(f"[CRITIC] ✓ Score: {score}/10")
                notify_high_score("Critic", topic, score, crit_result["text"][:300])
                self._update_scores_for_topic(topic, score)

                # ── STEP 5 — Memory ──
                if score >= 4 and not self.memory.is_rate_limited():
                    # memory.synthesize() takes (new_content, topic)
                    mem_result = self.memory.synthesize(combined, topic)
                    if mem_result["success"]:
                        log_manager(f"[MEMORY] ✓ Novelty: {mem_result.get('novelty_score', '?')}/10")
        else:
            log_manager("[CRITIC] Rate limited, skipping")

        return {"success": True, "score": score}

    def _update_scores_for_topic(self, topic: str, score: int):
        """Backfill critic score onto all unscored agent results for this topic."""
        try:
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

        processed = 0
        for task in pending:
            if processed >= 3:
                break

            topic = task["topic"]
            count = self.get_topic_result_count(topic)
            if count >= MAX_RESULTS_PER_TOPIC:
                task["status"] = "done"
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
                log_manager(f"✅ Done: {topic[:60]}")
                processed += 1
            else:
                log_manager("⏸️ All rate limited — waiting for next cycle")
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
        log_manager("🚀 Manager v7 — Postgres state, per-agent feedback, 100 topics")

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
