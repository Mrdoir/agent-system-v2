"""
SMART SCHEDULER v1 — Adaptive agent scheduling
================================================
Instead of firing all agents simultaneously every 15 minutes,
this scheduler:

1. Staggers agents with 3-minute gaps between them
2. Adapts cycle interval based on key availability
3. Pauses intelligently when keys are hot (waits for exact reset)
4. Tracks optimal execution windows
"""

import time
from datetime import datetime
from utils.provider_pool import pool
from utils.logger import log_info, log_warn, log_manager


class SmartScheduler:
    """
    Manages when agents should run to maximize uptime.
    """
    
    def __init__(self, base_interval_minutes: int = 15):
        self.base_interval = base_interval_minutes * 60  # seconds
        self.min_interval = 10 * 60   # never faster than 10 min
        self.max_interval = 45 * 60   # never slower than 45 min
        
        # Stagger config: seconds between each agent
        self.agent_stagger = 180  # 3 minutes between agents
        
        # Track cycles
        self.cycles_completed = 0
        self.last_cycle_start = 0
        self.last_cycle_duration = 0
        self.consecutive_full_exhaustions = 0
    
    def get_current_interval(self) -> int:
        """
        Calculate optimal cycle interval based on pool health.
        
        - Lots of keys available -> shorter intervals (more research)
        - Few keys available -> longer intervals (conserve)
        - All exhausted -> wait for next key to free up
        """
        pool.initialize()
        
        available = pool.get_available_count()
        total = pool.get_total_count()
        
        if total == 0:
            return self.max_interval
        
        availability_ratio = available / total
        
        if availability_ratio >= 0.7:
            # Plenty of keys — run frequently
            interval = self.min_interval
            self.consecutive_full_exhaustions = 0
        elif availability_ratio >= 0.4:
            # Some keys available — normal pace
            interval = self.base_interval
            self.consecutive_full_exhaustions = 0
        elif availability_ratio > 0:
            # Few keys — slow down
            interval = int(self.base_interval * 1.5)
            self.consecutive_full_exhaustions = 0
        else:
            # ALL exhausted — wait for next key
            self.consecutive_full_exhaustions += 1
            next_available = pool.get_next_available_time()
            if next_available > 0:
                # Wait exactly until the next key frees up + 30s buffer
                interval = next_available + 30
                log_info("scheduler", 
                    f"All keys exhausted. Waiting {interval}s for next key.")
            else:
                # Fallback: progressive backoff
                backoff = min(self.consecutive_full_exhaustions * 120, 1800)
                interval = self.base_interval + backoff
        
        # Clamp to bounds
        interval = max(self.min_interval, min(self.max_interval, interval))
        return interval
    
    def get_agent_order(self) -> list:
        """
        Return agents in optimal execution order.
        Rotates order each cycle to spread load fairly.
        """
        base_order = ["market_scout", "trend_analyst", "deep_diver"]
        # Rotate based on cycle count
        rotation = self.cycles_completed % len(base_order)
        return base_order[rotation:] + base_order[:rotation]
    
    def should_run_agent(self, agent_name: str) -> bool:
        """
        Check if we have enough keys to justify running this agent.
        Returns False if pool is too depleted.
        """
        pool.initialize()
        available = pool.get_available_count()
        
        if available == 0:
            log_warn("scheduler", f"Skipping {agent_name}: no keys available")
            return False
        
        return True
    
    def get_stagger_delay(self, agent_index: int) -> int:
        """Seconds to wait before running agent at this index."""
        return agent_index * self.agent_stagger
    
    def record_cycle_complete(self):
        """Record that a research cycle completed."""
        self.cycles_completed += 1
        now = time.time()
        if self.last_cycle_start > 0:
            self.last_cycle_duration = now - self.last_cycle_start
        self.last_cycle_start = now
    
    def get_status(self) -> dict:
        """Scheduler status for dashboard."""
        return {
            "cycles_completed": self.cycles_completed,
            "current_interval_seconds": self.get_current_interval(),
            "agent_stagger_seconds": self.agent_stagger,
            "consecutive_exhaustions": self.consecutive_full_exhaustions,
            "last_cycle_duration": round(self.last_cycle_duration, 1),
            "pool_status": pool.get_status()
        }
