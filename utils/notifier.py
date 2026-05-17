"""
NOTIFIER v3 — Multi-platform notifications (all free)
Improvements:
- Discord webhook support
- Slack webhook support
- Better message formatting
- Notification batching (avoid spam)
- Daily digest scheduling
"""

import os
import time
import requests
from datetime import datetime, date
from utils.logger import log_info, log_error, log_debug

# Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
MIN_SCORE_TO_NOTIFY = int(os.getenv("MIN_SCORE_TO_NOTIFY", "7"))

# Rate limiting
_last_notification_time = 0
_notification_cooldown = 60  # seconds between notifications
_daily_summary_sent = None


def _can_send_notification() -> bool:
    """Check if we can send a notification (rate limiting)."""
    global _last_notification_time
    now = time.time()
    if now - _last_notification_time < _notification_cooldown:
        return False
    _last_notification_time = now
    return True


# ═══════════════════════════════════════════════════════════════════
# TELEGRAM
# ═══════════════════════════════════════════════════════════════════

def send_telegram(message: str, parse_mode: str = "Markdown") -> bool:
    """Send a message via Telegram bot."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    
    try:
        # Truncate if too long
        if len(message) > 4000:
            message = message[:3997] + "..."
        
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            },
            timeout=10
        )
        
        if resp.status_code == 200:
            log_debug("notifier", "Telegram message sent")
            return True
        else:
            log_error("notifier", f"Telegram failed: {resp.status_code}")
            return False
            
    except Exception as e:
        log_error("notifier", f"Telegram error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════
# DISCORD
# ═══════════════════════════════════════════════════════════════════

def send_discord(message: str = None, embed: dict = None) -> bool:
    """Send a message via Discord webhook."""
    if not DISCORD_WEBHOOK_URL:
        return False
    
    try:
        payload = {}
        
        if message:
            payload["content"] = message[:2000]  # Discord limit
        
        if embed:
            payload["embeds"] = [embed]
        
        resp = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=10
        )
        
        if resp.status_code in [200, 204]:
            log_debug("notifier", "Discord message sent")
            return True
        else:
            log_error("notifier", f"Discord failed: {resp.status_code}")
            return False
            
    except Exception as e:
        log_error("notifier", f"Discord error: {e}")
        return False


def send_discord_embed(title: str, description: str, color: int = 0x7c6fcd, 
                       fields: list = None, footer: str = None) -> bool:
    """Send a rich embed to Discord."""
    embed = {
        "title": title,
        "description": description[:4096],  # Discord limit
        "color": color,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if fields:
        embed["fields"] = fields[:25]  # Discord limit
    
    if footer:
        embed["footer"] = {"text": footer}
    
    return send_discord(embed=embed)


# ═══════════════════════════════════════════════════════════════════
# SLACK
# ═══════════════════════════════════════════════════════════════════

def send_slack(message: str = None, blocks: list = None) -> bool:
    """Send a message via Slack webhook."""
    if not SLACK_WEBHOOK_URL:
        return False
    
    try:
        payload = {}
        
        if message:
            payload["text"] = message
        
        if blocks:
            payload["blocks"] = blocks
        
        resp = requests.post(
            SLACK_WEBHOOK_URL,
            json=payload,
            timeout=10
        )
        
        if resp.status_code == 200:
            log_debug("notifier", "Slack message sent")
            return True
        else:
            log_error("notifier", f"Slack failed: {resp.status_code}")
            return False
            
    except Exception as e:
        log_error("notifier", f"Slack error: {e}")
        return False


def send_slack_rich(title: str, text: str, color: str = "#7c6fcd", 
                    fields: list = None) -> bool:
    """Send a rich Slack message with attachments."""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": title}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text[:3000]}
        }
    ]
    
    if fields:
        field_block = {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*{f['title']}*\n{f['value']}"}
                for f in fields[:10]
            ]
        }
        blocks.append(field_block)
    
    return send_slack(blocks=blocks)


# ═══════════════════════════════════════════════════════════════════
# UNIFIED NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════

def notify_all(message: str):
    """Send notification to all configured platforms."""
    send_telegram(message)
    send_discord(message)
    send_slack(message)


def notify_high_score(agent: str, topic: str, score: int, preview: str):
    """Notify when research scores high (quality alert)."""
    if score < MIN_SCORE_TO_NOTIFY:
        return
    
    if not _can_send_notification():
        log_debug("notifier", "Skipping notification (rate limited)")
        return
    
    emoji = "🔥" if score >= 9 else "⭐"
    
    # Telegram (Markdown)
    tg_message = (
        f"{emoji} *High-Quality Research Found!*\n\n"
        f"*Agent:* {agent}\n"
        f"*Topic:* {topic}\n"
        f"*Score:* {score}/10\n\n"
        f"*Preview:*\n{preview[:300]}...\n\n"
        f"_Check your dashboard for full results_"
    )
    send_telegram(tg_message)
    
    # Discord (Embed)
    color = 0xff6b6b if score >= 9 else 0xffd93d
    send_discord_embed(
        title=f"{emoji} High-Quality Research Found!",
        description=preview[:500] + "...",
        color=color,
        fields=[
            {"name": "Agent", "value": agent, "inline": True},
            {"name": "Topic", "value": topic[:50], "inline": True},
            {"name": "Score", "value": f"{score}/10", "inline": True}
        ],
        footer="Agent Research Hub"
    )
    
    # Slack
    send_slack_rich(
        title=f"{emoji} High-Quality Research Found!",
        text=preview[:500] + "...",
        fields=[
            {"title": "Agent", "value": agent},
            {"title": "Topic", "value": topic[:50]},
            {"title": "Score", "value": f"{score}/10"}
        ]
    )
    
    log_info("notifier", f"Sent high-score alert: {topic} ({score}/10)")


def notify_rate_limit_all(reset_minutes: int):
    """Notify when ALL agents are rate limited (system pause)."""
    message = (
        f"⚠️ *System Paused*\n\n"
        f"All agents are rate limited.\n"
        f"System will auto-resume in ~{reset_minutes} minutes.\n\n"
        f"_This is normal — free API tiers have limits_"
    )
    notify_all(message)


def notify_daily_summary(total_results: int, new_today: int, top_insights: list):
    """Send daily summary of research progress."""
    global _daily_summary_sent
    
    # Only send once per day
    today = date.today()
    if _daily_summary_sent == today:
        return
    _daily_summary_sent = today
    
    insights_text = ""
    for i, insight in enumerate(top_insights[:3], 1):
        insights_text += f"{i}. {insight[:100]}...\n"
    
    # Telegram
    tg_message = (
        f"📊 *Daily Research Summary*\n"
        f"_{datetime.now().strftime('%B %d, %Y')}_\n\n"
        f"*Total results:* {total_results}\n"
        f"*New today:* {new_today}\n\n"
        f"*Top insights:*\n{insights_text}\n"
        f"_Agents running 24/7_ 🤖"
    )
    send_telegram(tg_message)
    
    # Discord
    send_discord_embed(
        title="📊 Daily Research Summary",
        description=f"_{datetime.now().strftime('%B %d, %Y')}_",
        color=0x7c6fcd,
        fields=[
            {"name": "Total Results", "value": str(total_results), "inline": True},
            {"name": "New Today", "value": str(new_today), "inline": True},
            {"name": "Top Insights", "value": insights_text or "No insights yet", "inline": False}
        ],
        footer="Agents running 24/7 🤖"
    )
    
    log_info("notifier", "Daily summary sent")


def notify_weekly_synthesis(synthesis_text: str, result_count: int):
    """Send weekly synthesis report."""
    header = (
        f"📊 *WEEKLY RESEARCH SYNTHESIS*\n"
        f"_{datetime.now().strftime('%B %d, %Y')}_\n"
        f"_Based on {result_count} research results_\n\n"
    )
    
    full_message = header + synthesis_text
    
    # Split into chunks for Telegram (4096 char limit)
    chunks = [full_message[i:i+4000] for i in range(0, len(full_message), 4000)]
    
    for i, chunk in enumerate(chunks):
        if i > 0:
            chunk = f"_(part {i+1}/{len(chunks)})_\n\n{chunk}"
        send_telegram(chunk)
    
    # Discord (truncated)
    send_discord_embed(
        title="📊 Weekly Research Synthesis",
        description=synthesis_text[:4000],
        color=0x7c6fcd,
        footer=f"Based on {result_count} results"
    )
    
    log_info("notifier", f"Weekly synthesis sent ({len(chunks)} parts)")


def notify_agent_error(agent: str, error: str):
    """Notify when an agent encounters an error."""
    message = (
        f"❌ *Agent Error*\n\n"
        f"*Agent:* {agent}\n"
        f"*Error:* {error[:200]}\n\n"
        f"_Agent will retry on next cycle_"
    )
    
    # Only send to Telegram (avoid spam on Discord/Slack)
    send_telegram(message)


def notify_new_insight(content: str, novelty_score: int, source_topics: list):
    """Notify when a novel insight is discovered."""
    if novelty_score < 7:  # Only notify for high-novelty insights
        return
    
    topics_str = ", ".join(source_topics[:3]) if source_topics else "multiple topics"
    
    message = (
        f"💡 *New Research Insight!*\n"
        f"_Novelty: {novelty_score}/10_\n\n"
        f"{content[:400]}...\n\n"
        f"_From: {topics_str}_"
    )
    
    send_telegram(message)
    
    send_discord_embed(
        title="💡 New Research Insight!",
        description=content[:1000],
        color=0x22c55e,
        fields=[
            {"name": "Novelty Score", "value": f"{novelty_score}/10", "inline": True},
            {"name": "Source Topics", "value": topics_str, "inline": True}
        ]
    )
