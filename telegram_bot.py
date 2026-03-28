"""
TELEGRAM BOT MANAGER - Advanced Version
- Add new research topics by messaging the bot
- Weekly digest every Sunday
- Proactive alerts when agents find something big
- Smart responses: short for simple, detailed for important
"""

import os
import time
import json
import threading
import requests
from datetime import datetime, date
from utils.logger import log
from utils.database import get_results, get_insights, get_total_results, get_agent_statuses
from utils.notifier import send_telegram

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
GEMINI_API_KEY = os.getenv("GEMINI_BOT_KEY") or os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
RESEARCH_TOPICS_FILE = "research_topics.json"

_last_update_id = 0
_answer_cache = {}
_cache_time = {}
_last_digest_date = ""
_last_alert_check = 0
_alerted_topics = set()
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


def get_research_context(limit: int = 20) -> tuple:
    total = get_total_results()
    results = get_results(limit=limit)
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


def ask_gemini(user_message: str, context: str, detailed: bool = False) -> str:
    if not GEMINI_API_KEY:
        return None

    cache_key = user_message.lower().strip()[:100]
    if cache_key in _answer_cache:
        age_minutes = (time.time() - _cache_time[cache_key]) / 60
        if age_minutes < CACHE_MINUTES:
            return _answer_cache[cache_key]

    max_tokens = 800 if detailed else 350

    prompt = f"""You are an advanced AI research assistant helping analyze market research findings.

RULES:
- For simple questions (status, counts): respond in 2-3 sentences max
- For important questions (what to build, best findings, opportunities): be detailed and specific
- Always extract concrete insights from the data
- Use emojis sparingly
- Never use markdown headers

CURRENT RESEARCH DATA:
{context}

USER ASKED: {user_message}

Respond appropriately — short if simple, detailed if important."""

    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7}
            },
            timeout=30
        )
        data = resp.json()
        if "candidates" in data:
            answer = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            _answer_cache[cache_key] = answer
            _cache_time[cache_key] = time.time()
            return answer
        log("telegram_bot", f"Gemini error: {data.get('error', {}).get('message', 'unknown')}")
        return None
    except Exception as e:
        log("telegram_bot", f"Gemini error: {e}")
        return None


def ask_groq(user_message: str, context: str, detailed: bool = False) -> str:
    if not GROQ_API_KEY:
        return None

    max_tokens = 800 if detailed else 350

    prompt = f"""You are an advanced AI research assistant. 
For simple questions respond in 2-3 sentences. For important questions be detailed and specific.
No markdown headers. Extract concrete insights from data.

RESEARCH DATA:
{context}

USER ASKED: {user_message}"""

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            },
            timeout=30
        )
        data = resp.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"].strip()
        return None
    except Exception as e:
        log("telegram_bot", f"Groq error: {e}")
        return None


def ask_ai(user_message: str, context: str, detailed: bool = False) -> str:
    answer = ask_gemini(user_message, context, detailed)
    if answer:
        return answer
    log("telegram_bot", "Gemini failed, trying Groq...")
    return ask_groq(user_message, context, detailed)


def get_quick_summary() -> str:
    total = get_total_results()
    if total == 0:
        return "🤖 Agents are running but no results yet. Check back in 15 minutes!"
    results = get_results(limit=20)
    top = sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:3]
    if not top or top[0].get("score", 0) == 0:
        topics = [r["topic"] for r in results[:2]]
        return f"📊 {total} results collected! Researching: {', '.join(topics)}. Try /best for details!"
    lines = [f"• {r['score']}/10 — {r['topic']}" for r in top]
    return f"📊 {total} results! Top findings:\n" + "\n".join(lines)


def add_research_topic(topic: str) -> str:
    """Add a new topic to research_topics.json."""
    try:
        if not os.path.exists(RESEARCH_TOPICS_FILE):
            data = {"topics": []}
        else:
            with open(RESEARCH_TOPICS_FILE, "r") as f:
                data = json.load(f)

        topics = data.get("topics", [])

        # Check if already exists
        if topic.lower() in [t.lower() for t in topics]:
            return f"📋 Already researching: {topic}"

        topics.append(topic)
        data["topics"] = topics

        with open(RESEARCH_TOPICS_FILE, "w") as f:
            json.dump(data, f, indent=2)

        log("telegram_bot", f"New topic added: {topic}")
        return f"✅ Added to research queue: {topic}\n\nAgents will start researching this in the next cycle (within 15 min)!"
    except Exception as e:
        log("telegram_bot", f"Error adding topic: {e}")
        return "❌ Couldn't add topic right now. Try again!"


def generate_weekly_digest() -> str:
    """Generate a detailed weekly digest of best findings."""
    total = get_total_results()
    if total == 0:
        return "📊 No research results yet for the weekly digest!"

    results = get_results(limit=50)
    top = sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:5]
    insights = get_insights(limit=3)

    context, _ = get_research_context(limit=50)
    digest_ai = ask_ai(
        "Generate a detailed weekly research digest. What are the top 3 market opportunities found? What should I focus on building? Be specific and actionable.",
        context,
        detailed=True
    )

    digest = f"📊 Weekly Research Digest\n"
    digest += f"Week of {date.today().strftime('%B %d, %Y')}\n"
    digest += f"Total results: {total}\n\n"

    if top and top[0].get("score", 0) > 0:
        digest += "🏆 Top Scored Findings:\n"
        for r in top[:3]:
            digest += f"• {r['score']}/10 — {r['topic']}\n"
        digest += "\n"

    if digest_ai:
        digest += f"🧠 AI Analysis:\n{digest_ai}"
    else:
        digest += "Keep researching — more insights coming soon!"

    return digest


def check_for_big_findings():
    """Proactively alert when multiple agents agree on something important."""
    global _last_alert_check, _alerted_topics

    # Only check every 30 minutes
    if time.time() - _last_alert_check < 1800:
        return

    _last_alert_check = time.time()

    try:
        results = get_results(limit=50)
        if not results:
            return

        # Find topics where multiple agents scored high
        topic_scores = {}
        for r in results:
            topic = r["topic"]
            score = r.get("score", 0)
            if score >= 7:
                if topic not in topic_scores:
                    topic_scores[topic] = []
                topic_scores[topic].append(score)

        # Alert if a topic has multiple high scores and hasn't been alerted
        for topic, scores in topic_scores.items():
            if len(scores) >= 2 and topic not in _alerted_topics:
                avg_score = sum(scores) / len(scores)
                _alerted_topics.add(topic)
                alert = (
                    f"🚨 Multiple agents agree on this!\n\n"
                    f"Topic: {topic}\n"
                    f"Agents scored it: {', '.join([str(s) for s in scores])}/10\n"
                    f"Average: {avg_score:.1f}/10\n\n"
                    f"This might be a real opportunity worth investigating! "
                    f"Ask me 'tell me everything about {topic}' for full details."
                )
                reply(alert)
                log("telegram_bot", f"Proactive alert sent for: {topic}")

    except Exception as e:
        log("telegram_bot", f"Alert check error: {e}")


def check_weekly_digest():
    """Send weekly digest every Sunday."""
    global _last_digest_date
    today = date.today()
    today_str = today.isoformat()

    if today.weekday() == 6 and _last_digest_date != today_str:
        _last_digest_date = today_str
        digest = generate_weekly_digest()
        reply(digest)
        log("telegram_bot", "Weekly digest sent")


def handle_command(text: str) -> str:
    context, total = get_research_context()
    cmd = text.strip().lower().split()[0]

    if cmd == "/start":
        return (
            "👋 Hey! I'm your advanced research assistant.\n\n"
            "Commands:\n"
            "• /status — agent status\n"
            "• /best — top discoveries\n"
            "• /topics — current research topics\n"
            "• /summary — quick overview\n"
            "• /digest — full weekly digest\n"
            "• /add [topic] — add new research topic\n\n"
            "Or just ask me anything:\n"
            "• 'any good app ideas?'\n"
            "• 'what should I build?'\n"
            "• 'tell me everything about note-taking apps'\n\n"
            "I'll alert you when agents find something big! 🔍"
        )

    if cmd == "/status":
        statuses = get_agent_statuses()
        if not statuses:
            return f"🤖 Agents running! {total} results so far."
        lines = []
        for name, info in statuses.items():
            status = "✅" if info.get("status") == "active" else "⏸"
            tasks = info.get("tasks_completed", 0)
            lines.append(f"{status} {name} — {tasks} tasks")
        return "📊 Agent Status\n\n" + "\n".join(lines) + f"\n\nTotal results: {total}"

    if cmd == "/best":
        if total == 0:
            return "🔍 No results yet — check back in 15 minutes!"
        results = get_results(limit=20)
        top = sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:3]
        if not top or top[0].get("score", 0) == 0:
            return f"📝 {total} results but none scored yet. Check back soon!"
        lines = []
        for r in top:
            lines.append(f"🏆 {r['score']}/10 — {r['topic']}\n{r['content'][:250]}...")
        return "🔥 Top Discoveries\n\n" + "\n\n".join(lines)

    if cmd == "/topics":
        try:
            with open(RESEARCH_TOPICS_FILE) as f:
                topics = json.load(f).get("topics", [])
            if not topics:
                return "No topics loaded yet."
            topic_list = "\n".join([f"• {t}" for t in topics])
            return f"📋 Research Topics ({len(topics)} total)\n\n{topic_list}\n\nAdd more with: /add your topic here"
        except:
            return "Couldn't load topics right now."

    if cmd == "/summary":
        if total == 0:
            return "🚀 System live! Give it 15-30 minutes for first results."
        answer = ask_ai("Give me a quick 3-sentence summary of the most interesting findings so far.", context, detailed=False)
        return answer or get_quick_summary()

    if cmd == "/digest":
        return generate_weekly_digest()

    if cmd == "/add":
        topic = text[4:].strip()
        if not topic:
            return "Tell me what to research! Example:\n/add AI tools for lawyers 2026"
        return add_research_topic(topic)

    return None


def handle_message(text: str) -> str:
    context, total = get_research_context()

    if total == 0:
        return "🤖 Agents just started! Give them 15-30 minutes and ask me again! 🔍"

    # Detect if user wants to add a topic
    lower = text.lower()
    if any(phrase in lower for phrase in ["research", "look into", "find out about", "add topic", "investigate"]):
        # Extract potential topic
        for phrase in ["research ", "look into ", "find out about ", "investigate "]:
            if phrase in lower:
                potential_topic = text[lower.index(phrase) + len(phrase):].strip()
                if len(potential_topic) > 5:
                    confirm = add_research_topic(potential_topic)
                    return confirm

    # Detect if important question needing detailed response
    important_keywords = ["what should i build", "best opportunity", "what to build",
                         "most promising", "tell me everything", "full analysis",
                         "best findings", "top insights", "recommend"]
    is_important = any(kw in lower for kw in important_keywords)

    answer = ask_ai(text, context, detailed=is_important)
    if answer:
        return answer

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

    log("telegram_bot", "💬 Advanced Telegram bot listening...")

    while True:
        try:
            updates = get_updates()
            for update in updates:
                process_update(update)

            # Background checks
            check_for_big_findings()
            check_weekly_digest()

            time.sleep(3)
        except Exception as e:
            log("telegram_bot", f"Bot loop error: {e}")
            time.sleep(10)


def start_bot_thread():
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()
    log("telegram_bot", "Advanced bot thread started.")
