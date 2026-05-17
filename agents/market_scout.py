"""
MARKET SCOUT v3 — Primary research agent with expanded fallbacks
Improvements:
- Added Together AI and Cohere fallbacks
- Better prompt with structured output
- Parallel web search
- Quality self-check
"""

import os
from agents.base_agent import BaseAgent, OpenAICompatibleMixin, GeminiMixin
from utils.logger import log_info, log_warn, log_debug, log_api_call
from utils.memory_context import get_context_for_prompt
from utils.web_search import search_web, search_reddit, search_hackernews, format_search_results


class MarketScout(BaseAgent, OpenAICompatibleMixin, GeminiMixin):
    NAME = "market_scout"
    PROVIDER = "Gemini + Groq + Together + Cerebras + Cohere"
    
    def __init__(self):
        super().__init__()
        
        # API Keys
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.groq_key_2 = os.getenv("GROQ_API_KEY_2", "")
        self.cerebras_key = os.getenv("CEREBRAS_API_KEY", "")
        self.together_key = os.getenv("TOGETHER_API_KEY", "")
        self.cohere_key = os.getenv("COHERE_API_KEY", "")
        
        # Endpoints
        self.groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.cerebras_endpoint = "https://api.cerebras.ai/v1/chat/completions"
        self.together_endpoint = "https://api.together.xyz/v1/chat/completions"
        
        # Models
        self.gemini_model = "gemini-2.0-flash"
        self.groq_model = "llama-3.3-70b-versatile"
        self.cerebras_model = "llama-3.3-70b"
        self.together_model = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    
    def build_prompt(self, topic: str, agent_name: str = None) -> str:
        """Build research prompt with memory context and web data."""
        
        # Get memory context (what we already know, critic feedback)
        memory_context = get_context_for_prompt(topic, agent_name=agent_name or self.NAME)
        
        # Get fresh web data
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

## 🔍 NEW MARKET FINDINGS
[List 3-5 specific findings NOT in the knowledge base above]
[Include: specific app names, user counts, growth rates, dates]
[Each finding must have evidence from the web data]

## 🏆 TOP EXISTING SOLUTIONS & THEIR SPECIFIC WEAKNESSES
[Name 3-5 real apps/products with evidence-backed weaknesses]
[Format: AppName (X users) — specific weakness with evidence]

## 😤 REAL USER COMPLAINTS (direct quotes)
[Extract 3-5 direct quotes from the web data]
[Include source (Reddit, HN, etc.) and context]
[Focus on emotional language that reveals pain points]

## 🎯 UNTAPPED MARKET GAPS
[Identify 2-3 specific gaps based on the complaints above]
[For each: who has this problem, why existing solutions fail, size estimate]

## 💡 QUICK WIN OPPORTUNITY
[One specific, actionable opportunity that could be built quickly]
[Include: target user, core feature, why now, competition level]

## 📊 VERDICT
[2-3 sentences: What's the single most valuable insight from this research?]

QUALITY REQUIREMENTS:
- NO generic statements like "growing market" or "users want better UX"
- EVERY claim must reference specific evidence from the web data
- Include real numbers, names, and dates wherever possible
- If you can't find specific evidence, say "No data found" instead of making it up
"""
    
    def _call_cohere(self, prompt: str) -> dict:
        """Call Cohere API (free tier: 5 req/min)."""
        if not self.cohere_key:
            return {"success": False, "text": None, "provider": "cohere", "error": "No Cohere key"}
        
        try:
            import requests
            resp = requests.post(
                "https://api.cohere.ai/v1/chat",
                headers={
                    "Authorization": f"Bearer {self.cohere_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "command-r",
                    "message": prompt,
                    "max_tokens": 1500,
                    "temperature": 0.7
                },
                timeout=45
            )
            
            if resp.status_code == 429:
                return {"success": False, "rate_limited": True, "provider": "cohere"}
            
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}", "provider": "cohere"}
            
            data = resp.json()
            text = data.get("text", "")
            
            if not text:
                return {"success": False, "error": "Empty response", "provider": "cohere"}
            
            return {"success": True, "text": text, "provider": "cohere"}
            
        except Exception as e:
            return {"success": False, "error": str(e), "provider": "cohere"}
    
    def call_api(self, prompt: str) -> dict:
        """Call AI API with comprehensive fallback chain."""
        
        system_msg = "You are an expert market researcher. Be specific, use real data, avoid generic statements."
        
        # 1. Try Gemini (primary)
        log_debug(self.NAME, "Trying Gemini...")
        result = self._call_gemini(prompt, self.gemini_key, self.gemini_model)
        if result["success"]:
            log_api_call(self.NAME, "Gemini", True)
            return result
        log_api_call(self.NAME, "Gemini", False, f"({result.get('error', 'failed')})")
        if result.get("rate_limited"):
            # Continue to fallbacks
            pass
        
        # 2. Try Groq (fallback 1)
        log_debug(self.NAME, "Trying Groq...")
        result = self._call_openai_compatible(
            prompt, self.groq_endpoint, self.groq_key, 
            self.groq_model, "groq", system_msg
        )
        if result["success"]:
            log_api_call(self.NAME, "Groq", True)
            return result
        log_api_call(self.NAME, "Groq", False)
        
        # 3. Try Groq key 2 (fallback 2)
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
        
        # 4. Try Together AI (fallback 3)
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
        
        # 5. Try Cerebras (fallback 4)
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
        
        # 6. Try Cohere (fallback 5)
        if self.cohere_key:
            log_debug(self.NAME, "Trying Cohere...")
            result = self._call_cohere(prompt)
            if result["success"]:
                log_api_call(self.NAME, "Cohere", True)
                return result
            log_api_call(self.NAME, "Cohere", False)
        
        # All providers failed
        log_warn(self.NAME, "All providers exhausted")
        return {
            "success": False,
            "text": None,
            "provider": None,
            "rate_limited": True,  # Treat as rate limited to trigger pause
            "error": "All providers failed or rate limited"
        }
