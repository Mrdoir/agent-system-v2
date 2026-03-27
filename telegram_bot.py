"""
TELEGRAM BOT MANAGER
Listens for your messages and answers questions about research progress.
Runs as a background thread alongside the main manager.

Commands you can send:
  /status   — how are the agents doing?
  /best     — top discoveries so far
  /summary  — quick overview of everything
  /topics   — what are agents researching?
  anything  — just ask naturally, AI will answer
"""

import os
import time
import json
import threading
import requests
from datetime import datetime
from utils.logger import log
from utils.database import get_results, get_insights, get_total_results, get_agent_statuses
from utils.notifier import send_telegram

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

_last_update_id = 0


def get_updates():
    """Poll Telegram for new messages."""
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
    """Send a reply message."""
    send_telegram(text)


def get_research_context():
    """Build a short context summary from the database."""
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


def ask_ai(user_message: str, context: str) -> str:
    """Ask AI to generate a short, friendly response — tries multiple models."""
    if not OPENROUTER_API_KEY:
        log("telegram_bot", "No OpenRouter key found!")
        return None

    models = [
        "mistralai/mistral-7b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.2-3b-instruct:free",
    ]

    system = """You are a friendly AI research assistant. You help the user understand what their AI research agents have discovered.
Keep responses SHORT (max 4-5 sentences). Be direct and highlight the most interesting findings.
Use simple language. Always try to answer the specific question asked using the research data provided.
If asked about app ideas, look through the research content and pull out any app ideas mentioned.
If asked about trends, summarize the trend findings.
Never say you don't have data if there is research content available — always try to extract something useful.
Never use markdown headers. Just plain conversational text with occasional emojis."""

    prompt = f"""The user is asking about their AI research agent system.

CURRENT RESEARCH DATA:
{context}

USER ASKED: {user_message}

Look through ALL the research data above and give a short, specific, helpful answer.
Pull out the most relevant findings that answer their question directly."""

    for model in models:
        try:
            log("telegram_bot", f"Trying model: {model}")
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/Mrdoir/agent-system",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 400
                },
                timeout=60
            )
            data = resp.json()
            if "choices" in data:
                return data["choices"][0]["message"]["content"].strip()
            else:
                log("telegram_bot", f"Model {model} failed: {data.get('error', data)}")
        except Exception as e:
            log("telegram_bot", f"Model {model} error: {e}")

    return None


def handle_command(text: str) -> str:
    """Handle slash commands with instant responses."""
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
            return f"🤖 Agents are running! {total} results collected so far. No detailed status yet — check back in a few minutes."
        lines = []
        for name, info in statuses.items():
            status = "✅ Active" if info.get("status") == "active" else "⏸ Limited"
            tasks = info.get("tasks_completed", 0)
            lines.append(f"{status} {name} — {tasks} tasks done")
        return "📊 Agent Status\n\n" + "\n".join(lines) + f"\n\nTotal results: {total}"

    if cmd == "/best":
        if total == 0:
            return "🔍 Agents are just getting started! No results yet — check back in 15 minutes."
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
            return "🚀 System is live! Nothing to summarize yet — give it 15-30 minutes for first results."
        context, _ = get_research_context()
        answer = ask_ai("Give me a quick summary of the most interesting things discovered so far.", context)
        return answer or f"📊 {total} results collected. Try /best for top findings!"

    return None


def handle_message(text: str) -> str:
    """Handle any free-form message."""
    context, total = get_research_context()

    if total == 0:
        return "🤖 Agents just started! No research results yet. Give them 15-30 minutes and ask me again! 🔍"

    answer = ask_ai(text, context)
    if answer:
        return answer

    return f"📊 Got {total} research results so far. Try /best to see top findings or /status to check the agents!"


def process_update(update: dict):
    """Process a single Telegram update."""
    try:
        msg = update.get("message", {})
        chat_id = str(msg.get("chat", {}).get("id", ""))
        text = msg.get("text", "").strip()

        if not text or not chat_id:
            return

        if TELEGRAM_CHAT_ID and chat_id != TELEGRAM_CHAT_ID:
            log("telegram_bot", f"Ignored message from unknown chat: {chat_id}")
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
    """Main polling loop — runs forever in background thread."""
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
    """Start the bot as a background daemon thread."""
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()
    log("telegram_bot", "Bot thread started.")
