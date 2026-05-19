"""
CRITIC v4 — Uses Global Provider Pool
======================================
FIXED: OpenRouter moved to END of preference list (only 200/day quota).
"""

import re
from agents.base_agent import BaseAgent
from utils.logger import log_info, log_debug
from utils.database import (
    get_do_not_repeat, save_critic_feedback, add_do_not_repeat,
    update_agent_status
)


class CriticAgent(BaseAgent):
    NAME = "critic"
    SYSTEM_MSG = "Elite research critic. Think deeply. Be specific and ruthless about quality."
    
    # FIXED: OpenRouter LAST (only 200/day), high-quota providers first
    PREFERRED_PROVIDERS = ["groq", "cerebras", "gemini", "together", "cohere", "openrouter"]
    
    def build_eval_prompt(self, topic: str, research_content: str) -> str:
        do_not_repeat = get_do_not_repeat()
        dnr_list = "\n".join(f"- {p}" for p in do_not_repeat[:25]) if do_not_repeat else "None yet"
        
        return f"""You are an ELITE RESEARCH CRITIC with deep reasoning capabilities.

TOPIC: {topic}

RESEARCH TO EVALUATE:
{research_content[:5000]}

PATTERNS THAT INDICATE LOW QUALITY (penalize if found):
{dnr_list}

Respond in this EXACT format:

## OVERALL QUALITY SCORE: [X]/10
[2-3 sentences explaining score]

## MARKET SCOUT FEEDBACK
Score: [X]/10
Strength: [specific]
Weakness: [specific]
Improvement: [exact instruction]

## TREND ANALYST FEEDBACK
Score: [X]/10
Strength: [specific]
Weakness: [specific]
Improvement: [exact instruction]

## DEEP DIVER FEEDBACK
Score: [X]/10
Strength: [specific]
Weakness: [specific]
Improvement: [exact instruction]

## TOP 3 ACTIONABLE TAKEAWAYS
1. 
2. 
3. 

## PATTERNS TO BLACKLIST
- 
- 

## FINAL VERDICT
[1 sentence: Is this research worth reading?]

SCORING: 9-10 Exceptional, 7-8 Good, 5-6 Average, 3-4 Below, 1-2 Poor
Be ruthless. Generic = worthless. Specific = valuable.
"""
    
    def extract_score(self, text: str) -> int:
        for line in text.split("\n"):
            if "OVERALL QUALITY SCORE" in line.upper() or "SCORE:" in line.upper():
                numbers = re.findall(r'\d+', line)
                if numbers:
                    return min(10, max(0, int(numbers[0])))
        return 5
    
    def extract_agent_feedback(self, text: str, agent_name: str) -> dict:
        feedback = {"score": 5, "strength": "", "weakness": "", "improvement": ""}
        in_section = False
        
        for line in text.split("\n"):
            upper = line.upper()
            if agent_name.upper().replace("_", " ") in upper and "FEEDBACK" in upper:
                in_section = True
                continue
            if in_section:
                if line.strip().startswith("##"):
                    break
                if "Score:" in line:
                    nums = re.findall(r'\d+', line)
                    if nums:
                        feedback["score"] = min(10, int(nums[0]))
                elif "Strength:" in line:
                    feedback["strength"] = line.split(":", 1)[-1].strip()
                elif "Weakness:" in line:
                    feedback["weakness"] = line.split(":", 1)[-1].strip()
                elif "Improvement:" in line or "Improve:" in line:
                    feedback["improvement"] = line.split(":", 1)[-1].strip()
        
        return feedback
    
    def extract_blacklist(self, text: str) -> list:
        patterns = []
        in_section = False
        for line in text.split("\n"):
            if "BLACKLIST" in line.upper():
                in_section = True
                continue
            if in_section:
                if line.strip().startswith("##"):
                    break
                if line.strip().startswith("-"):
                    p = line.strip("- ").strip()
                    if 10 < len(p) < 100:
                        patterns.append(p)
        return patterns[:3]
    
    def evaluate(self, topic: str, content: str) -> dict:
        prompt = self.build_eval_prompt(topic, content)
        
        # Uses the pool via BaseAgent.call_api()
        result = self.call_api(prompt, max_tokens=2500, temperature=0.2)
        
        if not result.get("success"):
            return result
        
        text = result["text"]
        score = self.extract_score(text)
        
        # Save per-agent feedback
        for agent in ["market_scout", "trend_analyst", "deep_diver"]:
            fb = self.extract_agent_feedback(text, agent)
            if fb["strength"] or fb["weakness"]:
                save_critic_feedback(agent, topic, fb["score"],
                    fb["strength"], fb["weakness"], fb["improvement"])
        
        # Blacklist generic patterns
        for pattern in self.extract_blacklist(text):
            add_do_not_repeat(pattern)
        
        update_agent_status(self.NAME, "active", tasks_completed=1, score=score)
        
        result["score"] = score
        result["evaluation"] = text
        return result
