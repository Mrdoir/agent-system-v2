"""
MEMORY AGENT v3 — Knowledge synthesis with better novelty detection
Improvements:
- Better novelty scoring algorithm
- Pattern extraction from insights
- Knowledge graph awareness
- Duplicate detection
"""

import os
import re
from agents.base_agent import BaseAgent, GeminiMixin
from utils.logger import log_info, log_debug, log_api_call
from utils.database import (
    get_insights, get_do_not_repeat, save_insight, add_do_not_repeat,
    update_agent_status
)


class MemoryAgent(BaseAgent, GeminiMixin):
    NAME = "memory"
    PROVIDER = "Google Gemini Flash"
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = "gemini-2.0-flash"
    
    def build_synthesis_prompt(self, new_content: str, existing_insights: list, 
                                do_not_repeat: list, topic: str) -> str:
        """Build prompt for knowledge synthesis."""
        
        # Format existing insights
        existing_text = ""
        if existing_insights:
            existing_text = "\n\n---\n\n".join([
                f"[{i.get('created_at', '')[:10]} | Novelty: {i.get('novelty_score', 0)}/10]\n{i['content'][:400]}"
                for i in existing_insights[:6]
            ])
        else:
            existing_text = "No previous insights yet — this is new territory!"
        
        # Format banned patterns
        dnr_text = "\n".join(f"- {p}" for p in do_not_repeat[:20]) if do_not_repeat else "None yet."
        
        return f"""You are a KNOWLEDGE SYNTHESIZER — your job is to compare new research with existing knowledge and extract ONLY what's genuinely novel.

═══════════════════════════════════════════════════════════════════
EXISTING KNOWLEDGE BASE (what we already know):
═══════════════════════════════════════════════════════════════════
{existing_text}

═══════════════════════════════════════════════════════════════════
PATTERNS WE'VE SEEN TOO MANY TIMES (skip these):
═══════════════════════════════════════════════════════════════════
{dnr_text}

═══════════════════════════════════════════════════════════════════
NEW RESEARCH TO SYNTHESIZE:
Topic: {topic}
═══════════════════════════════════════════════════════════════════
{new_content[:3000]}

═══════════════════════════════════════════════════════════════════
YOUR SYNTHESIS TASK
═══════════════════════════════════════════════════════════════════

Compare the new research against existing knowledge. Respond in this EXACT format:

## NOVELTY CHECK
Is this research adding anything genuinely new?
Answer: [YES/PARTIALLY/NO]
Reasoning: [2-3 sentences explaining why]

## NEW PATTERNS FOUND
[List ONLY patterns NOT seen in the knowledge base above]
[If nothing new, say "No new patterns found"]
- Pattern 1: [specific new finding]
- Pattern 2: [specific new finding]
- Pattern 3: [specific new finding]

## UPDATED KNOWLEDGE ENTRY
[Write 4-6 bullet points of UNIQUE insights to add to memory]
[Focus on:]
[- Specific pain points with real user language]
[- Underserved niches with evidence]
[- Market gaps that aren't already documented]
[Skip anything that's already in the knowledge base above!]

• 
• 
• 
• 

## CONNECTIONS DISCOVERED
[What patterns connect this research to previous insights?]
[List 1-2 cross-topic connections if any]

## NOVELTY SCORE: [X]/10
Scoring guide:
- 9-10: Completely new territory, breakthrough insight
- 7-8: Significant new information, valuable addition
- 5-6: Some new details, mostly confirms existing knowledge
- 3-4: Minor new information, largely redundant
- 1-2: Nothing new, duplicate of existing knowledge

## PATTERNS TO BLACKLIST
[2-3 generic phrases to add to do-not-repeat list]
-
-
-

═══════════════════════════════════════════════════════════════════
IMPORTANT: Only extract what's GENUINELY NEW. 
If the research just confirms what we already know, say so honestly.
Generic insights = 0 value. Specific novel insights = valuable.
═══════════════════════════════════════════════════════════════════
"""
    
    def extract_novelty_score(self, text: str) -> int:
        """Extract novelty score from synthesis."""
        for line in text.split("\n"):
            if "NOVELTY SCORE" in line.upper():
                numbers = re.findall(r'\d+', line)
                if numbers:
                    score = int(numbers[0])
                    return min(10, max(0, score))
        return 5
    
    def extract_blacklist_patterns(self, text: str) -> list:
        """Extract patterns to blacklist."""
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
                    if 10 < len(pattern) < 100:
                        patterns.append(pattern)
        
        return patterns[:3]
    
    def extract_new_patterns(self, text: str) -> list:
        """Extract new patterns discovered."""
        patterns = []
        in_section = False
        
        for line in text.split("\n"):
            if "NEW PATTERNS FOUND" in line.upper():
                in_section = True
                continue
            
            if in_section:
                if line.strip().startswith("##"):
                    break
                
                if line.strip().startswith("-") or line.strip().startswith("•"):
                    pattern = line.strip("- •").strip()
                    if len(pattern) > 10:
                        patterns.append(pattern)
        
        return patterns
    
    def synthesize(self, new_content: str, topic: str) -> dict:
        """
        Compare new research with memory and extract novel insights.
        
        Returns: {"success": bool, "novelty_score": int, "synthesis": str}
        """
        if self.is_rate_limited():
            return {"success": False, "rate_limited": True}
        
        # Get existing knowledge
        existing_insights = get_insights(limit=10)
        do_not_repeat = get_do_not_repeat()
        
        # Build prompt
        prompt = self.build_synthesis_prompt(new_content, existing_insights, do_not_repeat, topic)
        
        # Call API
        result = self._call_gemini(prompt, self.api_key, self.model, max_tokens=1200, temperature=0.3)
        
        if result.get("rate_limited"):
            self.set_rate_limited()
            return {"success": False, "rate_limited": True}
        
        if not result.get("success"):
            return {"success": False, "error": result.get("error")}
        
        synthesis_text = result["text"]
        
        # Extract novelty score
        novelty_score = self.extract_novelty_score(synthesis_text)
        
        # Save to insights if novel enough
        if novelty_score >= 5:
            save_insight(synthesis_text, [topic], novelty_score)
            log_info(self.NAME, f"Saved insight (novelty: {novelty_score}/10)")
        else:
            log_debug(self.NAME, f"Skipped saving (low novelty: {novelty_score}/10)")
        
        # Extract and save blacklist patterns
        patterns = self.extract_blacklist_patterns(synthesis_text)
        for pattern in patterns:
            add_do_not_repeat(pattern)
        
        # Update status
        update_agent_status(self.NAME, "active", tasks_completed=1, score=novelty_score)
        
        # Extract new patterns for return
        new_patterns = self.extract_new_patterns(synthesis_text)
        
        return {
            "success": True,
            "novelty_score": novelty_score,
            "synthesis": synthesis_text,
            "new_patterns": new_patterns,
            "provider": "gemini"
        }
    
    def get_memory_summary(self, limit: int = 5) -> str:
        """Get a summary of stored knowledge for other agents."""
        insights = get_insights(limit=limit, min_novelty=5)
        
        if not insights:
            return "No stored knowledge yet."
        
        summary_parts = []
        for i in insights:
            # Extract key bullet points
            content = i.get("content", "")
            bullets = [l.strip() for l in content.split("\n") 
                      if l.strip().startswith(("•", "-", "*"))]
            
            if bullets:
                summary_parts.append(f"[Novelty {i.get('novelty_score', 0)}/10]\n" + "\n".join(bullets[:3]))
        
        return "\n\n".join(summary_parts) if summary_parts else "No high-novelty insights yet."
    
    def research(self, topic: str) -> dict:
        """Memory agent doesn't do research, use synthesize() instead."""
        return {"success": False, "error": "Use synthesize() instead"}
    
    def build_prompt(self, topic: str, agent_name: str = None) -> str:
        """Not used directly."""
        return ""
    
    def call_api(self, prompt: str) -> dict:
        """Not used directly."""
        return {"success": False, "error": "Use synthesize() instead"}
