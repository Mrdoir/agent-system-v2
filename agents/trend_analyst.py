"""
TREND ANALYST v3 — Trend detection with expanded sources
Improvements:
- Hacker News trend analysis
- Product Hunt awareness
- Better timing analysis
- Expanded fallback chain
"""

import os
from agents.base_agent import BaseAgent, OpenAICompatibleMixin, GeminiMixin
from utils.logger import log_info, log_warn, log_debug, log_api_call
from utils.memory_context import get_context_for_prompt
from utils.web_search import search_web, search_hackernews, format_search_results


class TrendAnalyst(BaseAgent, OpenAICompatibleMixin, GeminiMixin):
    NAME = "trend_analyst"
    PROVIDER = "Groq + Cerebras + Together + Gemini"
    
    def __init__(self):
        super().__init__()
        
        # API Keys
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.groq_key_2 = os.getenv("GROQ_API_KEY_2", "")
        self.cerebras_key = os.getenv("CEREBRAS_API_KEY", "")
        self.together_key = os.getenv("TOGETHER_API_KEY", "")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        
        # Endpoints
        self.groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.cerebras_endpoint = "https://api.cerebras.ai/v1/chat/completions"
        self.together_endpoint = "https://api.together.xyz/v1/chat/completions"
        
        # Models
        self.groq_model = "llama-3.3-70b-versatile"
        self.cerebras_model = "llama-3.3-70b"
        self.together_model = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
        self.gemini_model = "gemini-2.0-flash"
    
    def build_prompt(self, topic: str, agent_name: str = None) -> str:
        """Build trend analysis prompt."""
        
        memory_context = get_context_for_prompt(topic, agent_name=agent_name or self.NAME)
        
        # Get diverse trend signals
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

Analyze the data and produce trend analysis in this EXACT format:

## 📈 NEW TREND SIGNALS (not previously documented)
[List 3-5 specific emerging signals with evidence]
[Include: growth rates, adoption metrics, timeline data]
[Each signal must have a source reference]

## ⏰ WHY NOW MATTERS
[What specifically changed in the last 6 months?]
[Include: triggering events, market shifts, technology enablers]
[Be specific about dates and causation]

## 👥 WHO IS DRIVING THIS TREND
[Identify the specific early adopter segment]
[Include: demographics, behaviors, psychographics]
[Name specific communities or platforms where they gather]

## 🔮 12-MONTH PREDICTION
[Make a specific, falsifiable prediction]
[Include: expected metrics, timeline, confidence level]
[What would prove this prediction wrong?]

## 🎭 CONTRARIAN TAKE
[What does everyone believe about this trend that's actually wrong?]
[Provide evidence for why the consensus is flawed]

## 📊 BUILD TIMING VERDICT
[Too early / Perfect timing / Too late?]
[Include: specific reasoning and risk factors]
[What milestones to watch for?]

## 🎯 TREND SCORE
Rate this trend: [1-10]
- Market Size Potential: [X/10]
- Timing Appropriateness: [X/10]
- Competition Level: [low/medium/high]
- Execution Difficulty: [low/medium/high]

QUALITY REQUIREMENTS:
- NO vague statements like "growing trend" or "increasing demand"
- EVERY trend claim must have specific evidence
- Include growth percentages, user counts, or timeline data
- Compare to similar historical trends for context
"""
    
    def call_api(self, prompt: str) -> dict:
        """Call AI API with fallback chain."""
        
        system_msg = "You are a sharp trend analyst. Find emerging patterns with specific evidence. No generic trend statements."
        
        # 1. Try Groq (primary - fast)
        log_debug(self.NAME, "Trying Groq...")
        result = self._call_openai_compatible(
            prompt, self.groq_endpoint, self.groq_key,
            self.groq_model, "groq", system_msg
        )
        if result["success"]:
            log_api_call(self.NAME, "Groq", True)
            return result
        log_api_call(self.NAME, "Groq", False)
        
        # 2. Try Groq key 2
        if self.groq_key_2:
            log_debug(self.NAME, "Trying Groq key 2...")
            result = self._call_openai_compatible(
                prompt, self.groq_endpoint, self.groq_key_2,
                self.groq_model, "groq-2", system_msg
            )
            if result["success"]:
                log_api_call(self.NAME, "Groq-2", True)
                return result
            log_api_call(self.NAME, "Groq-2", False)
        
        # 3. Try Together AI
        if self.together_key:
            log_debug(self.NAME, "Trying Together AI...")
            result = self._call_openai_compatible(
                prompt, self.together_endpoint, self.together_key,
                self.together_model, "together", system_msg
            )
            if result["success"]:
                log_api_call(self.NAME, "Together", True)
                return result
            log_api_call(self.NAME, "Together", False)
        
        # 4. Try Cerebras
        if self.cerebras_key:
            log_debug(self.NAME, "Trying Cerebras...")
            result = self._call_openai_compatible(
                prompt, self.cerebras_endpoint, self.cerebras_key,
                self.cerebras_model, "cerebras", system_msg
            )
            if result["success"]:
                log_api_call(self.NAME, "Cerebras", True)
                return result
            log_api_call(self.NAME, "Cerebras", False)
        
        # 5. Try Gemini (fallback)
        if self.gemini_key:
            log_debug(self.NAME, "Trying Gemini...")
            result = self._call_gemini(prompt, self.gemini_key, self.gemini_model)
            if result["success"]:
                log_api_call(self.NAME, "Gemini", True)
                return result
            log_api_call(self.NAME, "Gemini", False)
        
        # All failed
        log_warn(self.NAME, "All providers exhausted")
        return {
            "success": False,
            "text": None,
            "provider": None,
            "rate_limited": True,
            "error": "All providers failed"
        }
