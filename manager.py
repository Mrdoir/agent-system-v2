"""
MANAGER AGENT v5 — adaptive timing + topic rotation + search guard
==================================================================
Fixes vs v4:
1. Picks topics itself: under-cap topics first, then least-researched in the
   last 30 days. No more 17k rows on one topic.
2. Skips a topic when the web returns nothing (agents invent data otherwise).
3. Critic results are saved again and scores are written to the cycle's rows.
4. Memory only learns from cycles the critic scored >= MIN_SCORE_FOR_MEMORY.
5. Reads agent output from "text" OR "content".
6. Weekly synthesis can't be skipped by long sleeps; a crashed cycle no
   longer kills the main loop.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import json
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

from agents.market_scout import MarketScout
from agents.trend_analyst import TrendAnalyst
from agents.deep_diver import DeepDiver
from agents.critic import CriticAgent
from agents.memory_agent import MemoryAgent
from agents.synthesis_agent import SynthesisAgent

from utils.logger import log_info, log_warn, log_error, log_manager, log_debug
from utils.database import init_db, save_result, get_conn
from utils.notifier import notify_high_score, notify_rate_limit_all
from utils.provider_pool import pool
from utils.web_search import search_comprehensive, diagnose_search

Path("state").mkdir(exist_ok=True)

# ── Configuration (all overridable from Render env vars) ──────────
MAX_RESULTS_PER_TOPIC = int(os.getenv("MAX_RESULTS_PER_TOPIC", "5"))     # per topic per window
TOPIC_RECENT_DAYS = int(os.getenv("TOPIC_RECENT_DAYS", "30"))            # window for the cap
DEFAULT_CYCLE_MINUTES = int(os.getenv("CYCLE_INTERVAL_MINUTES", "15"))
REQUIRE_WEB_DATA = os.getenv("REQUIRE_WEB_DATA", "1") == "1"             # 0 = research even with no web data
NO_DATA_COOLDOWN_HOURS = int(os.getenv("NO_DATA_COOLDOWN_HOURS", "6"))
MIN_SCORE_FOR_MEMORY = int(os.getenv("MIN_SCORE_FOR_MEMORY", "4"))
MIN_SCORE_TO_NOTIFY = int(os.getenv("MIN_SCORE_TO_NOTIFY", "7"))

RESEARCH_AGENTS = ("market_scout", "trend_analyst", "deep_diver")

# Runtime state
_no_data_until = {}   # topic -> epoch seconds when it may be tried again
_empty_streak = 0     # consecutive topics where search returned nothing

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
    """Create manager state tables if not exist. Migrate if needed."""
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
                added_at TEXT NOT NULL
            );
        """)
        conn.commit()

        try:
            cur.execute("ALTER TABLE research_topics ADD COLUMN priority INTEGER DEFAULT 0")
            conn.commit()
        except Exception:
            conn.rollback()  # column already exists

        cur.close()
        conn.close()
        log_manager("Postgres state tables ready")
    except Exception as e:
        log_error("manager", f"init_manager_tables error: {e}")


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
        log_debug("manager", f"db_get({key}) error: {e}")
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
        log_debug("manager", f"db_set({key}) error: {e}")


def seed_topics():
    """Seed initial topics into database."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        for topic in TOPIC_POOL:
            try:
                cur.execute("""
                    INSERT INTO research_topics (topic, added_at, priority)
                    VALUES (%s, %s, 0)
                    ON CONFLICT (topic) DO NOTHING
                """, (topic, datetime.now().isoformat()))
            except Exception:
                conn.rollback()
                cur.execute("""
                    INSERT INTO research_topics (topic, added_at)
                    VALUES (%s, %s)
                    ON CONFLICT (topic) DO NOTHING
                """, (topic, datetime.now().isoformat()))
        conn.commit()
        cur.close()
        conn.close()
        log_manager(f"Seeded {len(TOPIC_POOL)} topics")
    except Exception as e:
        log_error("manager", f"seed_topics error: {e}")


# ═══════════════════════════════════════════════════════════════════
# TOPIC SELECTION (replaces get_next_topic)
# ═══════════════════════════════════════════════════════════════════

def get_topic_candidates() -> list:
    """All known topics with priority + how many research rows they got recently."""
    cutoff = (datetime.now() - timedelta(days=TOPIC_RECENT_DAYS)).isoformat()
    topics = {}
    try:
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute("SELECT topic, COALESCE(priority, 0) FROM research_topics")
            rows = cur.fetchall()
        except Exception:
            conn.rollback()
            cur.execute("SELECT topic, 0 FROM research_topics")
            rows = cur.fetchall()
        for t, p in rows:
            topics[t] = {"topic": t, "priority": int(p or 0), "recent": 0}

        cur.execute(
            """SELECT topic, COUNT(*) FROM results
               WHERE created_at >= %s AND agent IN %s
               GROUP BY topic""",
            (cutoff, RESEARCH_AGENTS)
        )
        for t, c in cur.fetchall():
            if t in topics:
                topics[t]["recent"] = int(c)
        cur.close()
        conn.close()
    except Exception as e:
        log_error("manager", f"get_topic_candidates error: {e}")

    if not topics:
        topics = {t: {"topic": t, "priority": 0, "recent": 0} for t in TOPIC_POOL}
    return list(topics.values())


def pick_topic():
    """Under-cap topics first (highest priority, then fewest rows).
    If every topic is at the cap, take the least-researched one.
    Priority is ignored once capped, so one topic can never monopolise the loop."""
    now = time.time()
    cands = [c for c in get_topic_candidates() if _no_data_until.get(c["topic"], 0) <= now]
    if not cands:
        return None

    under = [c for c in cands if c["recent"] < MAX_RESULTS_PER_TOPIC]
    if under:
        best_priority = max(c["priority"] for c in under)
        group = [c for c in under if c["priority"] == best_priority]
    else:
        group = cands
    lowest = min(c["recent"] for c in group)
    choice = random.choice([c for c in group if c["recent"] == lowest])
    log_manager(f"Topic: {choice['topic']} (recent rows: {choice['recent']}, priority: {choice['priority']})")
    return choice["topic"]


# ═══════════════════════════════════════════════════════════════════
# SEARCH GUARD — no web data, no research
# ═══════════════════════════════════════════════════════════════════

def check_web_data(topic: str) -> bool:
    """Return False (and put the topic on cooldown) if the web gives us nothing."""
    global _empty_streak
    if not REQUIRE_WEB_DATA:
        return True

    try:
        data = search_comprehensive(topic, 3)
    except Exception as e:
        log_warn("manager", f"Search pre-check crashed: {e}")
        data = {}

    counts = {name: len(items) for name, items in data.items()}
    if sum(counts.values()) == 0:
        _empty_streak += 1
        _no_data_until[topic] = time.time() + NO_DATA_COOLDOWN_HOURS * 3600
        log_warn("manager", f"No web data for '{topic}' — skipping it for {NO_DATA_COOLDOWN_HOURS}h "
                            f"(streak {_empty_streak}). Sources: {counts}")
        if _empty_streak == 3 or _empty_streak % 20 == 0:
            try:
                log_error("manager", "SEARCH LOOKS DEAD — " + diagnose_search())
            except Exception as e:
                log_error("manager", f"diagnose_search failed: {e}")
        return False

    _empty_streak = 0
    log_info("manager", f"Web data OK: {counts}")
    return True


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def _text(result) -> str:
    """Agents may return the text under 'text' or 'content'."""
    if not result:
        return ""
    return (result.get("text") or result.get("content") or "").strip()


def _critic_row_exists(topic: str, since_iso: str) -> bool:
    """True if the critic already saved a row for this topic during this cycle."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM results WHERE agent = 'critic' AND topic = %s AND created_at >= %s",
            (topic, since_iso)
        )
        n = cur.fetchone()[0]
        cur.close()
        conn.close()
        return n > 0
    except Exception as e:
        log_debug("manager", f"_critic_row_exists error: {e}")
        return False


def _apply_scores(topic: str, score: int, since_iso: str):
    """Write the critic score onto this cycle's research rows."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """UPDATE results SET score = %s
               WHERE topic = %s AND created_at >= %s AND agent IN %s""",
            (score, topic, since_iso, RESEARCH_AGENTS)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log_error("manager", f"_apply_scores error: {e}")


# ═══════════════════════════════════════════════════════════════════
# ADAPTIVE TIMING — check provider health before each cycle
# ═══════════════════════════════════════════════════════════════════

def get_adaptive_interval() -> int:
    available = pool.get_available_count()
    total = pool.get_total_count()

    if available == 0:
        log_warn("manager", "All providers exhausted!")
        return 120
    elif available == 1:
        log_warn("manager", f"Only 1/{total} provider available, slowing down")
        return 60
    elif available <= 2:
        log_info("manager", f"Only {available}/{total} providers available")
        return 30
    return DEFAULT_CYCLE_MINUTES


def should_run_cycle() -> bool:
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
    cycle_start = datetime.now().isoformat()
    log_manager("═══════════════════════════════════════════════════════════")
    log_manager("STARTING RESEARCH CYCLE")
    log_manager("═══════════════════════════════════════════════════════════")

    topic = pick_topic()
    if not topic:
        log_warn("manager", "No eligible topic (all cooling down) — skipping cycle")
        return

    if not check_web_data(topic):
        return

    # ── RESEARCH AGENTS ───────────────────────────────────────────
    texts = []
    steps = [("market_scout", MarketScout), ("trend_analyst", TrendAnalyst), ("deep_diver", DeepDiver)]
    for name, cls in steps:
        try:
            res = cls().research(topic) or {}
            text = _text(res)
            if res.get("success") and text:
                texts.append(text)
                log_info(name, f"Research complete via {res.get('provider', '?')}")
            else:
                log_warn(name, f"Failed: {res.get('error', 'no text returned')}")
        except Exception as e:
            log_error(name, f"Exception: {e}")
        time.sleep(10)  # breathing room so the pool spreads across providers

    if not texts:
        log_warn("manager", "No research results to evaluate")
        return
    combined = "\n\n---\n\n".join(texts)

    # ── CRITIC ────────────────────────────────────────────────────
    score = None
    try:
        critic = CriticAgent()
        ev = critic.evaluate(topic, combined) or {}
        if ev.get("success"):
            score = ev.get("score")
            log_info("critic", f"Score: {score}/10 via {ev.get('provider', '?')}")

            critic_text = _text(ev)
            if critic_text and not _critic_row_exists(topic, cycle_start):
                save_result("critic", topic, critic_text, score or 0)

            if score is not None:
                _apply_scores(topic, score, cycle_start)
                if score >= MIN_SCORE_TO_NOTIFY:
                    notify_high_score("critic", topic, score, combined[:500])
        else:
            log_warn("critic", f"Evaluation failed: {ev.get('error', 'unknown')}")
    except Exception as e:
        log_error("critic", f"Exception: {e}")

    time.sleep(10)

    # ── MEMORY — only learn from cycles the critic scored well enough ──
    if score is not None and score >= MIN_SCORE_FOR_MEMORY:
        try:
            mem = MemoryAgent().synthesize(combined, topic) or {}
            if mem.get("success"):
                log_info("memory", f"Novelty: {mem.get('novelty_score', '?')}/10 via {mem.get('provider', '?')}")
            else:
                log_warn("memory", f"Synthesis failed: {mem.get('error', 'unknown')}")
        except Exception as e:
            log_error("memory", f"Exception: {e}")
    else:
        log_info("manager", f"Memory skipped (critic score: {score})")

    log_manager("═══════════════════════════════════════════════════════════")
    log_manager("CYCLE COMPLETE")
    log_manager("═══════════════════════════════════════════════════════════")


def safe_cycle():
    try:
        run_cycle()
    except Exception as e:
        log_error("manager", f"Cycle crashed: {e}")


def run_weekly_synthesis():
    log_manager("Running weekly synthesis...")
    try:
        result = SynthesisAgent().generate_weekly()
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
    log_manager("═══════════════════════════════════════════════════════════════")
    log_manager("AGENT RESEARCH HUB v5 — Starting")
    log_manager("═══════════════════════════════════════════════════════════════")

    init_db()
    init_manager_tables()
    seed_topics()
    pool.initialize()

    log_manager(f"Provider pool: {pool.get_available_count()}/{pool.get_total_count()} available")

    try:
        log_manager("SEARCH HEALTH: " + diagnose_search())
    except Exception as e:
        log_warn("manager", f"diagnose_search failed: {e}")

    last_weekly = db_get("last_weekly_synthesis", "")

    if should_run_cycle():
        safe_cycle()

    while True:
        interval = get_adaptive_interval()
        if _empty_streak >= 3:
            interval = max(interval, 60)
            log_warn("manager", f"Search returned nothing for {_empty_streak} topics in a row — slowing to {interval} min")
        log_manager(f"Next cycle in {interval} minutes")
        time.sleep(interval * 60)

        now = datetime.now()
        today = now.date().isoformat()
        if now.weekday() == 6 and last_weekly != today:   # any time on Sunday, once
            run_weekly_synthesis()
            db_set("last_weekly_synthesis", today)
            last_weekly = today

        if should_run_cycle():
            safe_cycle()


if __name__ == "__main__":
    main()
