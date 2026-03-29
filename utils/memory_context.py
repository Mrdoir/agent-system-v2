"""
Memory context loader — feeds existing knowledge AND critic feedback
back into agent prompts. Makes agents genuinely smarter over time.
"""
from utils.database import (
    get_insights, get_do_not_repeat, get_recent_topics,
    get_critic_feedback_for_agent, get_agent_average_score
)


def get_context_for_prompt(topic: str, agent_name: str = None) -> str:
    """
    Build a memory context block to inject into any agent's prompt.
    Tells the agent what's already known, what to avoid,
    and what the Critic said about its last research.
    """
    insights = get_insights(limit=8)
    do_not_repeat = get_do_not_repeat()
    recent_topics = get_recent_topics(limit=10)
    context_parts = []

    # What we already know
    if insights:
        context_parts.append("## EXISTING KNOWLEDGE BASE (DO NOT repeat this):")
        for i in insights[:5]:
            lines = [l.strip() for l in i["content"].split("\n")
                     if l.strip().startswith("-") or l.strip().startswith("•")]
            preview = "\n".join(lines[:4]) if lines else i["content"][:300]
            context_parts.append(
                f"[Novelty {i['novelty_score']}/10 — {i['created_at'][:10]}]\n{preview}"
            )

    # What to avoid
    if do_not_repeat:
        context_parts.append("\n## BANNED PHRASES (never say these — too generic):")
        for p in do_not_repeat[:15]:
            context_parts.append(f"❌ {p}")

    # Critic feedback for THIS specific agent
    if agent_name:
        feedback = get_critic_feedback_for_agent(agent_name, limit=3)
        avg_score = get_agent_average_score(agent_name)

        if feedback:
            context_parts.append(f"\n## YOUR PERSONAL CRITIC FEEDBACK (learn from this!):")
            context_parts.append(f"Your average quality score: {avg_score}/10")
            context_parts.append("Your last research was reviewed by the Critic. Here's what they said:\n")

            for f in feedback:
                context_parts.append(
                    f"Topic: {f['topic']} — Score: {f['score']}/10\n"
                    f"✅ What you did well: {f['strength']}\n"
                    f"❌ What was weak: {f['weakness']}\n"
                    f"💡 How to improve: {f['improvement']}\n"
                )

            context_parts.append(
                "APPLY THIS FEEDBACK NOW: Fix the weaknesses above in your current research. "
                "The Critic will score you again — improve your score!"
            )
        else:
            context_parts.append(
                "\n## CRITIC FEEDBACK: No feedback yet — this is your first research. "
                "Be as specific and deep as possible to get a high score!"
            )

    # Mission
    context_parts.append(f"\n## YOUR MISSION FOR THIS TOPIC: '{topic}'")
    context_parts.append("- Find ONLY what is NOT in the knowledge base above")
    context_parts.append("- Be more specific than previous research")
    context_parts.append("- Fix any weaknesses mentioned in your critic feedback")
    context_parts.append("- Find real examples, real user quotes, real numbers")
    context_parts.append("- If you can't find something new and specific, say so honestly")

    return "\n".join(context_parts) if context_parts else ""
