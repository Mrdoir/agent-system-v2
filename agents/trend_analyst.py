"""
TREND ANALYST v4 — Uses Global Provider Pool
"""

from agents.base_agent import BaseAgent
from utils.logger import log_info, log_debug
from utils.memory_context import get_context_for_prompt
from utils.web_search import search_web, search_hackernews, format_search_results


class TrendAnalyst(BaseAgent):
    NAME = "trend_analyst"
    SYSTEM_MSG = "You are a sharp trend analyst. Find emerging patterns with specific evidence."
    
    # Different order than Scout — spreads load across providers
    PREFERRED_PROVIDERS = ["groq", "cerebras", "together", "gemini", "openrouter", "cohere"]
    
    def build_prompt(self, topic: str) -> str:
        memory_context = get_context_for_prompt(topic, agent_name=self.NAME)
        
        web_results = search_web(f"{topic} trend growth 2026")
        hn_results = search_hackernews(f"{topic}")
        
        all_results = web_results + hn_results
        web_context = format_search_results(all_results)
        
        return f"""You are a TREND ANALYST — an expert at identifying emerging trends before they go mainstream.

{memory_context}

═══════════════════════════════════════════════════════════════════
REAL-TIME TREND DATA:
═══════════════════════════════════════════════════════════════════
{web_context}

═══════════════════════════════════════════════════════════════════
TREND ANALYSIS MISSION: {topic}
═══════════════════════════════════════════════════════════════════

Produce trend analysis in this EXACT format:

## NEW TREND SIGNALS (not previously documented)
[3-5 specific emerging signals with evidence]

## WHY NOW MATTERS
[What specifically changed in the last 6 months?]

## WHO IS DRIVING THIS TREND
[Specific early adopter segment]

## 12-MONTH PREDICTION
[Specific, falsifiable prediction]

## BUILD TIMING VERDICT
[Too early / Perfect timing / Too late?]

## TREND SCORE
Rate this trend: [1-10]
- Market Size Potential: [X/10]
- Timing Appropriateness: [X/10]
- Competition Level: [low/medium/high]

QUALITY REQUIREMENTS:
- NO vague statements like "growing trend"
- EVERY claim must have specific evidence
- Include growth percentages, user counts, or timeline data
"""
    
    def research(self, topic: str) -> dict:
        prompt = self.build_prompt(topic)
        result = self.call_api(prompt)
        if result["success"]:
            self.save_to_db(topic, result["text"])
        return result
