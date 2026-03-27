"""
MANAGER AGENT - The Brain
Full pipeline: Scout → Analyst → Deep Diver → Critic → Memory
Persistent state via SQLite database.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import json
import time
import schedule
import threading
from datetime import datetime
from pathlib import Path
from agents.market_scout import MarketScout
from agents.trend_analyst import TrendAnalyst
from agents.deep_diver import DeepDiver
from agents.critic import CriticAgent
from agents.memory_agent import MemoryAgent
from utils.logger import log, log_manager
from utils.database import (
    init_db, save_result, get_total_results,
    update_agent_status, get_recent_topics, add_do_not_repeat
)

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
        self.task_queue = self.state.get("task_queue", [])
        self.completed = self.state.get("completed", [])
        log_manager("Manager Agent initialized. Pipeline: Scout→Analyst→Diver→Critic→Memory")

    def _load_state(self):
        if Path(STATE_FILE).exists():
            with open(STATE_FILE) as f:
                return json.load(f)
        return {}

    def _save_state(self):
        with open(STATE_FILE, "w") as f:
            json.dump({"task_queue": self.task_queue, "completed": self.completed}, f, indent=2)

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
        topics = self.load_topics()
        done_keys = {(t["agent"], t["topic"]) for t in self.completed}
        queued_keys = {(t["agent"], t["topic"]) for t in self.task_queue}

        for topic in topics:
            for agent_name in ["market_scout", "trend_analyst", "deep_diver"]:
                key = (agent_name, topic)
                if key not in done_keys and key not in queued_keys:
                    self.task_queue.append({"agent": agent_name, "topic": topic, "status": "pending"})

        log_manager(f"Queue: {len([t for t in self.task_queue if t['status'] == 'pending'])} pending tasks")
        self._save_state()

    def run_pipeline_for_topic(self, topic: str, results_by_topic: dict):
        """Run Critic + Memory on all research collected for a topic."""
        contents = results_by_topic.get(topic, [])
        if not contents:
            return

        combined = "\n\n---\n\n".join(contents)
        log_manager(f"Running Critic on: {topic}")

        # Critic pass
        if not self.critic.is_rate_limited():
            crit_result = self.critic.evaluate(topic, combined)
            if crit_result["success"]:
                score = crit_result["score"]
                save_result("critic", topic, crit_result["text"], score)
                log_manager(f"Critic scored '{topic}': {score}/10")

                # Memory pass — only on decent quality research
                if score >= 4 and not self.memory.is_rate_limited():
                    mem_result = self.memory.synthesize(combined + "\n\n" + crit_result["text"], topic)
                    if mem_result["success"]:
                        log_manager(f"Memory updated (novelty: {mem_result.get('novelty_score', '?')}/10)")
            else:
                log_manager(f"Critic skipped: {crit_result.get('error', 'rate limited')}")

    def run_cycle(self):
        log_manager("--- Starting work cycle ---")
        pending = [t for t in self.task_queue if t["status"] == "pending"]

        if not pending:
            log_manager("All topics done! Resetting for next round...")
            self.task_queue = []
            self.completed = []
            self._save_state()
            self.build_task_queue()
            pending = [t for t in self.task_queue if t["status"] == "pending"]

        results_by_topic = {}

        for task in pending:
            agent_name = task["agent"]
            agent = self.agents[agent_name]
            topic = task["topic"]

            if agent.is_rate_limited():
                log_manager(f"[{agent_name}] Rate limited (~{agent.minutes_until_reset()} min). Skipping.")
                continue

            log_manager(f"[{agent_name}] Researching: {topic}")
            result = agent.research(topic)

            if result["success"]:
                task["status"] = "done"
                self.completed.append({"agent": agent_name, "topic": topic, "timestamp": datetime.now().isoformat()})

                # Collect for pipeline
                if topic not in results_by_topic:
                    results_by_topic[topic] = []
                results_by_topic[topic].append(result["content"])

                log_manager(f"[{agent_name}] ✓ Done: {topic}")
            elif result.get("rate_limited"):
                log_manager(f"[{agent_name}] Hit rate limit mid-task.")
            else:
                log_manager(f"[{agent_name}] ✗ Error: {result.get('error', '?')}")
                task["status"] = "error"

            self._save_state()
            time.sleep(3)

        # Run Critic + Memory on completed topics
        for topic in results_by_topic:
            self.run_pipeline_for_topic(topic, results_by_topic)
            time.sleep(2)

        total = get_total_results()
        log_manager(f"--- Cycle complete. Total DB results: {total} ---\n")

    def status(self):
        print("\n" + "="*50)
        print("  AGENT SYSTEM STATUS")
        print("="*50)
        for name, agent in self.agents.items():
            limited = agent.is_rate_limited()
            reset = f"resets in {agent.minutes_until_reset()} min" if limited else "available"
            print(f"  {name:<20} {'🔴 LIMITED' if limited else '🟢 READY'} ({reset})")
        print(f"  {'critic':<20} {'🔴 LIMITED' if self.critic.is_rate_limited() else '🟢 READY'}")
        print(f"  {'memory':<20} {'🔴 LIMITED' if self.memory.is_rate_limited() else '🟢 READY'}")
        pending = len([t for t in self.task_queue if t["status"] == "pending"])
        print(f"\n  Pending tasks : {pending}")
        print(f"  DB results    : {get_total_results()}")
        print("="*50 + "\n")

    def start(self):
        log_manager("🚀 Manager started. Full 5-agent pipeline active.")
        self.build_task_queue()
        self.status()

        # Start dashboard
        try:
            from dashboard import app
            t = threading.Thread(
                target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), use_reloader=False, threaded=True),
                daemon=True
            )
            t.start()
            log_manager("📊 Dashboard running")
        except Exception as e:
            log_manager(f"Dashboard error: {e}")

        self.run_cycle()
        schedule.every(15).minutes.do(self.run_cycle)

        while True:
            schedule.run_pending()
            time.sleep(60)


if __name__ == "__main__":
    manager = ManagerAgent()
    try:
        manager.start()
    except KeyboardInterrupt:
        log_manager("Manager stopped.")
        manager.status()
