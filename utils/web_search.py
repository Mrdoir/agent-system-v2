"""
Web Search utility using DuckDuckGo (free, no API key needed)
Gives agents access to real current data from the web
"""

import requests
import json
from utils.logger import log


def search_web(query: str, max_results: int = 5) -> list:
    """
    Search the web using DuckDuckGo instant answer API.
    Returns list of {"title": str, "snippet": str, "url": str}
    """
    try:
        # DuckDuckGo HTML search (free, no key needed)
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"
        }
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1"
        }
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params=params,
            headers=headers,
            timeout=10
        )
        data = resp.json()

        results = []

        # Abstract (main result)
        if data.get("Abstract"):
            results.append({
                "title": data.get("Heading", ""),
                "snippet": data["Abstract"],
                "url": data.get("AbstractURL", "")
            })

        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "")[:100],
                    "snippet": topic.get("Text", ""),
                    "url": topic.get("FirstURL", "")
                })

        return results[:max_results]

    except Exception as e:
        log("web_search", f"DuckDuckGo search failed: {e}")
        return []


def search_reddit(topic: str) -> list:
    """Search Reddit for real user complaints and discussions."""
    try:
        query = f"{topic} site:reddit.com"
        headers = {"User-Agent": "ResearchBot/1.0"}
        params = {
            "q": topic,
            "sort": "relevance",
            "t": "year",
            "limit": 5,
            "type": "link"
        }
        resp = requests.get(
            "https://www.reddit.com/search.json",
            params=params,
            headers=headers,
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
        return results
    except Exception as e:
        log("web_search", f"Reddit search failed: {e}")
        return []


def format_search_results(results: list) -> str:
    """Format search results for injection into agent prompts."""
    if not results:
        return "No web results found."
    
    formatted = []
    for r in results:
        formatted.append(f"• {r.get('title', '')[:100]}\n  {r.get('snippet', '')[:200]}")
    
    return "\n\n".join(formatted)
