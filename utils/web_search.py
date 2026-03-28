"""
Web Search utility — Real Google results via Serper + full content via Jina
Priority: Serper (Google) → Jina Search → DuckDuckGo
Full article reading via Jina Reader API
"""

import os
import requests
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

        kg = data.get("knowledgeGraph", {})
        if kg.get("description"):
            results.append({
                "title": kg.get("title", ""),
                "snippet": kg.get("description", ""),
                "url": kg.get("website", "")
            })

        for r in data.get("organic", [])[:max_results]:
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("snippet", ""),
                "url": r.get("link", "")
            })

        log("web_search", f"Serper returned {len(results)} results for: {query[:50]}")
        return results[:max_results]
    except Exception as e:
        log("web_search", f"Serper error: {e}")
        return []


def fetch_full_content(url: str) -> str:
    """
    Fetch full article content using Jina Reader API.
    Turns any URL into clean readable text.
    """
    if not url or not JINA_API_KEY:
        return ""
    try:
        resp = requests.get(
            f"https://r.jina.ai/{url}",
            headers={
                "Authorization": f"Bearer {JINA_API_KEY}",
                "Accept": "text/plain",
                "X-Return-Format": "text"
            },
            timeout=15
        )
        if resp.status_code != 200:
            return ""
        content = resp.text[:3000]  # First 3000 chars is enough
        log("web_search", f"Fetched full content from: {url[:60]}")
        return content
    except Exception as e:
        log("web_search", f"Jina reader error: {e}")
        return ""


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
            return []
        data = resp.json()
        results = []
        for r in data.get("data", [])[:max_results]:
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("description", "") or r.get("content", "")[:300],
                "url": r.get("url", "")
            })
        log("web_search", f"Jina returned {len(results)} results")
        return results[:max_results]
    except Exception as e:
        log("web_search", f"Jina search error: {e}")
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
    """Search Reddit for real user discussions — fetches full post content."""
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
            # Get full post text if available
            full_text = p.get("selftext", "")[:500] or p.get("title", "")
            results.append({
                "title": p.get("title", ""),
                "snippet": full_text,
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
    Main search — tries best sources in order:
    1. Serper (real Google results)
    2. Jina AI search
    3. DuckDuckGo
    """
    results = search_serper(query, max_results)
    if results:
        return results

    log("web_search", "Serper failed, trying Jina...")
    results = search_jina(query, max_results)
    if results:
        return results

    log("web_search", "Jina failed, trying DuckDuckGo...")
    return search_duckduckgo(query, max_results)


def search_and_fetch(query: str, max_results: int = 3) -> list:
    """
    Search AND fetch full content of top results.
    Returns results with full article text — much deeper than snippets!
    """
    results = search_web(query, max_results)

    enriched = []
    for r in results:
        url = r.get("url", "")
        full_content = fetch_full_content(url) if url else ""

        enriched.append({
            "title": r.get("title", ""),
            "snippet": r.get("snippet", ""),
            "url": url,
            "full_content": full_content or r.get("snippet", "")
        })

    return enriched


def format_search_results(results: list, use_full_content: bool = False) -> str:
    """Format search results for injection into agent prompts."""
    if not results:
        return "No web results found."

    formatted = []
    for r in results:
        title = r.get("title", "")[:100]
        subreddit = r.get("subreddit", "")

        # Use full content if available, otherwise snippet
        if use_full_content and r.get("full_content"):
            content = r["full_content"][:800]
        else:
            content = r.get("snippet", "")[:300]

        url = r.get("url", "")

        if subreddit:
            formatted.append(f"• [Reddit r/{subreddit}] {title}\n  {content}")
        else:
            formatted.append(f"• {title}\n  {content}\n  Source: {url}")

    return "\n\n".join(formatted)
