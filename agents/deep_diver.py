"""
DEEP DIVER v4 — Uses Global Provider Pool
==========================================
FIXED: OpenRouter moved to END of preference list (only 200/day quota).
"""

from agents.base_agent import BaseAgent
from utils.logger import log_info, log_debug
from utils.memory_context import get_context_for_prompt
from utils.web_search import search_web, search_github_issues, format_search_results


class DeepDiver(BaseAgent):
    NAME = "deep_diver"
    SYSTEM_MSG = "Deep strategic analyst. Think step by step. Be rigorous and specific."
    
    # FIXED: OpenRouter LAST (only 200/day), high-quota providers first
    PREFERRED_PROVIDERS = ["cerebras", "groq", "gemini", "together", "cohere", "openrouter"]
    
    def build_prompt(self, topic: str) -> str:
        memory_context = get_context_for_prompt(topic, agent_name=self.NAME)
        
        web_results = search_web(f"{topic} why fails strategic analysis")
        github_results = search_github_issues(f"{topic} problem")
        
        all_results = web_results + github_results
        web_context = format_search_results(all_results)
        
        return f"""You are a DEEP DIVER — a strategic analyst who finds what others miss.

{memory_context}

═══════════════════════════════════════════════════════════════════
RESEARCH DATA FOR DEEP ANALYSIS:
═══════════════════════════════════════════════════════════════════
{web_context}

═══════════════════════════════════════════════════════════════════
DEEP DIVE MISSION: {topic}
═══════════════════════════════════════════════════════════════════

Think step by step. Produce analysis in this EXACT format:

## ROOT CAUSE ANALYSIS
Level 1: Surface problem...
Level 2: Because...
Level 3: Because...
Level 4: Because...
Level 5: Root cause...

## WHAT PREVIOUS RESEARCH MISSED
[Unexplored angles, wrong assumptions]

## HIDDEN OPPORTUNITIES
[2-3 opportunities from combining pain points in new ways]

## WHY CURRENT SOLUTIONS REALLY FAIL
[Structural reasons incumbents can't fix this]

## 3 CONTRARIAN TAKES
1. Consensus: X -> Actually: Y (because...)
2. Consensus: X -> Actually: Y (because...)
3. Consensus: X -> Actually: Y (because...)

## MVP CONCEPT
- Core feature (ONE thing):
- Target user (specific):
- Build time estimate:
- Why this beats existing:

## STRATEGIC VERDICT
[One non-obvious insight that changes everything]

QUALITY: Think from first principles. Challenge obvious assumptions.
"""
    
    def research(self, topic: str) -> dict:
        prompt = self.build_prompt(topic)
        result = self.call_api(prompt, max_tokens=2000, temperature=0.5)
        if result.get("success"):
            self.save_to_db(topic, result["text"])
        return result
