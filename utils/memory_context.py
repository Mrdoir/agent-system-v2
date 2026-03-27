"""
Memory context loader — feeds existing knowledge back into agent prompts.
This is what makes agents genuinely smarter over time.
"""

from utils.database import get_insights, get_do_not_repeat, get_recent_topics


def get_context_for_prompt(topic: str) -> str:
    """
    Build a memory context block to inject into any agent's prompt.
    Tells the agent what's already known and what to avoid.
    """
    insights = get_insights(limit=8)
    do_not_repeat = get_do_not_repeat()
    recent_topics = get_recent_topics(limit=10)

    context_parts = []

    # What we already know
    if insights:
        context_parts.append("## EXISTING KNOWLEDGE BASE (what we already know — DO NOT repeat this):")
        for i in insights[:5]:
            # Extract just the key lines from insight
            lines = [l.strip() for l in i["content"].split("\n") if l.strip().startswith("-") or l.strip().startswith("•")]
            preview = "\n".join(lines[:4]) if lines else i["content"][:300]
            context_parts.append(f"[Novelty {i['novelty_score']}/10 — {i['created_at'][:10]}]\n{preview}")

    # What to avoid
    if do_not_repeat:
        context_parts.append("\n## BANNED PHRASES (never say these — too generic):")
        for p in do_not_repeat[:15]:
            context_parts.append(f"❌ {p}")

    # What to dig deeper on
    context_parts.append(f"\n## YOUR MISSION FOR THIS TOPIC: '{topic}'")
    context_parts.append("- Find ONLY what is NOT in the knowledge base above")
    context_parts.append("- Be more specific than previous research")
    context_parts.append("- Find real examples, real user quotes, real numbers where possible")
    context_parts.append("- If you can't find something new and specific, say so honestly")

    return "\n".join(context_parts) if context_parts else ""
