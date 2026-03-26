"""Logging utility for all agents."""

from datetime import datetime
from pathlib import Path

Path("logs").mkdir(exist_ok=True)
LOG_FILE = "logs/agent_system.log"

def log(agent_name: str, message: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{agent_name.upper()}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def log_manager(message: str):
    log("MANAGER", message)
