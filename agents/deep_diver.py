"""
DEEP DIVER v3 — Strategic deep analysis with reasoning models
Improvements:
- Multiple reasoning models (DeepSeek, Qwen, QwQ)
- Deeper competitive analysis
- Root cause analysis framework
- Expanded fallback chain
"""

import os
from agents.base_agent import BaseAgent, OpenAICompatibleMixin, GeminiMixin
from utils.logger import log_info, log_warn, log_debug, log_api_call
from utils.memory_context import get_context_for_prompt
from utils.web_search import search_web, search_github_issues, format_search_results


class DeepDiver(BaseAgent, OpenAICompatibleMixin, GeminiMixin):
    NAME = "deep_diver"
    PROVIDER = "Nemotron + QwQ + Cerebras + Together + Gemini"
    
    def __init__(self):
        super().__init__()
        
        # API Keys
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_key_2 = os.getenv("OPENROUTER_API_KEY_2", "")
        self.openrouter_key_3 = os.getenv("OPENROUTER_API_KEY_3", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.cerebras_key = os.getenv("CEREBRAS_API_KEY", "")
        self.together_key = os.getenv("TOGETHER_API_KEY", "")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        
        # Endpoints
        self.openrouter_endpoint = "https://openrouter.ai/api/v1/chat/completions"
        self.groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.cerebras_endpoint = "https://api.cerebras.ai/v1/chat/completions"
        self.together_endpoint = "https://api.together.xyz/v1/chat/completions"
        
        # Models
        self.primary_model = "nvidia/llama-3.1-nemotron-70b-instruct:free"
        self.qwq_model = "qwen/qwq-32b:free"
        self.groq_model = "qwen-qwq-32b"
        self.cerebras_model = "llama-3.3-70b"
        self.together_model = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
        self.gemini_model = "gemini-2.0-flash"
    
    def build_prompt(self, topic: str, agent_name: str = None) -> str:
        """Build deep analysis prompt."""
        
        memory_context = get_context_for_prompt(topic, agent_name=agent_name or self.NAME)
        
        # Get strategic research data
        web_results = search_web(f"{topic} why fails strategic analysis")
        github_results = search_github_issues(f"{topic} problem")
        
        all_results = web_results + github_results
        web_context = format_search_results(all_results)
        
        return f"""You are a DEEP DIVER — a strategic analyst who finds what others miss by thinking from first principles.

{memory_context}

═══════════════════════════════════════════════════════════════════
RESEARCH DATA FOR DEEP ANALYSIS:
═══════════════════════════════════════════════════════════════════
{web_context}

═══════════════════════════════════════════════════════════════════
DEEP DIVE MISSION: {topic}
═══════════════════════════════════════════════════════════════════

Think step by step. Analyze deeply. Produce analysis in this EXACT format:

## 🔬 ROOT CAUSE ANALYSIS
[Why does this problem actually exist? Go 5 levels deep (5 Whys)]
Level 1: Surface problem...
Level 2: Because...
Level 3: Because...
Level 4: Because...
Level 5: Root cause...

## 🔍 WHAT PREVIOUS RESEARCH MISSED
[What angle hasn't been explored in the knowledge base above?]
[What assumptions are everyone making that might be wrong?]

## 🎯 HIDDEN OPPORTUNITIES
[Identify 2-3 opportunities from combining pain points in new ways]
[For each: specific opportunity, why it's hidden, evidence]

## 💀 WHY CURRENT SOLUTIONS REALLY FAIL
[Structural reasons incumbents can't fix this]
[Include: business model constraints, technical debt, incentive misalignment]

## ⚔️ UNFAIR ADVANTAGE NEEDED
[What would give a new entrant an uncopyable edge?]
[Consider: technology, distribution, data, network effects]

## 🎭 3 CONTRARIAN TAKES
[What does everyone believe that's actually wrong?]
1. Consensus view: X → Actually: Y (because...)
2. Consensus view: X → Actually: Y (because...)
3. Consensus view: X → Actually: Y (because...)

## 🛠️ MVP CONCEPT
[Simplest possible product to test the hypothesis]
- Core feature (ONE thing):
- Target user (specific):
- Success metric:
- Build time estimate:
- Why this beats existing solutions:

## 🧠 STRATEGIC VERDICT
[What's the one non-obvious insight that changes everything?]

QUALITY REQUIREMENTS:
- Think from first principles, not analogies
- Challenge obvious assumptions
- Find structural advantages, not feature improvements
- Be specific about why existing players can't just copy this
"""
    
    def _call_openrouter(self, prompt: str, model: str, provider_name: str) -> dict:
        """Call OpenRouter API with multiple keys."""
        
        keys = [k for k in [self.openrouter_key, self.openrouter_key_2, self.openrouter_key_3] if k]
        
        if not keys:
            return {"success": False, "error": "No OpenRouter keys", "provider": provider_name}
        
        import requests
        
        for i, key in enumerate(keys):
            try:
                log_debug(self.NAME, f"Trying OpenRouter key {i+1} with {model}...")
                
                resp = requests.post(
                    self.openrouter_endpoint,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://agent-research-hub.local",
                        "X-Title": "Deep Diver Agent"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "Deep strategic analyst. Think step by step. Be rigorous and specific."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 2000,
                        "temperature": 0.5
                    },
                    timeout=60
                )
                
                if resp.status_code == 429:
                    log_debug(self.NAME, f"OpenRouter key {i+1} rate limited")
                    continue
                
                if resp.status_code != 200:
                    log_debug(self.NAME, f"OpenRouter key {i+1} failed: HTTP {resp.status_code}")
                    continue
                
                data = resp.json()
                if "choices" not in data:
                    continue
                
                text = data["choices"][0]["message"]["content"]
                log_api_call(self.NAME, f"OpenRouter-{model.split('/')[-1]}", True)
                return {"success": True, "text": text, "provider": provider_name}
                
            except Exception as e:
                log_debug(self.NAME, f"OpenRouter key {i+1} error: {e}")
                continue
        
        return {"success": False, "rate_limited": True, "provider": provider_name}
    
    def call_api(self, prompt: str) -> dict:
        """Call AI API with reasoning model priority."""
        
        system_msg = "Deep strategic analyst. Think step by step. Be rigorous and specific."
        
        # 1. Try Nemotron (primary - good at reasoning)
        log_debug(self.NAME, "Trying Nemotron...")
        result = self._call_openrouter(prompt, self.primary_model, "nemotron")
        if result.get("success"):
            return result
        log_api_call(self.NAME, "Nemotron", False)
        
        # 2. Try QwQ via OpenRouter
        log_debug(self.NAME, "Trying QwQ (OpenRouter)...")
        result = self._call_openrouter(prompt, self.qwq_model, "qwq-openrouter")
        if result.get("success"):
            return result
        log_api_call(self.NAME, "QwQ-OpenRouter", False)
        
        # 3. Try QwQ via Groq
        if self.groq_key:
            log_debug(self.NAME, "Trying QwQ (Groq)...")
            result = self._call_openai_compatible(
                prompt, self.groq_endpoint, self.groq_key,
                self.groq_model, "qwq-groq", system_msg, max_tokens=2000
            )
            if result["success"]:
                log_api_call(self.NAME, "QwQ-Groq", True)
                return result
            log_api_call(self.NAME, "QwQ-Groq", False)
        
        # 4. Try Together AI
        if self.together_key:
            log_debug(self.NAME, "Trying Together AI...")
            result = self._call_openai_compatible(
                prompt, self.together_endpoint, self.together_key,
                self.together_model, "together", system_msg, max_tokens=2000
            )
            if result["success"]:
                log_api_call(self.NAME, "Together", True)
                return result
            log_api_call(self.NAME, "Together", False)
        
        # 5. Try Cerebras
        if self.cerebras_key:
            log_debug(self.NAME, "Trying Cerebras...")
            result = self._call_openai_compatible(
                prompt, self.cerebras_endpoint, self.cerebras_key,
                self.cerebras_model, "cerebras", system_msg, max_tokens=2000
            )
            if result["success"]:
                log_api_call(self.NAME, "Cerebras", True)
                return result
            log_api_call(self.NAME, "Cerebras", False)
        
        # 6. Try Gemini
        if self.gemini_key:
            log_debug(self.NAME, "Trying Gemini...")
            result = self._call_gemini(prompt, self.gemini_key, self.gemini_model, max_tokens=2000)
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
