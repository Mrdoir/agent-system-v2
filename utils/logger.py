""" 
LOGGER v2 — stdout only. No log file writes.
Render captures stdout automatically in its log viewer.
Writing to logs/ on Render free tier is pointless (ephemeral + no viewer).
"""

from datetime import datetime


def log(agent_name: str, message: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{agent_name.upper()}] {message}", flush=True)


def log_manager(message: str):
    log("MANAGER", message)
