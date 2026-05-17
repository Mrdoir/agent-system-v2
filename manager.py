"""
MANAGER AGENT v4 — Orchestrates all research agents
Improvements:
- Smarter topic selection (avoid saturated)
- Parallel agent execution option
- Better error recovery
- Analytics tracking
- Daily/weekly summaries
"""

from dotenv import load_dotenv
load_dotenv()

import os
import json
import time
import schedule
import threading
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

# Ensure state directory exists
Path("state").mkdir(exist_ok=True)

# Configuration
MAX_RESULTS_PER_TOPIC = int(os.getenv("MAX_RESULTS_PER_TOPIC", "5"))
CYCLE_INTERVAL_MINUTES = int(os.getenv("CYCLE_INTERVAL_MINUTES", "15"))

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
                VALUES (%s, %s, %s)
                ON CONFLICT (topic) DO NOTHING
            """, (topic, datetime.now().isoformat(), 1))
        conn.commit()
        cur.close()
        conn.close()
        log_manager(f"Seeded {len(TOPIC_POOL)} topics")
    except Exception as e:
        log_debug("manager", f"seed_topics error: {e}")


# ═══════════════════════════════════════════════════════════════════
# RESEARCH CYCLE
# ═══════════════════════════════════════════════════════════════════

def get_available_agents() -> list:
    """Get agents that aren't rate limited."""
    agents = [
        ("market_scout", MarketScout()),
        ("trend_analyst", TrendAnalyst()),
        ("deep_diver", DeepDiver()),
    ]
    
    available = []
    for name, agent in agents:
        if not agent.is_rate_limited():
            available.append((name, agent))
        else:
            mins = agent.minutes_until_reset()
            log_debug("manager", f"{name} rate limited for {mins}m")
    
    return available


def select_topic(completed_this_cycle: list = None) -> str:
    """Select the best topic to research next."""
    completed = completed_this_cycle or []
    
    # Try to get a prioritized topic
    prioritized = get_prioritized_topics(limit=20)
    
    for topic in prioritized:
        if topic not in completed and not is_topic_saturated(topic):
            return topic
    
    # Fall back to dynamic topic selection
    return get_next_topic(exclude=completed)


def run_research_cycle():
    """Run one complete research cycle."""
    log_manager("═══════════════════════════════════════════════════")
    log_manager("Starting research cycle")
    log_manager("═══════════════════════════════════════════════════")
    
    # Rotate topics if needed
    rotate_topics()
    
    # Get available agents
    available = get_available_agents()
    
    if not available:
        log_warn("manager", "All agents rate limited! Waiting for reset...")
        notify_rate_limit_all(60)
        return
    
    log_manager(f"{len(available)} agents available: {[a[0] for a in available]}")
    
    # Track completed topics this cycle
    completed = []
    
    # Run each available agent on a topic
    for agent_name, agent in available:
        topic = select_topic(completed)
        log_manager(f"Assigning {agent_name} to: {topic[:50]}...")
        
        try:
            result = agent.research(topic)
            
            if result.get("success"):
                log_manager(f"✓ {agent_name} completed research")
                completed.append(topic)
            elif result.get("rate_limited"):
                log_warn("manager", f"{agent_name} hit rate limit")
            else:
                log_warn("manager", f"{agent_name} failed: {result.get('error', 'Unknown')}")
                
        except Exception as e:
            log_error("manager", f"{agent_name} exception: {e}")
    
    # If we have results, run critic
    if completed:
        run_critic_evaluation(completed)
    
    # Run memory synthesis
    run_memory_synthesis()
    
    # Log summary
    log_summary()


def run_critic_evaluation(topics: list):
    """Run critic to evaluate recent research."""
    critic = CriticAgent()
    
    if critic.is_rate_limited():
        log_debug("manager", "Critic rate limited, skipping evaluation")
        return
    
    # Get recent research content
    recent = get_results(limit=10)
    
    if not recent:
        return
    
    # Combine recent research for evaluation
    combined_content = "\n\n---\n\n".join([
        f"[{r.get('agent', '?')} | {r.get('topic', '')}]\n{r.get('content', '')[:800]}"
        for r in recent[:5]
    ])
    
    topic = topics[0] if topics else "Multiple topics"
    
    log_manager("Running critic evaluation...")
    
    try:
        result = critic.evaluate(topic, combined_content)
        
        if result.get("success"):
            score = result.get("score", 0)
            log_manager(f"✓ Critic scored research: {score}/10")
            
            # Notify if high quality
            if score >= 7:
                takeaways = result.get("takeaways", [])
                preview = takeaways[0] if takeaways else "High-quality research found"
                notify_high_score("critic", topic, score, preview)
        else:
            log_warn("manager", f"Critic evaluation failed: {result.get('error')}")
            
    except Exception as e:
        log_error("manager", f"Critic exception: {e}")


def run_memory_synthesis():
    """Run memory agent to synthesize recent research."""
    memory = MemoryAgent()
    
    if memory.is_rate_limited():
        log_debug("manager", "Memory agent rate limited, skipping synthesis")
        return
    
    # Get recent results
    recent = get_results(limit=5)
    
    if not recent:
        return
    
    # Synthesize the most recent research
    latest = recent[0]
    
    log_manager("Running memory synthesis...")
    
    try:
        result = memory.synthesize(latest.get("content", ""), latest.get("topic", ""))
        
        if result.get("success"):
            novelty = result.get("novelty_score", 0)
            log_manager(f"✓ Memory synthesis complete (novelty: {novelty}/10)")
        else:
            log_debug("manager", f"Memory synthesis failed: {result.get('error')}")
            
    except Exception as e:
        log_error("manager", f"Memory exception: {e}")


def log_summary():
    """Log current system status."""
    try:
        analytics = get_analytics_summary()
        overall = analytics.get("overall", {})
        
        log_manager("───────────────────────────────────────────────────")
        log_manager(f"Total Results: {overall.get('total_results', 0)}")
        log_manager(f"Avg Score: {overall.get('avg_score', 0):.1f}/10")
        log_manager(f"High Quality (7+): {overall.get('high_quality', 0)}")
        log_manager(f"Last 24h: {analytics.get('last_24h', 0)} new results")
        log_manager("───────────────────────────────────────────────────")
        
    except Exception as e:
        log_debug("manager", f"log_summary error: {e}")


# ═══════════════════════════════════════════════════════════════════
# SCHEDULED JOBS
# ═══════════════════════════════════════════════════════════════════

def run_daily_summary():
    """Run daily summary (end of day)."""
    log_manager("Running daily summary...")
    
    try:
        total = get_total_results()
        today = date.today().isoformat()
        
        # Count today's results
        results = get_results(limit=100)
        new_today = len([r for r in results if r.get("created_at", "").startswith(today)])
        
        # Get top insights
        insights = get_insights(limit=5)
        top_insights = [i.get("content", "")[:100] for i in insights]
        
        notify_daily_summary(total, new_today, top_insights)
        
        # Save last summary date
        db_set("last_summary_date", today)
        
    except Exception as e:
        log_error("manager", f"Daily summary error: {e}")


def run_weekly_synthesis():
    """Run weekly synthesis (Sunday)."""
    if datetime.now().weekday() != 6:  # Only on Sunday
        return
    
    log_manager("Running weekly synthesis...")
    
    try:
        synthesis = SynthesisAgent()
        result = synthesis.synthesize()
        
        if result.get("success"):
            log_manager("✓ Weekly synthesis complete")
        else:
            log_warn("manager", f"Weekly synthesis failed: {result.get('error')}")
            
    except Exception as e:
        log_error("manager", f"Weekly synthesis error: {e}")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    """Main entry point."""
    log_manager("═══════════════════════════════════════════════════")
    log_manager("    AGENT RESEARCH HUB v4")
    log_manager("═══════════════════════════════════════════════════")
    
    # Initialize
    log_manager("Initializing database...")
    init_db()
    init_manager_tables()
    seed_topics()
    
    # Initial rotation
    rotate_topics()
    
    # Schedule jobs
    log_manager(f"Scheduling research cycle every {CYCLE_INTERVAL_MINUTES} minutes")
    schedule.every(CYCLE_INTERVAL_MINUTES).minutes.do(run_research_cycle)
    schedule.every().day.at("23:00").do(run_daily_summary)
    schedule.every().sunday.at("10:00").do(run_weekly_synthesis)
    
    # Run first cycle immediately
    log_manager("Running initial research cycle...")
    run_research_cycle()
    
    # Main loop
    log_manager("Entering main loop (Ctrl+C to stop)")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
        except KeyboardInterrupt:
            log_manager("Shutting down...")
            break
        except Exception as e:
            log_error("manager", f"Main loop error: {e}")
            time.sleep(60)  # Wait a minute on error


if __name__ == "__main__":
    main()
