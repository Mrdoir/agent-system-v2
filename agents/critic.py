"""
CRITIC v3 — Quality evaluator with better feedback extraction
Improvements:
- More robust score/feedback parsing
- Per-agent feedback storage
- Pattern detection for do-not-repeat
- Quality metrics tracking
"""

import os
import re
from agents.base_agent import BaseAgent, OpenAICompatibleMixin
from utils.logger import log_info, log_warn, log_debug, log_api_call
from utils.database import (
    get_do_not_repeat, save_critic_feedback, add_do_not_repeat,
    update_agent_status
)


class CriticAgent(BaseAgent, OpenAICompatibleMixin):
    NAME = "critic"
    PROVIDER = "DeepSeek R1 + Qwen3 + Llama (OpenRouter) + Groq + Cerebras"
    
    def __init__(self):
        super().__init__()
        
        # API Keys
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_key_2 = os.getenv("OPENROUTER_API_KEY_2", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.groq_key_2 = os.getenv("GROQ_API_KEY_2", "")
        self.cerebras_key = os.getenv("CEREBRAS_API_KEY", "")
        
        # Endpoints
        self.openrouter_endpoint = "https://openrouter.ai/api/v1/chat/completions"
        self.groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.cerebras_endpoint = "https://api.cerebras.ai/v1/chat/completions"
        
        # Reasoning models (prioritize deep thinking)
        self.reasoning_models = [
            "deepseek/deepseek-r1:free",
            "qwen/qwen3-235b-a22b:free",
            "meta-llama/llama-3.3-70b-instruct:free",
        ]
        
        self.groq_model = "llama-3.3-70b-versatile"
        self.cerebras_model = "llama-3.3-70b"
    
    def build_eval_prompt(self, topic: str, research_content: str) -> str:
        """Build evaluation prompt for critic."""
        
        do_not_repeat = get_do_not_repeat()
        dnr_list = "\n".join(f"- {p}" for p in do_not_repeat[:25]) if do_not_repeat else "None yet"
        
        return f"""You are an ELITE RESEARCH CRITIC with deep reasoning capabilities.
Your job is to evaluate research quality and provide specific, actionable feedback.

═══════════════════════════════════════════════════════════════════
TOPIC BEING RESEARCHED: {topic}
═══════════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════════
RESEARCH CONTENT TO EVALUATE:
═══════════════════════════════════════════════════════════════════
{research_content[:5000]}

═══════════════════════════════════════════════════════════════════
PATTERNS THAT INDICATE LOW QUALITY (penalize if found):
═══════════════════════════════════════════════════════════════════
{dnr_list}

═══════════════════════════════════════════════════════════════════
YOUR EVALUATION TASK
═══════════════════════════════════════════════════════════════════

Think carefully and evaluate. Respond in this EXACT format:

## OVERALL QUALITY SCORE: [X]/10
[2-3 sentences explaining the score with specific examples]

## MARKET SCOUT FEEDBACK
Score: [X]/10
Strength: [What Scout did well — be specific, quote if possible]
Weakness: [What Scout missed or did poorly — be specific]
Improvement: [Exact instruction for Scout to improve next time]

## TREND ANALYST FEEDBACK
Score: [X]/10
Strength: [What Analyst did well — be specific]
Weakness: [What Analyst missed — be specific]
Improvement: [Exact instruction for Analyst to improve]

## DEEP DIVER FEEDBACK
Score: [X]/10
Strength: [What Diver did well — be specific]
Weakness: [What Diver missed — be specific]
Improvement: [Exact instruction for Diver to improve]

## STRONG INSIGHTS (keep these)
[List only genuinely specific, actionable, non-obvious findings]
[Include why each is valuable]

## WEAK INSIGHTS (cut these)
[List generic, vague, or obvious statements that add no value]

## TOP 3 ACTIONABLE TAKEAWAYS
[The 3 most useful, specific things someone could act on TODAY]
1. 
2. 
3. 

## PATTERNS TO BLACKLIST
[2-3 generic phrases from this output that should never appear again]
- 
- 
- 

## FINAL VERDICT
[1 sentence: Is this research worth reading? What's the single most important finding?]

═══════════════════════════════════════════════════════════════════
SCORING GUIDE:
- 9-10: Exceptional — specific, actionable, novel with hard evidence
- 7-8: Good — mostly specific, some actionable insights  
- 5-6: Average — mix of specific and generic
- 3-4: Below Average — mostly generic statements
- 1-2: Poor — no specific insights, all generic

Be ruthless. Generic = worthless. Specific = valuable.
═══════════════════════════════════════════════════════════════════
"""
    
    def _call_openrouter_reasoning(self, prompt: str) -> dict:
        """Call OpenRouter with reasoning models."""
        import requests
        
        keys = [k for k in [self.openrouter_key, self.openrouter_key_2] if k]
        if not keys:
            return {"success": False, "error": "No OpenRouter keys"}
        
        for api_key in keys:
            for model in self.reasoning_models:
                try:
                    log_debug(self.NAME, f"Trying {model}...")
                    
                    resp = requests.post(
                        self.openrouter_endpoint,
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://agent-research-hub.local",
                            "X-Title": "Research Critic"
                        },
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": "Elite research critic. Think deeply. Be specific and ruthless about quality."},
                                {"role": "user", "content": prompt}
                            ],
                            "max_tokens": 2500,
                            "temperature": 0.2
                        },
                        timeout=90
                    )
                    
                    if resp.status_code == 429:
                        log_debug(self.NAME, f"{model} rate limited")
                        continue
                    
                    if resp.status_code != 200:
                        log_debug(self.NAME, f"{model} failed: HTTP {resp.status_code}")
                        continue
                    
                    data = resp.json()
                    if "choices" not in data:
                        continue
                    
                    text = data["choices"][0]["message"]["content"]
                    log_api_call(self.NAME, model.split("/")[-1], True)
                    return {"success": True, "text": text, "provider": model}
                    
                except Exception as e:
                    log_debug(self.NAME, f"{model} error: {e}")
                    continue
        
        return {"success": False, "rate_limited": True}
    
    def call_api(self, prompt: str) -> dict:
        """Call AI API for evaluation."""
        
        system_msg = "Elite research critic. Think deeply. Be specific and ruthless about quality."
        
        # 1. Try OpenRouter reasoning models
        result = self._call_openrouter_reasoning(prompt)
        if result.get("success"):
            return result
        log_api_call(self.NAME, "OpenRouter", False)
        
        # 2. Try Groq
        if self.groq_key:
            log_debug(self.NAME, "Trying Groq...")
            result = self._call_openai_compatible(
                prompt, self.groq_endpoint, self.groq_key,
                self.groq_model, "groq", system_msg, max_tokens=2500, temperature=0.2
            )
            if result["success"]:
                log_api_call(self.NAME, "Groq", True)
                return result
        
        # 3. Try Groq key 2
        if self.groq_key_2:
            result = self._call_openai_compatible(
                prompt, self.groq_endpoint, self.groq_key_2,
                self.groq_model, "groq-2", system_msg, max_tokens=2500, temperature=0.2
            )
            if result["success"]:
                log_api_call(self.NAME, "Groq-2", True)
                return result
        
        # 4. Try Cerebras
        if self.cerebras_key:
            log_debug(self.NAME, "Trying Cerebras...")
            result = self._call_openai_compatible(
                prompt, self.cerebras_endpoint, self.cerebras_key,
                self.cerebras_model, "cerebras", system_msg, max_tokens=2500, temperature=0.2
            )
            if result["success"]:
                log_api_call(self.NAME, "Cerebras", True)
                return result
        
        log_warn(self.NAME, "All providers exhausted")
        return {"success": False, "rate_limited": True, "error": "All providers failed"}
    
    # ═══════════════════════════════════════════════════════════════
    # FEEDBACK EXTRACTION
    # ═══════════════════════════════════════════════════════════════
    
    def extract_score(self, text: str, label: str = "OVERALL QUALITY SCORE") -> int:
        """Extract score from evaluation text."""
        for line in text.split("\n"):
            if label.upper() in line.upper():
                # Find digits in the line
                numbers = re.findall(r'\d+', line)
                if numbers:
                    score = int(numbers[0])
                    return min(10, max(0, score))
        return 5  # Default
    
    def extract_agent_feedback(self, text: str, agent_keyword: str) -> dict:
        """Extract feedback for a specific agent."""
        feedback = {"score": 5, "strength": "", "weakness": "", "improvement": ""}
        
        lines = text.split("\n")
        in_section = False
        
        for i, line in enumerate(lines):
            # Find the agent section
            if agent_keyword.upper() in line.upper() and "FEEDBACK" in line.upper():
                in_section = True
                continue
            
            if in_section:
                # Check if we've moved to next section
                if line.strip().startswith("##"):
                    break
                
                line_lower = line.lower()
                
                if "score:" in line_lower:
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        feedback["score"] = min(10, max(0, int(numbers[0])))
                
                elif "strength:" in line_lower:
                    feedback["strength"] = line.split(":", 1)[-1].strip()[:500]
                
                elif "weakness:" in line_lower:
                    feedback["weakness"] = line.split(":", 1)[-1].strip()[:500]
                
                elif "improvement:" in line_lower:
                    feedback["improvement"] = line.split(":", 1)[-1].strip()[:500]
        
        return feedback
    
    def extract_blacklist_patterns(self, text: str) -> list:
        """Extract patterns to add to do-not-repeat list."""
        patterns = []
        in_section = False
        
        for line in text.split("\n"):
            if "PATTERNS TO BLACKLIST" in line.upper():
                in_section = True
                continue
            
            if in_section:
                if line.strip().startswith("##"):
                    break
                
                if line.strip().startswith("-"):
                    pattern = line.strip("- ").strip()
                    if len(pattern) > 10 and len(pattern) < 100:
                        patterns.append(pattern)
        
        return patterns[:5]  # Max 5 patterns per evaluation
    
    def extract_takeaways(self, text: str) -> list:
        """Extract top actionable takeaways."""
        takeaways = []
        in_section = False
        
        for line in text.split("\n"):
            if "ACTIONABLE TAKEAWAY" in line.upper():
                in_section = True
                continue
            
            if in_section:
                if line.strip().startswith("##"):
                    break
                
                # Match numbered items
                match = re.match(r'^\d+[\.\)]\s*(.+)', line.strip())
                if match:
                    takeaways.append(match.group(1).strip())
        
        return takeaways[:3]
    
    # ═══════════════════════════════════════════════════════════════
    # MAIN EVALUATION
    # ═══════════════════════════════════════════════════════════════
    
    def evaluate(self, topic: str, research_content: str) -> dict:
        """
        Evaluate research and provide feedback.
        Returns: {"success": bool, "score": int, "feedback": str, "takeaways": list}
        """
        if self.is_rate_limited():
            return {"success": False, "error": "Rate limited", "rate_limited": True}
        
        # Build and call
        prompt = self.build_eval_prompt(topic, research_content)
        result = self.call_api(prompt)
        
        if result.get("rate_limited"):
            self.set_rate_limited(provider=result.get("provider"))
            return {"success": False, "rate_limited": True}
        
        if not result.get("success"):
            return {"success": False, "error": result.get("error")}
        
        eval_text = result["text"]
        
        # Extract overall score
        overall_score = self.extract_score(eval_text)
        
        # Extract and save per-agent feedback
        for agent_name, keyword in [
            ("market_scout", "MARKET SCOUT"),
            ("trend_analyst", "TREND ANALYST"),
            ("deep_diver", "DEEP DIVER"),
        ]:
            feedback = self.extract_agent_feedback(eval_text, keyword)
            if feedback["score"] > 0 or feedback["strength"] or feedback["weakness"]:
                save_critic_feedback(
                    agent=agent_name,
                    topic=topic,
                    score=feedback["score"],
                    strength=feedback["strength"],
                    weakness=feedback["weakness"],
                    improvement=feedback["improvement"]
                )
                log_debug(self.NAME, f"Saved feedback for {agent_name}: {feedback['score']}/10")
        
        # Extract and save blacklist patterns
        patterns = self.extract_blacklist_patterns(eval_text)
        for pattern in patterns:
            add_do_not_repeat(pattern)
            log_debug(self.NAME, f"Added blacklist pattern: {pattern[:50]}")
        
        # Extract takeaways
        takeaways = self.extract_takeaways(eval_text)
        
        # Save critic's own result
        self.save_to_db(topic, eval_text, score=overall_score)
        
        log_info(self.NAME, f"Evaluated research: {overall_score}/10")
        
        return {
            "success": True,
            "score": overall_score,
            "feedback": eval_text,
            "takeaways": takeaways,
            "provider": result.get("provider")
        }
    
    def research(self, topic: str) -> dict:
        """Critic doesn't do research, use evaluate() instead."""
        return {"success": False, "error": "Use evaluate() instead"}
    
    def build_prompt(self, topic: str, agent_name: str = None) -> str:
        """Not used directly - use build_eval_prompt."""
        return ""
