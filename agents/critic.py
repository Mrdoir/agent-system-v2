"""
AGENT 4: CRITIC - The Deep Thinker
Primary:   DeepSeek R1 + Qwen3-235B + Llama via OpenRouter (loops all 3)
Fallback1: Groq (Llama 3.3 70B)
Fallback2: Cerebras (Llama 3.3 70B — separate quota)
Order: OpenRouter models → Groq → Cerebras
"""

import os
import requests
from agents.base_agent import BaseAgent
from utils.logger import log
from utils.database import save_result, get_do_not_repeat, save_critic_feedback


class CriticAgent(BaseAgent):
    NAME = "critic"
    PROVIDER = "DeepSeek R1 (reasoning) via OpenRouter + Groq + Cerebras"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.api_key_2 = os.getenv("OPENROUTER_API_KEY_2", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.groq_key_2 = os.getenv("GROQ_API_KEY_2", "")
        self.cerebras_key = os.getenv("CEREBRAS_API_KEY", "")

        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"
        self.groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.cerebras_endpoint = "https://api.cerebras.ai/v1/chat/completions"

        self.reasoning_models = [
            "deepseek/deepseek-r1:free",
            "qwen/qwen3-235b-a22b:free",
            "meta-llama/llama-3.3-70b-instruct:free",
        ]

    def build_eval_prompt(self, topic: str, research_content: str) -> str:
        do_not_repeat = get_do_not_repeat()
        dnr_list = "\n".join(f"- {p}" for p in do_not_repeat[:20]) if do_not_repeat else "None yet"

        return f"""You are an elite research critic with deep reasoning capabilities.
Your job is to evaluate multi-agent research and extract specific, actionable feedback for each agent.

TOPIC BEING RESEARCHED: {topic}

COMBINED RESEARCH FROM ALL AGENTS:
{research_content}

OVERUSED PATTERNS TO PENALIZE:
{dnr_list}

Think deeply and carefully before scoring. Consider:
- Is this research actually specific or just generic AI knowledge?
- Does it use real web data or just hallucinate facts?
- Are the insights actionable or vague?
- What's genuinely new vs what everyone already knows?

Respond in this EXACT format:

## OVERALL QUALITY SCORE: [0-10]
[2-3 sentences explaining the score honestly]

## MARKET SCOUT FEEDBACK
Score: [0-10]
Strength: [what Scout did well — be specific]
Weakness: [what Scout missed or did poorly — be specific]
Improvement: [exact instruction for Scout to improve next time]

## TREND ANALYST FEEDBACK
Score: [0-10]
Strength: [what Analyst did well — be specific]
Weakness: [what Analyst missed or did poorly — be specific]
Improvement: [exact instruction for Analyst to improve next time]

## DEEP DIVER FEEDBACK
Score: [0-10]
Strength: [what Diver did well — be specific]
Weakness: [what Diver missed or did poorly — be specific]
Improvement: [exact instruction for Diver to improve next time]

## STRONG INSIGHTS (keep these)
[List only genuinely specific, actionable, non-obvious findings]

## WEAK INSIGHTS (cut these)
[List generic, vague, or obvious statements]

## TOP 3 ACTIONABLE TAKEAWAYS
[The 3 most useful, specific things someone could act on]

## PATTERNS TO ADD TO DO-NOT-REPEAT LIST
[2-3 generic phrases from this output that should never appear again]

## VERDICT
[1 sentence: Is this research useful? What's the single most important finding?]

Be ruthless. Generic = worthless. Specific = valuable."""

    def call_openrouter(self, prompt: str) -> dict:
        keys = [k for k in [self.api_key, self.api_key_2] if k]
        if not keys:
            return {"success": False, "error": "No OpenRouter keys"}

        for api_key in keys:
            for model in self.reasoning_models:
                try:
                    log("critic", f"Trying reasoning model: {model}")
                    resp = requests.post(
                        self.endpoint,
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://agent-system.local",
                            "X-Title": "Research Critic"
                        },
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": "You are an elite research critic. Think deeply and carefully before scoring. Be specific, honest, and ruthless about quality."},
                                {"role": "user", "content": prompt}
                            ],
                            "max_tokens": 2000,
                            "temperature": 0.2
                        },
                        timeout=90
                    )
                    if resp.status_code == 429:
                        log("critic", f"{model} rate limited, trying next...")
                        continue
                    if resp.status_code != 200:
                        log("critic", f"{model} failed: HTTP {resp.status_code}")
                        continue
                    data = resp.json()
                    if "choices" not in data:
                        log("critic", f"{model} bad response")
                        continue
                    text = data["choices"][0]["message"]["content"]
                    log("critic", f"✓ Success with: {model}")
                    return {"success": True, "text": text}
                except Exception as e:
                    log("critic", f"{model} error: {e}")
                    continue

        return {"success": False, "rate_limited": True}

    def _call_openai_compat(self, prompt: str, endpoint: str, api_key: str, model: str, provider_name: str) -> dict:
        """Generic caller for OpenAI-compatible endpoints (Groq, Cerebras, etc.)"""
        if not api_key:
            return {"success": False, "error": f"No {provider_name} key"}
        try:
            log("critic", f"Trying {provider_name} fallback...")
            resp = requests.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are an elite research critic. Be specific, honest, and ruthless about quality."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.2
                },
                timeout=60
            )
            if resp.status_code == 429:
                return {"success": False, "rate_limited": True}
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}"}
            text = resp.json()["choices"][0]["message"]["content"]
            log("critic", f"✓ {provider_name} fallback succeeded")
            return {"success": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_score(self, text: str, label: str = "OVERALL QUALITY SCORE") -> int:
        for line in text.split("\n"):
            if label in line:
                try:
                    score = int(''.join(filter(str.isdigit, line.split(":")[-1][:3])))
                    return min(10, max(0, score))
                except:
                    pass
        return 5

    def extract_section(self, text: str, section: str) -> str:
        lines = text.split("\n")
        capturing = False
        result = []
        for line in lines:
            if section in line:
                capturing = True
                continue
            if capturing:
                if line.startswith("##"):
                    break
                if line.strip():
                    result.append(line.strip())
        return " ".join(result[:3])

    def extract_agent_feedback(self, text: str, agent_label: str) -> dict:
        lines = text.split("\n")
        in_section = False
        score = 5
        strength = ""
        weakness = ""
        improvement = ""

        for line in lines:
            if agent_label in line and "##" in line:
                in_section = True
                continue
            if in_section:
                if line.startswith("##") and agent_label not in line:
                    break
                if "Score:" in line:
                    try:
                        score = int(''.join(filter(str.isdigit, line.split(":")[-1][:3])))
                        score = min(10, max(0, score))
                    except:
                        pass
                elif "Strength:" in line:
                    strength = line.split(":", 1)[-1].strip()
                elif "Weakness:" in line:
                    weakness = line.split(":", 1)[-1].strip()
                elif "Improvement:" in line:
                    improvement = line.split(":", 1)[-1].strip()

        return {"score": score, "strength": strength, "weakness": weakness, "improvement": improvement}

    def evaluate(self, topic: str, research_content: str) -> dict:
        if self.is_rate_limited():
            return {"success": False, "rate_limited": True}

        prompt = self.build_eval_prompt(topic, research_content)

        # 1. Try OpenRouter reasoning models
        result = self.call_openrouter(prompt)

        # 2. Groq fallback
        if not result["success"]:
            result = self._call_openai_compat(
                prompt, self.groq_endpoint, self.groq_key,
                "llama-3.3-70b-versatile", "groq"
            )

        # 3. Groq key 2 fallback
        if not result["success"]:
            result = self._call_openai_compat(
                prompt, self.groq_endpoint, self.groq_key_2,
                "llama-3.3-70b-versatile", "groq-key2"
            )

        # 4. Cerebras final fallback
        if not result["success"]:
            result = self._call_openai_compat(
                prompt, self.cerebras_endpoint, self.cerebras_key,
                "llama-3.3-70b", "cerebras"
            )

        if not result["success"]:
            log("critic", "⚠️ All providers exhausted (OpenRouter, Groq, Cerebras)")
            return {"success": False, "error": "All critic providers failed"}

        text = result["text"]
        overall_score = self.extract_score(text, "OVERALL QUALITY SCORE")

        agent_map = {
            "market_scout": "MARKET SCOUT FEEDBACK",
            "trend_analyst": "TREND ANALYST FEEDBACK",
            "deep_diver": "DEEP DIVER FEEDBACK"
        }

        for agent_name, label in agent_map.items():
            feedback = self.extract_agent_feedback(text, label)
            if feedback["strength"] or feedback["weakness"]:
                save_critic_feedback(
                    agent=agent_name,
                    topic=topic,
                    score=feedback["score"],
                    strength=feedback["strength"],
                    weakness=feedback["weakness"],
                    improvement=feedback["improvement"]
                )
                log("critic", f"Saved feedback for {agent_name}: {feedback['score']}/10")

        return {"success": True, "text": text, "score": overall_score}

    def research(self, topic: str) -> dict:
        return {"success": False, "error": "Use evaluate() instead"}

    def call_api(self, prompt: str) -> dict:
        return {"success": False, "error": "Use evaluate() instead"}
