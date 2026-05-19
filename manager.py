"""
MANAGER AGENT v4 — Orchestrates all research agents with adaptive timing
=========================================================================
FIXED: Checks provider availability before cycles, adapts interval when low.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import json
import time
from datetime import datetime, date, timedelta
from pathlib import Path

from agents.market_scout import MarketScout
from agents.trend_analyst import TrendAnalyst
from agents.deep_diver import DeepDiver
from agents.critic import CriticAgent
from agents.memory_agent import MemoryAgent
from agents.synthesis_agent import SynthesisAgent

from utils.logger import log_info, log_warn, log_error, log_manager, log_debug
from utils.database import (
    init_db, save_result, get_total_results, get_results,
    update_agent_status, get_insights, get_conn, get_agent_statuses,
    is_topic_saturated, get_analytics_summary
)
from utils.notifier import (
    notify_high_score, notify_daily_summary, notify_rate_limit_all
)
from utils.topic_rotator import rotate_topics, get_next_topic, get_prioritized_topics
from utils.provider_pool import pool

# Ensure state directory exists
Path("state").mkdir(exist_ok=True)

# Configuration
MAX_RESULTS_PER_TOPIC = int(os.getenv("MAX_RESULTS_PER_TOPIC", "5"))
DEFAULT_CYCLE_MINUTES = int(os.getenv("CYCLE_INTERVAL_MINUTES", "15"))

# 100-topic research pool
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


# ═══════════════════════════════════════════════════════════════════
# POSTGRES STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

def init_manager_tables():
    """Create manager state tables if not exist."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS manager_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS research_topics (
                topic TEXT PRIMARY KEY,
                added_at TEXT NOT NULL,
                priority INTEGER DEFAULT 0
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        log_manager("Postgres state tables ready")
    except Exception as e:
        log_error("manager", f"init_manager_tables error: {e}")


def db_get(key: str, default=None):
    """Get value from manager_state."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT value FROM manager_state WHERE key = %s", (key,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return json.loads(row[0]) if row else default
    except Exception as e:
        log_debug("manager", f"db_get({key}) error: {e}")
        return default


def db_set(key: str, value):
    """Set value in manager_state."""
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
        log_debug("manager", f"db_set({key}) error: {e}")


def seed_topics():
    """Seed initial topics into database."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        for topic in TOPIC_POOL:
            cur.execute("""
                INSERT INTO research_topics (topic, added_at, priority)
                VALUES (%s, %s, 0)
                ON CONFLICT (topic) DO NOTHING
            """, (topic, datetime.now().isoformat()))
        conn.commit()
        cur.close()
        conn.close()
        log_manager(f"Seeded {len(TOPIC_POOL)} topics")
    except Exception as e:
        log_error("manager", f"seed_topics error: {e}")


# ═══════════════════════════════════════════════════════════════════
# ADAPTIVE TIMING — Check provider health before each cycle
# ═══════════════════════════════════════════════════════════════════

def get_adaptive_interval() -> int:
    """Get cycle interval based on provider health."""
    available = pool.get_available_count()
    total = pool.get_total_count()
    
    if available == 0:
        log_warn("manager", "All providers exhausted!")
        return 120  # 2 hours
    elif available == 1:
        log_warn("manager", f"Only 1/{total} provider available, slowing down")
        return 60  # 1 hour
    elif available <= 2:
        log_info("manager", f"Only {available}/{total} providers available")
        return 30  # 30 minutes
    else:
        return DEFAULT_CYCLE_MINUTES


def should_run_cycle() -> bool:
    """Check if enough providers are available to run a cycle."""
    available = pool.get_available_count()
    total = pool.get_total_count()
    
    if available == 0:
        log_warn("manager", "All providers exhausted, skipping cycle")
        notify_rate_limit_all(get_adaptive_interval())
        return False
    
    log_info("manager", f"Providers: {available}/{total} available")
    return True


# ═══════════════════════════════════════════════════════════════════
# RESEARCH CYCLE
# ═══════════════════════════════════════════════════════════════════

def run_cycle():
    """Run one research cycle."""
    log_manager("═══════════════════════════════════════════════════════════")
    log_manager("STARTING RESEARCH CYCLE")
    log_manager("═══════════════════════════════════════════════════════════")
    
    # Get topic
    topic = get_next_topic()
    if not topic:
        log_warn("manager", "No topics available, using fallback")
        topic = TOPIC_POOL[0]
    
    log_manager(f"Topic: {topic}")
    
    # ── MARKET SCOUT ──────────────────────────────────────────────
    scout_result = None
    try:
        scout = MarketScout()
        scout_result = scout.research(topic)
        if scout_result.get("success"):
            log_info("market_scout", f"Research complete via {scout_result.get('provider', '?')}")
        else:
            log_warn("market_scout", f"Failed: {scout_result.get('error', 'unknown')}")
    except Exception as e:
        log_error("market_scout", f"Exception: {e}")
    
    # ── TREND ANALYST ─────────────────────────────────────────────
    analyst_result = None
    try:
        analyst = TrendAnalyst()
        analyst_result = analyst.research(topic)
        if analyst_result.get("success"):
            log_info("trend_analyst", f"Research complete via {analyst_result.get('provider', '?')}")
        else:
            log_warn("trend_analyst", f"Failed: {analyst_result.get('error', 'unknown')}")
    except Exception as e:
        log_error("trend_analyst", f"Exception: {e}")
    
    # ── DEEP DIVER ────────────────────────────────────────────────
    diver_result = None
    try:
        diver = DeepDiver()
        diver_result = diver.research(topic)
        if diver_result.get("success"):
            log_info("deep_diver", f"Research complete via {diver_result.get('provider', '?')}")
        else:
            log_warn("deep_diver", f"Failed: {diver_result.get('error', 'unknown')}")
    except Exception as e:
        log_error("deep_diver", f"Exception: {e}")
    
    # ── COMBINE RESULTS FOR CRITIC ────────────────────────────────
    all_results = []
    if scout_result and scout_result.get("success"):
        all_results.append(scout_result.get("text", ""))
    if analyst_result and analyst_result.get("success"):
        all_results.append(analyst_result.get("text", ""))
    if diver_result and diver_result.get("success"):
        all_results.append(diver_result.get("text", ""))
    
    combined = "\n\n---\n\n".join(all_results)
    
    if not combined:
        log_warn("manager", "No research results to evaluate")
        return
    
    # ── CRITIC ────────────────────────────────────────────────────
    score = 0
    try:
        critic = CriticAgent()
        eval_result = critic.evaluate(topic, combined)
        if eval_result.get("success"):
            score = eval_result.get("score", 5)
            log_info("critic", f"Score: {score}/10 via {eval_result.get('provider', '?')}")
            
            # Notify if high score
            min_notify = int(os.getenv("MIN_SCORE_TO_NOTIFY", "7"))
            if score >= min_notify:
                notify_high_score("critic", topic, score, combined[:500])
        else:
            log_warn("critic", f"Evaluation failed: {eval_result.get('error', 'unknown')}")
    except Exception as e:
        log_error("critic", f"Exception: {e}")
    
    # ── MEMORY SYNTHESIS ──────────────────────────────────────────
    try:
        memory = MemoryAgent()
        mem_result = memory.synthesize(combined, topic)
        if mem_result.get("success"):
            novelty = mem_result.get("novelty_score", 5)
            log_info("memory", f"Novelty: {novelty}/10 via {mem_result.get('provider', '?')}")
        else:
            log_warn("memory", f"Synthesis failed: {mem_result.get('error', 'unknown')}")
    except Exception as e:
        log_error("memory", f"Exception: {e}")
    
    log_manager("═══════════════════════════════════════════════════════════")
    log_manager("CYCLE COMPLETE")
    log_manager("═══════════════════════════════════════════════════════════")


def run_weekly_synthesis():
    """Run weekly synthesis."""
    log_manager("Running weekly synthesis...")
    try:
        synthesis = SynthesisAgent()
        result = synthesis.generate_weekly()
        if result.get("success"):
            log_info("synthesis", f"Weekly report complete via {result.get('provider', '?')}")
        else:
            log_warn("synthesis", f"Weekly synthesis failed: {result.get('error', 'unknown')}")
    except Exception as e:
        log_error("synthesis", f"Exception: {e}")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    """Main entry point with adaptive scheduling."""
    log_manager("═══════════════════════════════════════════════════════════════")
    log_manager("AGENT RESEARCH HUB v4 — Starting")
    log_manager("═══════════════════════════════════════════════════════════════")
    
    # Initialize
    init_db()
    init_manager_tables()
    seed_topics()
    pool.initialize()
    
    log_manager(f"Provider pool: {pool.get_available_count()}/{pool.get_total_count()} available")
    
    # Track for weekly synthesis
    last_weekly = db_get("last_weekly_synthesis", "")
    
    # Run initial cycle if providers available
    if should_run_cycle():
        run_cycle()
    
    # Main loop with adaptive timing
    while True:
        interval = get_adaptive_interval()
        log_manager(f"Next cycle in {interval} minutes")
        time.sleep(interval * 60)
        
        # Check for weekly synthesis (Sundays at midnight-ish)
        now = datetime.now()
        if now.weekday() == 6 and now.hour < 1:
            today = now.date().isoformat()
            if last_weekly != today:
                run_weekly_synthesis()
                db_set("last_weekly_synthesis", today)
                last_weekly = today
        
        # Run cycle if providers available
        if should_run_cycle():
            run_cycle()


if __name__ == "__main__":
    main()
