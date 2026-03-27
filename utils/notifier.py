"""
Telegram notification system — sends alerts when agents find high-scoring insights.
Free via Telegram Bot API. No cost, instant delivery to your phone.

Setup:
1. Message @BotFather on Telegram → /newbot → get token
2. Message @userinfobot to get your chat ID
3. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to Railway variables
"""

import os
import requests
from utils.logger import log

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
MIN_SCORE_TO_NOTIFY = 7  # Only notify for high quality research (7+/10)


def send_telegram(message: str) -> bool:
    """Send a message via Telegram bot."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            },
            timeout=10
        )
        return resp.status_code == 200
    except Exception as e:
        log("notifier", f"Telegram error: {e}")
        return False


def notify_high_score(agent: str, topic: str, score: int, preview: str):
    """Send notification when research scores high."""
    if score < MIN_SCORE_TO_NOTIFY:
        return

    emoji = "🔥" if score >= 9 else "⭐"
    message = (
        f"{emoji} *High-Quality Research Found!*\n\n"
        f"*Agent:* {agent}\n"
        f"*Topic:* {topic}\n"
        f"*Score:* {score}/10\n\n"
        f"*Preview:*\n{preview[:300]}...\n\n"
        f"_Check your dashboard for full results_"
    )

    sent = send_telegram(message)
    if sent:
        log("notifier", f"Telegram alert sent: {topic} ({score}/10)")


def notify_rate_limit(agent: str, reset_minutes: int):
    """Notify when an agent hits rate limit (optional — can be noisy)."""
    # Only notify if ALL agents are limited (system pause)
    pass


def notify_daily_summary(total_results: int, new_today: int, top_insights: list):
    """Send daily summary of research progress."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    insights_text = ""
    for i, insight in enumerate(top_insights[:3], 1):
        insights_text += f"{i}. {insight[:100]}...\n"

    message = (
        f"📊 *Daily Research Summary*\n\n"
        f"*Total results:* {total_results}\n"
        f"*New today:* {new_today}\n\n"
        f"*Top insights today:*\n{insights_text}\n"
        f"_Agents are running 24/7_ 🤖"
    )

    send_telegram(message)
    log("notifier", "Daily summary sent to Telegram")
