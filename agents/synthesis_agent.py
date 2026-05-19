"""
SYNTHESIS AGENT v4 — Uses Global Provider Pool
===============================================
FIXED: No longer has its own _call_api(). Uses pool like every other agent.
"""

from datetime import datetime, timedelta
from agents.base_agent import BaseAgent
from utils.logger import log_info, log_warn, log_debug
from utils.database import get_results, get_insights, save_result, update_agent_status
from utils.notifier import notify_weekly_synthesis
from utils.memory_context import get_weekly_synthesis_context


class SynthesisAgent(BaseAgent):
    NAME = "synthesis"
    SYSTEM_MSG = "Strategic research synthesizer. Be specific and actionable. Prioritize quality over quantity."
    
    # Prefer Groq (fast, high quota), then fallbacks
    PREFERRED_PROVIDERS = ["groq", "together", "cerebras", "gemini", "openrouter", "cohere"]
    
    def get_weekly_results(self) -> list:
        """Get all results from the past week."""
        try:
            all_results = get_results(limit=500)
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            return [r for r in all_results if r.get("created_at", "") >= week_ago]
        except Exception as e:
            log_warn(self.NAME, f"Error fetching results: {e}")
            return []
    
    def get_top_insights(self) -> list:
        """Get top insights from the past week."""
        try:
            insights = get_insights(limit=20)
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            weekly = [i for i in insights if i.get("created_at", "") >= week_ago]
            return sorted(weekly, key=lambda x: x.get("novelty_score", 0), reverse=True)[:5]
        except Exception as e:
            log_warn(self.NAME, f"Error fetching insights: {e}")
            return []
    
    def build_synthesis_prompt(self, results: list, insights: list) -> str:
        """Build the weekly synthesis prompt."""
        
        # Get context
        context = get_weekly_synthesis_context(results, insights)
        
        # Calculate stats
        total_results = len(results)
        avg_score = sum(r.get("score", 0) for r in results) / max(len(results), 1)
        high_quality = len([r for r in results if r.get("score", 0) >= 7])
        unique_topics = len(set(r.get("topic", "") for r in results))
        
        return f"""You are a STRATEGIC RESEARCH SYNTHESIZER analyzing a week of market research.

═══════════════════════════════════════════════════════════════════
WEEKLY STATS
═══════════════════════════════════════════════════════════════════
- Total Research Results: {total_results}
- Average Quality Score: {avg_score:.1f}/10
- High-Quality Results (7+): {high_quality}
- Unique Topics Covered: {unique_topics}

{context}

═══════════════════════════════════════════════════════════════════
YOUR SYNTHESIS TASK
═══════════════════════════════════════════════════════════════════

Create a comprehensive weekly synthesis. Use this EXACT format:

## TOP 3 MARKET OPPORTUNITIES THIS WEEK

### Opportunity 1: [Name]
- **Problem**: [Specific problem from research]
- **Target User**: [Who has this problem - be specific]
- **Why Now**: [What changed to make this timely]
- **Existing Solutions**: [What's failing and why]
- **Opportunity Size**: [Estimate with reasoning]
- **Evidence**: [Quotes/data from research]
- **Build Difficulty**: [Low/Medium/High]
- **Competition**: [Low/Medium/High]

### Opportunity 2: [Name]
[Same format]

### Opportunity 3: [Name]
[Same format]

## TOP 3 MOST COMPLAINED ABOUT PROBLEMS

1. **[Problem]**
   - Source: [Where we found this]
   - User Quote: "[Direct quote if available]"
   - Frequency: [How often this appeared]
   - Unmet Need: [What users actually want]

2. **[Problem]**
   [Same format]

3. **[Problem]**
   [Same format]

## TOP 3 APP/PRODUCT IDEAS

### Idea 1: [Name]
- One-line: [What it does in one sentence]
- Target: [Specific user segment]
- Core Feature: [The ONE thing that matters]
- Why It Wins: [Unfair advantage over existing]
- MVP Scope: [What to build first]
- Competition: [Low/Medium/High]
- Confidence: [1-10 with reasoning]

### Idea 2: [Name]
[Same format]

### Idea 3: [Name]
[Same format]

## STRONGEST TREND THIS WEEK

**Trend**: [Name the trend]
- Evidence: [What data supports this]
- Growth Signal: [Specific metrics if available]
- Who's Driving It: [User segment]
- Timeline: [When to act]
- Opportunity Window: [How long until saturated]

## WHAT TO AVOID

### Saturated/Declining Areas:
- [Area 1]: [Why to avoid]
- [Area 2]: [Why to avoid]

### Common Mistakes We Saw:
- [Mistake 1]
- [Mistake 2]

## WEEKLY VERDICT

**The Single Most Important Finding:**
[2-3 sentences on the #1 actionable insight from this week]

**Recommended Next Steps:**
1. [Specific action]
2. [Specific action]
3. [Specific action]

═══════════════════════════════════════════════════════════════════
QUALITY REQUIREMENTS:
- Be specific — names, numbers, quotes
- Prioritize actionable over interesting
- Include evidence from research
- Don't recommend anything already oversaturated
═══════════════════════════════════════════════════════════════════
"""
    
    def generate_weekly(self) -> dict:
        """Generate weekly synthesis report using the global provider pool."""
        results = self.get_weekly_results()
        insights = self.get_top_insights()
        
        if not results:
            log_warn(self.NAME, "No results from past week to synthesize")
            return {"success": False, "error": "No results to synthesize"}
        
        log_info(self.NAME, f"Synthesizing {len(results)} results from past week")
        
        prompt = self.build_synthesis_prompt(results, insights)
        
        # USE THE POOL (not direct API call)
        result = self.call_api(prompt, max_tokens=3000, temperature=0.4)
        
        if not result.get("success"):
            log_warn(self.NAME, f"Synthesis failed: {result.get('error')}")
            return result
        
        synthesis_text = result["text"]
        
        # Save synthesis as a special result
        self.save_to_db(
            topic="weekly_synthesis",
            content=synthesis_text,
            score=8,
            tags=["synthesis", "weekly"]
        )
        
        # Update status
        update_agent_status(self.NAME, "active", tasks_completed=1, score=8)
        
        # Send notification
        try:
            notify_weekly_synthesis(synthesis_text[:2000])
        except Exception as e:
            log_debug(self.NAME, f"Notification error: {e}")
        
        log_info(self.NAME, "Weekly synthesis complete")
        
        return {
            "success": True,
            "synthesis": synthesis_text,
            "results_count": len(results),
            "insights_count": len(insights),
            "provider": result.get("provider", "unknown")
        }
