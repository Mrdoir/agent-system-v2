# 🤖 AI Research Agent System

4 agents working nonstop to research business & market opportunities.
Auto-pauses when rate limits hit, auto-resumes when they reset.

---

## Agents

| Agent | AI Used | Job |
|-------|---------|-----|
| **Manager** | Logic only | Orchestrates everything, tracks limits, queues tasks |
| **Market Scout** | Gemini Flash (free) | Competitors, user complaints, market gaps |
| **Trend Analyst** | Groq Llama 4 (free) | Trends, timing, who's driving demand |
| **Deep Diver** | DeepSeek R1 (free) | Deep strategy, why things fail, how to win |

---

## Setup (5 minutes)

### Step 1 — Install dependencies
Open a terminal in this folder and run:
```
pip install -r requirements.txt
```

### Step 2 — Get your free API keys

| Service | Link | Time |
|---------|------|------|
| Google Gemini | https://aistudio.google.com/app/apikey | 1 min |
| Groq | https://console.groq.com/keys | 1 min |
| OpenRouter | https://openrouter.ai/settings/keys | 2 min |

No credit card needed for any of these.

### Step 3 — Set up your keys
1. Rename `.env.example` to `.env`
2. Open `.env` and paste your keys

### Step 4 — Customize research topics (optional)
Edit `research_topics.json` to add your own topics.
The file is auto-created on first run with default topics.

### Step 5 — Run the system
```
python manager.py
```

That's it. The system runs forever. Results saved to `/results/` folder.

---

## How It Works

```
Manager wakes up every 15 minutes
    ↓
Checks which agents are available (not rate limited)
    ↓
Assigns pending research tasks to available agents
    ↓
Agents call their AI APIs and save results to /results/
    ↓
If an agent hits a rate limit → marked as limited for 60 min
    ↓
After 60 min → agent auto-clears, back to work
    ↓
Repeat forever
```

---

## Output

Results are saved as markdown files in `/results/`:
```
results/
  market_scout_productivity_apps_20250325_1430.md
  trend_analyst_productivity_apps_20250325_1431.md
  deep_diver_productivity_apps_20250325_1435.md
```

---

## Add Your Own Topics

Edit `research_topics.json`:
```json
{
  "topics": [
    "your topic here",
    "another topic",
    "freelancer invoicing app gaps"
  ]
}
```

The manager will pick up new topics automatically on the next cycle.

---

## Stop / Resume

- **Stop:** Press `Ctrl+C`
- **Resume:** Run `python manager.py` again — it remembers where it left off
- All state is saved in `/state/` folder
