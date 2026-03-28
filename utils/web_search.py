"""
Web Search utility — Real Google results via Serper + Jina fallback
Priority: Serper (Google) → Jina → Reddit → DuckDuckGo
"""

import os
import requests
import json
from utils.logger import log

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
JINA_API_KEY = os.getenv("JINA_API_KEY", "")


def search_serper(query: str, max_results: int = 5) -> list:
    """Search Google via Serper API — 2,500 free searches/month."""
    if not SERPER_API_KEY:
        return []
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json"
            },
            json={"q": query, "num": max_results},
            timeout=10
        )
        if resp.status_code != 200:
            log("web_search", f"Serper failed: HTTP {resp.status_code}")
            return []
        data = resp.json()
        results = []

        # Organic results
        for r in data.get("organic", [])[:max_results]:
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("snippet", ""),
                "url": r.get("link", "")
            })

        # Knowledge graph if available
        kg = data.get("knowledgeGraph", {})
        if kg.get("description"):
            results.insert(0, {
                "title": kg.get("title", ""),
                "snippet": kg.get("description", ""),
                "url": kg.get("website", "")
            })

        log("web_search", f"Serper returned {len(results)} results for: {query[:50]}")
        return results[:max_results]
    except Exception as e:
        log("web_search", f"Serper error: {e}")
        return []


def search_jina(query: str, max_results: int = 5) -> list:
    """Search using Jina AI — free fallback."""
    if not JINA_API_KEY:
        return []
    try:
        resp = requests.get(
            f"https://s.jina.ai/{requests.utils.quote(query)}",
            headers={
                "Authorization": f"Bearer {JINA_API_KEY}",
                "Accept": "application/json"
            },
            timeout=15
        )
        if resp.status_code != 200:
            log("web_search", f"Jina failed: HTTP {resp.status_code}")
            return []
        data = resp.json()
        results = []
        for r in data.get("data", [])[:max_results]:
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("description", "") or r.get("content", "")[:300],
                "url": r.get("url", "")
            })
        log("web_search", f"Jina returned {len(results)} results for: {query[:50]}")
        return results[:max_results]
    except Exception as e:
        log("web_search", f"Jina error: {e}")
        return []


def search_duckduckgo(query: str, max_results: int = 5) -> list:
    """DuckDuckGo last resort fallback."""
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        data = resp.json()
        results = []
        if data.get("Abstract"):
            results.append({
                "title": data.get("Heading", ""),
                "snippet": data["Abstract"],
                "url": data.get("AbstractURL", "")
            })
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "")[:100],
                    "snippet": topic.get("Text", ""),
                    "url": topic.get("FirstURL", "")
                })
        return results[:max_results]
    except Exception as e:
        log("web_search", f"DuckDuckGo error: {e}")
        return []


def search_reddit(topic: str) -> list:
    """Search Reddit for real user discussions."""
    try:
        resp = requests.get(
            "https://www.reddit.com/search.json",
            params={"q": topic, "sort": "relevance", "t": "year", "limit": 5},
            headers={"User-Agent": "ResearchBot/1.0"},
            timeout=10
        )
        data = resp.json()
        results = []
        for post in data.get("data", {}).get("children", []):
            p = post.get("data", {})
            results.append({
                "title": p.get("title", ""),
                "snippet": p.get("selftext", "")[:300] or p.get("title", ""),
                "url": f"https://reddit.com{p.get('permalink', '')}",
                "score": p.get("score", 0),
                "subreddit": p.get("subreddit", "")
            })
        log("web_search", f"Reddit returned {len(results)} results")
        return results
    except Exception as e:
        log("web_search", f"Reddit error: {e}")
        return []


def search_web(query: str, max_results: int = 5) -> list:
    """
    Main search function — tries best sources in order:
    1. Serper (real Google results)
    2. Jina AI
    3. DuckDuckGo
    """
    # Try Serper first (best quality)
    results = search_serper(query, max_results)
    if results:
        return results

    # Try Jina fallback
    log("web_search", "Serper failed, trying Jina...")
    results = search_jina(query, max_results)
    if results:
        return results

    # DuckDuckGo last resort
    log("web_search", "Jina failed, trying DuckDuckGo...")
    return search_duckduckgo(query, max_results)


def format_search_results(results: list) -> str:
    """Format search results for injection into agent prompts."""
    if not results:
        return "No web results found."

    formatted = []
    for r in results:
        title = r.get("title", "")[:100]
        snippet = r.get("snippet", "")[:300]
        url = r.get("url", "")
        subreddit = r.get("subreddit", "")

        if subreddit:
            formatted.append(f"• [Reddit r/{subreddit}] {title}\n  {snippet}")
        else:
            formatted.append(f"• {title}\n  {snippet}\n  Source: {url}")

    return "\n\n".join(formatted)
