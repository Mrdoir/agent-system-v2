# 🤖 AI Research Agent System v4

**6 AI agents working 24/7 to research market opportunities.** Auto-pauses on rate limits, auto-resumes when they reset. Completely free to run.

---

## ✨ What's New in v4

### 🔄 More Free AI Providers
- **Together AI** - Added as fallback (free tier)
- **Cohere** - Added as fallback (5 req/min free)
- Each agent now has 4-6 fallback providers

### 📊 Analytics & Search
- Full-text search across all research
- Agent performance tracking
- Topic saturation detection
- Score trends over time

### 🔔 Multi-Platform Notifications
- **Telegram** - Instant alerts
- **Discord** - Webhook support
- **Slack** - Webhook support

### 🧠 Smarter Research
- Topic saturation detection (stops over-researching)
- Follow-up topic generation from high-scoring research
- Trending topics from Hacker News
- Critic feedback loop for agent improvement

### 🔍 Better Web Search
- Hacker News search (tech trends)
- GitHub Issues search (developer pain points)
- Improved Reddit parsing
- Result caching to reduce API calls

---

## 🤖 Agents

| Agent | Job | Primary AI | Fallbacks |
|-------|-----|------------|-----------|
| **Market Scout** | Competitors, complaints, gaps | Gemini Flash | Groq, Together, Cerebras, Cohere |
| **Trend Analyst** | Trends, timing, demand | Groq Llama | Cerebras, Together, Gemini |
| **Deep Diver** | Strategy, why things fail | Nemotron | QwQ, Cerebras, Together, Gemini |
| **Critic** | Scores & feedback | DeepSeek R1 | Qwen3, Llama, Groq, Cerebras |
| **Memory** | Synthesizes knowledge | Gemini Flash | — |
| **Synthesis** | Weekly reports | Groq Llama | Together |

---

## 🚀 Setup (5 minutes)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Get your free API keys

| Service | Link | Time |
|---------|------|------|
| Google Gemini | https://aistudio.google.com/app/apikey | 1 min |
| Groq | https://console.groq.com/keys | 1 min |
| OpenRouter | https://openrouter.ai/settings/keys | 2 min |
| Together AI | https://api.together.xyz/settings/api-keys | 1 min |
| Cerebras | https://cloud.cerebras.ai/ | 2 min |
| Cohere | https://dashboard.cohere.com/api-keys | 1 min |

**No credit card needed for any of these.**

### 3. Set up environment
```bash
cp .env.example .env
# Edit .env and add your keys
```

### 4. Set up PostgreSQL

**Free options:**
- [Render PostgreSQL](https://render.com) - 90 day free
- [Supabase](https://supabase.com) - Free tier
- [Neon](https://neon.tech) - Free tier

Add the `DATABASE_URL` to your `.env` file.

### 5. Run the system
```bash
python manager.py
```

That's it! The system runs forever. Results saved to PostgreSQL.

---

## 📊 Dashboard

Run the dashboard:
```bash
python dashboard.py
```

Access at `http://localhost:5000`

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/results` | Research results (filter by agent, min_score) |
| `GET /api/insights` | Synthesized insights |
| `GET /api/stats` | System statistics |
| `GET /api/search?q=` | Full-text search |
| `GET /api/analytics/summary` | Analytics overview |
| `GET /api/analytics/scores` | Score trends |
| `GET /api/analytics/topics` | Topic stats |
| `GET /api/analytics/agents` | Agent performance |
| `GET /api/feedback/<agent>` | Critic feedback |
| `GET /api/export` | Download all data |

---

## 🔔 Notifications Setup

### Telegram
1. Message [@BotFather](https://t.me/BotFather) → `/newbot`
2. Message [@userinfobot](https://t.me/userinfobot) for your chat ID
3. Add to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

### Discord
1. Server Settings → Integrations → Webhooks → New
2. Copy URL and add to `.env`:
   ```
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   ```

### Slack
1. Create an [Incoming Webhook](https://api.slack.com/messaging/webhooks)
2. Add to `.env`:
   ```
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   ```

---

## ⚙️ Configuration

In `.env`:

```bash
# Research cycle interval (default: 15 minutes)
CYCLE_INTERVAL_MINUTES=15

# Max results per topic before saturation (default: 5)
MAX_RESULTS_PER_TOPIC=5

# Minimum score to send notifications (default: 7)
MIN_SCORE_TO_NOTIFY=7
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      MANAGER                            │
│            (Orchestrates every 15 min)                  │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ┌─────────┐   ┌──────────┐   ┌──────────┐
   │  Scout  │   │ Analyst  │   │  Diver   │
   │(Gemini) │   │ (Groq)   │   │(Nemotron)│
   └────┬────┘   └────┬─────┘   └────┬─────┘
        │             │              │
        └──────────┬──┴──────────────┘
                   │
                   ▼
            ┌────────────┐
            │   CRITIC   │
            │(DeepSeek)  │
            └─────┬──────┘
                  │
         ┌────────┴────────┐
         ▼                 ▼
   ┌──────────┐     ┌───────────┐
   │  MEMORY  │     │ SYNTHESIS │
   │ (Gemini) │     │  (Groq)   │
   └────┬─────┘     └───────────┘
        │
        ▼
   Feeds back into
   next research cycle
```

---

## 📁 File Structure

```
improved_repo/
├── manager.py           # Main orchestrator
├── dashboard.py         # Flask API & web UI
├── requirements.txt     # Dependencies
├── .env.example         # Environment template
├── agents/
│   ├── base_agent.py    # Base class with retry logic
│   ├── market_scout.py  # Market research agent
│   ├── trend_analyst.py # Trend detection agent
│   ├── deep_diver.py    # Strategic analysis agent
│   ├── critic.py        # Quality scoring agent
│   ├── memory_agent.py  # Knowledge synthesis agent
│   └── synthesis_agent.py # Weekly report agent
└── utils/
    ├── database.py      # PostgreSQL operations
    ├── logger.py        # Colored logging
    ├── notifier.py      # Multi-platform notifications
    ├── web_search.py    # Multi-source search
    ├── memory_context.py # Context building for agents
    └── topic_rotator.py # Smart topic selection
```

---

## 🛠️ Deploy to Render (Free)

### Option A: Single Web Service (recommended — runs both)

1. Push to GitHub
2. Create new **Web Service** on Render
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python run.py`
5. Add environment variables from `.env`

This runs both the dashboard (Flask on port) AND the agent manager in one process.

### Option B: Two separate services

**Web Service** (dashboard):
- Start Command: `python dashboard.py`

**Background Worker** (agents):
- Start Command: `python manager.py`

---

## 📝 License

MIT - Do whatever you want with it.

---

## 🤝 Contributing

PRs welcome! Key areas for improvement:
- More free AI providers
- Better web scraping
- ML-based topic generation
- Research quality classification
