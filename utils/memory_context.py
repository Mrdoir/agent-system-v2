"""
MEMORY CONTEXT v3 — Enhanced context building with learning
Improvements:
- More detailed critic feedback injection
- Common weakness analysis
- Performance trend awareness
- Competitor agent comparison
- Smarter context truncation
"""

from utils.database import (
    get_insights, get_do_not_repeat, get_recent_topics,
    get_critic_feedback_for_agent, get_agent_average_score,
    get_common_weaknesses, get_agent_stats, is_topic_saturated
)


def get_context_for_prompt(topic: str, agent_name: str = None) -> str:
    """
    Build a comprehensive memory context to inject into agent prompts.
    Tells the agent:
    - What's already known (don't repeat)
    - What to avoid (banned phrases)
    - Personal critic feedback (learn from mistakes)
    - Performance metrics (motivation)
    - Topic saturation status
    """
    context_parts = []
    
    # ─── EXISTING KNOWLEDGE BASE ───────────────────────────────────
    insights = get_insights(limit=8)
    if insights:
        context_parts.append("## 📚 EXISTING KNOWLEDGE BASE (DO NOT repeat this):\n")
        for i in insights[:5]:
            # Extract bullet points from insights
            lines = [l.strip() for l in i["content"].split("\n")
                     if l.strip().startswith(("-", "•", "*", "1", "2", "3"))]
            preview = "\n".join(lines[:4]) if lines else i["content"][:350]
            novelty = i.get("novelty_score", 0)
            date = i.get("created_at", "")[:10]
            context_parts.append(f"[Novelty {novelty}/10 — {date}]\n{preview}\n")
    
    # ─── BANNED PHRASES ────────────────────────────────────────────
    do_not_repeat = get_do_not_repeat()
    if do_not_repeat:
        context_parts.append("\n## 🚫 BANNED PHRASES (never use these — too generic):")
        for p in do_not_repeat[:20]:
            context_parts.append(f"❌ \"{p}\"")
    
    # ─── TOPIC SATURATION WARNING ──────────────────────────────────
    if is_topic_saturated(topic):
        context_parts.append(f"""
## ⚠️ TOPIC SATURATION WARNING
This topic has been heavily researched with diminishing returns.
You MUST find a completely new angle or sub-niche.
Consider: specific user segment, geographic focus, or emerging tech intersection.
""")
    
    # ─── PERSONAL CRITIC FEEDBACK ──────────────────────────────────
    if agent_name:
        feedback = get_critic_feedback_for_agent(agent_name, limit=3)
        avg_score = get_agent_average_score(agent_name)
        common_weaknesses = get_common_weaknesses(agent_name, limit=3)
        stats = get_agent_stats(agent_name)
        
        if feedback:
            context_parts.append(f"\n## 📊 YOUR PERFORMANCE REPORT ({agent_name.upper()}):")
            context_parts.append(f"• Average Quality Score: {avg_score}/10")
            
            if stats:
                total = stats.get("total_results", 0)
                high_quality = stats.get("high_quality_count", 0)
                if total > 0:
                    quality_rate = round(high_quality / total * 100)
                    context_parts.append(f"• High-Quality Rate: {quality_rate}% ({high_quality}/{total})")
            
            # Common weaknesses
            if common_weaknesses:
                context_parts.append("\n### 🔴 YOUR RECURRING WEAKNESSES (fix these!):")
                for w in common_weaknesses:
                    context_parts.append(f"  → {w}")
            
            # Recent feedback
            context_parts.append("\n### 📝 RECENT CRITIC FEEDBACK:")
            for f in feedback:
                context_parts.append(f"""
Topic: {f.get('topic', 'Unknown')[:50]}
Score: {f.get('score', 0)}/10
✅ Strength: {f.get('strength', 'N/A')}
❌ Weakness: {f.get('weakness', 'N/A')}
💡 Improve: {f.get('improvement', 'N/A')}
""")
            
            # Motivation based on score
            if avg_score >= 7:
                context_parts.append("🌟 You're performing well! Maintain this quality.")
            elif avg_score >= 5:
                context_parts.append("📈 Room for improvement. Focus on being more specific.")
            else:
                context_parts.append("⚠️ Quality needs work. Read feedback carefully and apply it.")
        
        else:
            context_parts.append(f"""
## 📊 YOUR PERFORMANCE ({agent_name.upper()})
No feedback yet — this is your first research!
Be as specific and evidence-based as possible to get a high score.
""")
    
    # ─── MISSION BRIEF ─────────────────────────────────────────────
    context_parts.append(f"""
## 🎯 YOUR MISSION FOR: '{topic}'

REQUIREMENTS:
1. Find ONLY information NOT in the knowledge base above
2. Be MORE specific than previous research
3. Fix any weaknesses mentioned in your feedback
4. Use REAL examples: names, numbers, dates, quotes
5. If you can't find something genuinely new, say so honestly
6. Avoid ALL banned phrases

QUALITY CHECKLIST:
□ Did I include specific app/product names?
□ Did I include real numbers (%, $, users)?
□ Did I quote actual user complaints?
□ Did I identify a specific underserved niche?
□ Did I avoid generic statements?
□ Did I address my previous weaknesses?

Remember: Generic research = 0 value. Specific research = valuable insights.
""")
    
    return "\n".join(context_parts) if context_parts else ""


def get_synthesis_context(new_content: str, topic: str) -> str:
    """
    Build context for the memory/synthesis agent.
    Helps it compare new research with existing knowledge.
    """
    insights = get_insights(limit=10)
    do_not_repeat = get_do_not_repeat()
    
    existing_text = ""
    if insights:
        existing_text = "\n---\n".join([
            f"[{i.get('created_at', '')[:10]} | Novelty: {i.get('novelty_score', 0)}/10]\n{i['content'][:400]}"
            for i in insights[:5]
        ])
    else:
        existing_text = "No previous insights yet."
    
    dnr_text = "\n".join(f"- {p}" for p in do_not_repeat[:15]) if do_not_repeat else "None yet."
    
    return f"""## EXISTING KNOWLEDGE BASE
{existing_text}

## PATTERNS TO NEVER REPEAT
{dnr_text}

## NEW RESEARCH TO SYNTHESIZE
Topic: {topic}
Content:
{new_content[:2500]}
"""


def get_critic_context(topic: str, research_content: str) -> str:
    """
    Build context for the critic agent.
    Includes quality standards and previous patterns.
    """
    do_not_repeat = get_do_not_repeat()
    dnr_list = "\n".join(f"- {p}" for p in do_not_repeat[:25]) if do_not_repeat else "None yet"
    
    return f"""## RESEARCH QUALITY EVALUATION

### TOPIC: {topic}

### RESEARCH CONTENT TO EVALUATE:
{research_content[:4000]}

### PATTERNS THAT INDICATE LOW QUALITY (penalize these):
{dnr_list}

### SCORING GUIDE
- 9-10: Exceptional — specific, actionable, novel insights with evidence
- 7-8: Good — mostly specific, some actionable insights
- 5-6: Average — mix of specific and generic, needs improvement
- 3-4: Below Average — mostly generic, few specifics
- 1-2: Poor — all generic statements, no real insights

### WHAT TO LOOK FOR
POSITIVE SIGNALS (raise score):
+ Specific product/app names mentioned
+ Real numbers (users, revenue, growth %)
+ Direct user quotes or complaints
+ Specific underserved niches identified
+ Actionable recommendations
+ Contrarian insights with evidence

NEGATIVE SIGNALS (lower score):
- Generic phrases like "growing market" without numbers
- Vague recommendations like "improve user experience"
- No specific products or competitors mentioned
- Repeating common knowledge
- No evidence for claims
"""


def get_weekly_synthesis_context(results: list, insights: list) -> str:
    """
    Build context for weekly synthesis reports.
    """
    # Sort by score
    high_scored = sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:20]
    
    results_text = "\n\n".join([
        f"[{r.get('agent', '?')} | Score: {r.get('score', 0)}/10 | {r.get('topic', '')}]\n{r.get('content', '')[:500]}"
        for r in high_scored
    ])
    
    insights_text = "\n\n".join([
        f"[Novelty: {i.get('novelty_score', 0)}/10]\n{i.get('content', '')[:400]}"
        for i in insights[:5]
    ])
    
    return f"""## WEEKLY RESEARCH SYNTHESIS CONTEXT

### TOP {len(high_scored)} RESEARCH RESULTS (sorted by score):
{results_text}

### TOP INSIGHTS:
{insights_text}

### YOUR TASK
Analyze all research and extract:
1. Top 3 market opportunities with evidence
2. Most complained about problems (real patterns)
3. Actionable app/product ideas
4. Strongest trends with data
5. What to avoid (oversaturated areas)
6. Single most important finding

Be specific. Use real examples from the research.
"""
