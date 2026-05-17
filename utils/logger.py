"""
LOGGER v3 — Colored stdout logging with levels
Improvements:
- Color-coded output by log level and agent
- Timestamps with milliseconds for debugging
- Log levels (DEBUG, INFO, WARN, ERROR)
- Emoji indicators for quick scanning
"""

import os
from datetime import datetime

# ANSI color codes
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    # Agent colors
    "market_scout": "\033[94m",   # Blue
    "trend_analyst": "\033[92m",  # Green
    "deep_diver": "\033[95m",     # Purple
    "critic": "\033[91m",         # Red
    "memory": "\033[93m",         # Yellow
    "synthesis": "\033[96m",      # Cyan
    "manager": "\033[97m",        # White
    # Level colors
    "debug": "\033[90m",          # Gray
    "info": "\033[97m",           # White
    "warn": "\033[93m",           # Yellow
    "error": "\033[91m",          # Red
    "success": "\033[92m",        # Green
}

# Emoji indicators
EMOJIS = {
    "debug": "🔍",
    "info": "📝",
    "warn": "⚠️",
    "error": "❌",
    "success": "✅",
    "rate_limit": "🚫",
    "api_call": "🌐",
    "save": "💾",
    "start": "🚀",
    "complete": "✨",
}

# Check if running in terminal that supports colors
USE_COLORS = os.environ.get("TERM") or os.environ.get("RENDER")


def _colorize(text: str, color_key: str) -> str:
    """Apply color if terminal supports it."""
    if not USE_COLORS:
        return text
    color = COLORS.get(color_key, "")
    reset = COLORS["reset"]
    return f"{color}{text}{reset}"


def _format_timestamp() -> str:
    """Format current time with milliseconds."""
    now = datetime.now()
    return now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"


def log(agent_name: str, message: str, level: str = "info"):
    """
    Log a message with color and formatting.
    
    Args:
        agent_name: Name of the agent (market_scout, critic, etc.)
        message: Log message
        level: Log level (debug, info, warn, error, success)
    """
    ts = _format_timestamp()
    agent_upper = agent_name.upper()
    
    # Get emoji based on message content or level
    emoji = EMOJIS.get(level, "")
    if "rate limit" in message.lower():
        emoji = EMOJIS["rate_limit"]
    elif "trying" in message.lower() or "calling" in message.lower():
        emoji = EMOJIS["api_call"]
    elif "saved" in message.lower() or "save" in message.lower():
        emoji = EMOJIS["save"]
    elif "✓" in message or "success" in message.lower():
        emoji = EMOJIS["success"]
    elif "starting" in message.lower():
        emoji = EMOJIS["start"]
    elif "complete" in message.lower():
        emoji = EMOJIS["complete"]
    
    # Color the components
    ts_colored = _colorize(ts, "dim")
    agent_colored = _colorize(f"[{agent_upper}]", agent_name.lower())
    level_colored = _colorize(f"[{level.upper()}]", level)
    
    # Format and print
    print(f"{ts_colored} {agent_colored} {emoji} {message}", flush=True)


def log_debug(agent_name: str, message: str):
    """Log debug message (verbose, for troubleshooting)."""
    if os.environ.get("DEBUG"):
        log(agent_name, message, "debug")


def log_info(agent_name: str, message: str):
    """Log info message (normal operations)."""
    log(agent_name, message, "info")


def log_warn(agent_name: str, message: str):
    """Log warning message (non-critical issues)."""
    log(agent_name, message, "warn")


def log_error(agent_name: str, message: str):
    """Log error message (failures)."""
    log(agent_name, message, "error")


def log_success(agent_name: str, message: str):
    """Log success message (completions)."""
    log(agent_name, message, "success")


def log_manager(message: str, level: str = "info"):
    """Shortcut for manager logs."""
    log("manager", message, level)


def log_api_call(agent_name: str, provider: str, success: bool, details: str = ""):
    """Log an API call result."""
    if success:
        log_success(agent_name, f"{provider} responded {details}")
    else:
        log_warn(agent_name, f"{provider} failed {details}")


def log_rate_limit(agent_name: str, provider: str, reset_minutes: int):
    """Log a rate limit hit."""
    log_warn(agent_name, f"{provider} rate limited — will retry in {reset_minutes}m")


def log_research_start(agent_name: str, topic: str):
    """Log start of research."""
    log_info(agent_name, f"Starting research: {topic[:60]}...")


def log_research_complete(agent_name: str, topic: str, score: int = None):
    """Log completion of research."""
    score_str = f" (score: {score}/10)" if score is not None else ""
    log_success(agent_name, f"Completed: {topic[:50]}...{score_str}")
