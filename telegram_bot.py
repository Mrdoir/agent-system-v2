"""
TELEGRAM BOT MANAGER
Listens for your messages and answers questions about research progress.
Uses Gemini with smart caching to stay within free quota limits.
"""

import os
import time
import json
import threading
import requests
from utils.logger import log
from utils.database import get_results, get_insights, get_total_results, get_agent_statuses
from utils.notifier import send_telegram

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
GEMINI_API_KEY = os.getenv("GEMINI_BOT_KEY") or os.getenv("GEMINI_API_KEY", "")

_last_update_id = 0
_answer_cache = {}
_cache_time = {}
CACHE_MINUTES = 10


def get_updates():
    global _last_update_id
    if not TELEGRAM_TOKEN:
        return []
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
            params={"offset": _last_update_id + 1, "timeout": 10},
            timeout=15
        )
        if resp.status_code != 200:
            return []
        updates = resp.json().get("result", [])
        if updates:
            _last_update_id = updates[-1]["update_id"]
        return updates
    except Exception as e:
        log("telegram_bot", f"Poll error: {e}")
        return []


def reply(text: str):
    send_telegram(text)


def get_research_context():
    total = get_total_results()
    results = get_results(limit=20)
    insights = get_insights(limit=5)

    if total == 0:
        return None, total

    top = sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:5]
    top_text = "\n".join([
        f"- [{r['score']}/10] Topic: {r['topic']} | Agent: {r['agent']} | Preview: {r['content'][:300]}"
        for r in top if r.get("score", 0) > 0
    ])

    recent_text = "\n".join([
        f"- Topic: {r['topic']} | Content: {r['content'][:200]}"
        for r in results[:10]
    ])

    insight_text = "\n".join([
        f"- {i['content'][:200]}"
        for i in insights[:3]
    ]) if insights else "No insights yet."

    context = f"""TOTAL RESULTS IN DATABASE: {total}

TOP SCORED FINDINGS:
{top_text or 'No scored results yet.'}

RECENT RESEARCH (last 10):
{recent_text}

TOP INSIGHTS:
{insight_text}"""

    return context, total


def ask_gemini(user_message: str, context: str) -> str:
    """Ask Gemini with caching to avoid quota issues."""
    if not GEMINI_API_KEY:
        log("telegram_bot", "No Gemini API key found!")
        return None

    # Check cache first
    cache_key = user_message.lower().strip()[:100]
    if cache_key in _answer_cache:
        age_minutes = (time.time() - _cache_time[cache_key]) / 60
        if age_minutes < CACHE_MINUTES:
            log("telegram_bot", f"Returning cached answer for: {cache_key[:30]}")
            return _answer_cache[cache_key]

    prompt = f"""You are a friendly AI research assistant. Keep responses SHORT (max 4-5 sentences).
Be direct and highlight the most interesting findings. Use simple language with occasional emojis.
Never use markdown headers. Just plain conversational text.

CURRENT RESEARCH DATA:
{context}

USER ASKED: {user_message}

Give a short, specific, helpful answer based on the research data above."""

    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 400, "temperature": 0.7}
            },
            timeout=30
        )
        data = resp.json()
        if "candidates" in data:
            answer = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Cache the answer
            _answer_cache[cache_key] = answer
            _cache_time[cache_key] = time.time()
            return answer
        elif data.get("error", {}).get("code") == 429:
            # Rate limited — return a helpful fallback instead
            log("telegram_bot", "Gemini rate limited, using fallback")
            return None
        else:
            log("telegram_bot", f"Gemini error: {data}")
            return None
    except Exception as e:
        log("telegram_bot", f"Gemini error: {e}")
        return None


def get_quick_summary() -> str:
    """Build a quick summary without AI for when Gemini is rate limited."""
    total = get_total_results()
    if total == 0:
        return "🤖 Agents are running but no results yet. Check back in 15 minutes!"

    results = get_results(limit=20)
    top = sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:3]

    if not top or top[0].get("score", 0) == 0:
        recent = results[:3]
        topics = [r["topic"] for r in recent]
        return f"📊 {total} results collected so far! Agents are researching: {', '.join(topics[:2])}. Try /best or /summary for more details!"

    lines = [f"• {r['score']}/10 — {r['topic']}" for r in top]
    return f"📊 {total} results collected! Top findings:\n" + "\n".join(lines) + "\n\nTry /best for full details!"


def handle_command(text: str) -> str:
    context, total = get_research_context()
    cmd = text.strip().lower().split()[0]

    if cmd == "/start":
        return (
            "👋 Hey! I'm your research assistant bot.\n\n"
            "You can ask me anything like:\n"
            "• What did the agents find?\n"
            "• Any good app ideas?\n"
            "• What are the biggest trends?\n"
            "• /status — agent status\n"
            "• /best — top discoveries\n"
            "• /topics — current research topics\n"
            "• /summary — quick overview\n\n"
            "I'll keep you updated on the best findings! 🔍"
        )

    if cmd == "/status":
        statuses = get_agent_statuses()
        if not statuses:
            return f"🤖 Agents are running! {total} results collected so far."
        lines = []
        for name, info in statuses.items():
            status = "✅ Active" if info.get("status") == "active" else "⏸ Limited"
            tasks = info.get("tasks_completed", 0)
            lines.append(f"{status} {name} — {tasks} tasks done")
        return "📊 Agent Status\n\n" + "\n".join(lines) + f"\n\nTotal results: {total}"

    if cmd == "/best":
        if total == 0:
            return "🔍 Agents are just getting started! Check back in 15 minutes."
        results = get_results(limit=20)
        top = sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:3]
        if not top or top[0].get("score", 0) == 0:
            return f"📝 {total} results collected but none scored yet. Check back soon!"
        lines = []
        for r in top:
            lines.append(f"🏆 {r['score']}/10 — {r['topic']}\n{r['content'][:200]}...")
        return "🔥 Top Discoveries\n\n" + "\n\n".join(lines)

    if cmd == "/topics":
        try:
            with open("research_topics.json") as f:
                topics = json.load(f).get("topics", [])
            if not topics:
                return "No topics loaded yet."
            topic_list = "\n".join([f"• {t}" for t in topics[:10]])
            return f"📋 Current Research Topics\n\n{topic_list}"
        except:
            return "Couldn't load topics right now."

    if cmd == "/summary":
        if total == 0:
            return "🚀 System is live! Nothing to summarize yet — give it 15-30 minutes."
        context, _ = get_research_context()
        answer = ask_gemini("Give me a quick summary of the most interesting things discovered so far.", context)
        return answer or get_quick_summary()

    return None


def handle_message(text: str) -> str:
    context, total = get_research_context()

    if total == 0:
        return "🤖 Agents just started! No research results yet. Give them 15-30 minutes! 🔍"

    answer = ask_gemini(text, context)
    if answer:
        return answer

    # Fallback when Gemini is rate limited — still useful!
    return get_quick_summary()


def process_update(update: dict):
    try:
        msg = update.get("message", {})
        chat_id = str(msg.get("chat", {}).get("id", ""))
        text = msg.get("text", "").strip()

        if not text or not chat_id:
            return

        if TELEGRAM_CHAT_ID and chat_id != TELEGRAM_CHAT_ID:
            return

        log("telegram_bot", f"Received: {text[:50]}")

        if text.startswith("/"):
            response = handle_command(text)
            if response:
                reply(response)
                return

        response = handle_message(text)
        reply(response)

    except Exception as e:
        log("telegram_bot", f"Error processing update: {e}")


def run_bot():
    if not TELEGRAM_TOKEN:
        log("telegram_bot", "No token found, bot disabled.")
        return

    log("telegram_bot", "💬 Telegram bot listening for messages...")

    while True:
        try:
            updates = get_updates()
            for update in updates:
                process_update(update)
            time.sleep(3)
        except Exception as e:
            log("telegram_bot", f"Bot loop error: {e}")
            time.sleep(10)


def start_bot_thread():
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()
    log("telegram_bot", "Bot thread started.")
