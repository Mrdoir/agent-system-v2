"""
MARKET SCOUT v4 — Uses Global Provider Pool
============================================
Dramatically simplified. No more per-agent key management.
Just builds the prompt and calls pool.call_llm().
"""

from agents.base_agent import BaseAgent
from utils.logger import log_info, log_debug
from utils.memory_context import get_context_for_prompt
from utils.web_search import (
    search_web, search_reddit, search_hackernews, format_search_results
)


class MarketScout(BaseAgent):
    NAME = "market_scout"
    SYSTEM_MSG = "You are an expert market researcher. Be specific, use real data, avoid generic statements."
    
    # Prefer Gemini (fast, high quota), then spread across others
    PREFERRED_PROVIDERS = ["gemini", "groq", "together", "cerebras", "openrouter", "cohere"]
    
    def build_prompt(self, topic: str) -> str:
        """Build research prompt with memory context and web data."""
        memory_context = get_context_for_prompt(topic, agent_name=self.NAME)
        
        web_results = search_web(f"{topic} app complaints problems 2026")
        reddit_results = search_reddit(f"{topic} frustrating")
        hn_results = search_hackernews(f"{topic} problem")
        
        all_results = web_results + reddit_results + hn_results
        web_context = format_search_results(all_results)
        
        return f"""You are a MARKET SCOUT — an expert at finding specific, actionable market research insights.

{memory_context}

═══════════════════════════════════════════════════════════════════
REAL-TIME WEB DATA (use this as evidence):
═══════════════════════════════════════════════════════════════════
{web_context}

═══════════════════════════════════════════════════════════════════
YOUR RESEARCH MISSION: {topic}
═══════════════════════════════════════════════════════════════════

Analyze the web data above and produce research in this EXACT format:

## NEW MARKET FINDINGS
[List 3-5 specific findings NOT in the knowledge base above]
[Include: specific app names, user counts, growth rates, dates]

## TOP EXISTING SOLUTIONS & THEIR SPECIFIC WEAKNESSES
[Name 3-5 real apps/products with evidence-backed weaknesses]

## REAL USER COMPLAINTS (direct quotes)
[Extract 3-5 direct quotes from the web data]
[Include source (Reddit, HN, etc.) and context]

## UNTAPPED MARKET GAPS
[Identify 2-3 specific gaps based on the complaints above]

## QUICK WIN OPPORTUNITY
[One specific, actionable opportunity that could be built quickly]

## VERDICT
[2-3 sentences: the single most valuable insight]

QUALITY REQUIREMENTS:
- NO generic statements like "growing market"
- EVERY claim must reference specific evidence
- Include real numbers, names, and dates
- If you can't find evidence, say "No data found"
"""
    
    def research(self, topic: str) -> dict:
        """Run market research on a topic."""
        prompt = self.build_prompt(topic)
        result = self.call_api(prompt)
        
        if result["success"]:
            self.save_to_db(topic, result["text"])
        
        return result
