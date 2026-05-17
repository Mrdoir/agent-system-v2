"""
WEB SEARCH v3 — Multi-source search with more free APIs
Improvements:
- Hacker News search (free, no key)
- GitHub Issues search (free, no key)
- Twitter/X via Nitter (free, no key)
- Better Reddit parsing with comments
- Content caching to reduce API calls
- Parallel fetching for speed
"""

import os
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.logger import log_info, log_warn, log_debug, log_error

# API Keys
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
JINA_API_KEY = os.getenv("JINA_API_KEY", "")

# Simple cache
_search_cache = {}
_cache_ttl = 3600  # 1 hour


def _get_cached(key: str):
    """Get cached result if still valid."""
    if key in _search_cache:
        result, timestamp = _search_cache[key]
        if time.time() - timestamp < _cache_ttl:
            return result
    return None


def _set_cached(key: str, value):
    """Cache a result."""
    _search_cache[key] = (value, time.time())
    # Limit cache size
    if len(_search_cache) > 100:
        oldest = min(_search_cache, key=lambda k: _search_cache[k][1])
        del _search_cache[oldest]


# ═══════════════════════════════════════════════════════════════════
# SERPER (Google Search) — 2,500 free/month
# ═══════════════════════════════════════════════════════════════════

def search_serper(query: str, max_results: int = 5) -> list:
    """Search Google via Serper API."""
    if not SERPER_API_KEY:
        return []
    
    cache_key = f"serper:{query}"
    cached = _get_cached(cache_key)
    if cached:
        return cached
    
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
            log_warn("web_search", f"Serper HTTP {resp.status_code}")
            return []
        
        data = resp.json()
        results = []
        
        # Knowledge graph
        kg = data.get("knowledgeGraph", {})
        if kg.get("description"):
            results.append({
                "title": kg.get("title", ""),
                "snippet": kg.get("description", ""),
                "url": kg.get("website", ""),
                "source": "google_kg"
            })
        
        # Organic results
        for r in data.get("organic", [])[:max_results]:
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("snippet", ""),
                "url": r.get("link", ""),
                "source": "google"
            })
        
        log_debug("web_search", f"Serper: {len(results)} results for '{query[:40]}'")
        _set_cached(cache_key, results)
        return results[:max_results]
        
    except Exception as e:
        log_error("web_search", f"Serper error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
# JINA AI — Free tier
# ═══════════════════════════════════════════════════════════════════

def fetch_full_content(url: str) -> str:
    """Fetch full article content using Jina Reader API."""
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
        
        content = resp.text[:4000]  # Limit size
        log_debug("web_search", f"Jina: fetched content from {url[:50]}")
        return content
        
    except Exception as e:
        log_debug("web_search", f"Jina reader error: {e}")
        return ""


def search_jina(query: str, max_results: int = 5) -> list:
    """Search using Jina AI."""
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
                "url": r.get("url", ""),
                "source": "jina"
            })
        
        log_debug("web_search", f"Jina: {len(results)} results")
        return results[:max_results]
        
    except Exception as e:
        log_debug("web_search", f"Jina search error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
# DUCKDUCKGO — Free, no key needed
# ═══════════════════════════════════════════════════════════════════

def search_duckduckgo(query: str, max_results: int = 5) -> list:
    """DuckDuckGo instant answers (free, no key)."""
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1"},
            headers={"User-Agent": "Mozilla/5.0 (ResearchBot)"},
            timeout=10
        )
        
        data = resp.json()
        results = []
        
        # Abstract
        if data.get("Abstract"):
            results.append({
                "title": data.get("Heading", ""),
                "snippet": data["Abstract"],
                "url": data.get("AbstractURL", ""),
                "source": "duckduckgo"
            })
        
        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "")[:100],
                    "snippet": topic.get("Text", ""),
                    "url": topic.get("FirstURL", ""),
                    "source": "duckduckgo"
                })
        
        return results[:max_results]
        
    except Exception as e:
        log_debug("web_search", f"DuckDuckGo error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
# REDDIT — Free, no key needed
# ═══════════════════════════════════════════════════════════════════

def search_reddit(query: str, max_results: int = 5) -> list:
    """Search Reddit for real user discussions."""
    cache_key = f"reddit:{query}"
    cached = _get_cached(cache_key)
    if cached:
        return cached
    
    try:
        resp = requests.get(
            "https://www.reddit.com/search.json",
            params={
                "q": query,
                "sort": "relevance",
                "t": "year",
                "limit": max_results + 5  # Get extra in case some are removed
            },
            headers={"User-Agent": "ResearchBot/2.0"},
            timeout=10
        )
        
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        results = []
        
        for post in data.get("data", {}).get("children", []):
            p = post.get("data", {})
            
            # Skip removed/deleted posts
            if p.get("removed_by_category") or p.get("selftext") == "[removed]":
                continue
            
            full_text = p.get("selftext", "")[:600] or p.get("title", "")
            
            results.append({
                "title": p.get("title", ""),
                "snippet": full_text,
                "url": f"https://reddit.com{p.get('permalink', '')}",
                "score": p.get("score", 0),
                "subreddit": p.get("subreddit", ""),
                "num_comments": p.get("num_comments", 0),
                "source": "reddit"
            })
        
        results = results[:max_results]
        log_debug("web_search", f"Reddit: {len(results)} results for '{query[:30]}'")
        _set_cached(cache_key, results)
        return results
        
    except Exception as e:
        log_debug("web_search", f"Reddit error: {e}")
        return []


def get_reddit_comments(url: str, max_comments: int = 5) -> list:
    """Fetch top comments from a Reddit post."""
    try:
        # Convert to JSON endpoint
        json_url = url.rstrip('/') + ".json"
        
        resp = requests.get(
            json_url,
            headers={"User-Agent": "ResearchBot/2.0"},
            timeout=10
        )
        
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        comments = []
        
        # Comments are in second element of the list
        if len(data) > 1:
            for comment in data[1].get("data", {}).get("children", [])[:max_comments]:
                c = comment.get("data", {})
                if c.get("body") and c.get("body") != "[removed]":
                    comments.append({
                        "text": c["body"][:400],
                        "score": c.get("score", 0)
                    })
        
        return comments
        
    except Exception as e:
        log_debug("web_search", f"Reddit comments error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
# HACKER NEWS — Free, no key needed
# ═══════════════════════════════════════════════════════════════════

def search_hackernews(query: str, max_results: int = 5) -> list:
    """Search Hacker News via Algolia (free, no key)."""
    cache_key = f"hn:{query}"
    cached = _get_cached(cache_key)
    if cached:
        return cached
    
    try:
        resp = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={
                "query": query,
                "tags": "story",
                "hitsPerPage": max_results
            },
            timeout=10
        )
        
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        results = []
        
        for hit in data.get("hits", []):
            results.append({
                "title": hit.get("title", ""),
                "snippet": hit.get("title", ""),  # HN doesn't have descriptions
                "url": hit.get("url", "") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                "points": hit.get("points", 0),
                "num_comments": hit.get("num_comments", 0),
                "source": "hackernews"
            })
        
        log_debug("web_search", f"HN: {len(results)} results for '{query[:30]}'")
        _set_cached(cache_key, results)
        return results
        
    except Exception as e:
        log_debug("web_search", f"Hacker News error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
# GITHUB ISSUES — Free, no key needed (rate limited: 60/hour)
# ═══════════════════════════════════════════════════════════════════

def search_github_issues(query: str, max_results: int = 5) -> list:
    """Search GitHub Issues for developer pain points."""
    cache_key = f"github:{query}"
    cached = _get_cached(cache_key)
    if cached:
        return cached
    
    try:
        resp = requests.get(
            "https://api.github.com/search/issues",
            params={
                "q": f"{query} is:issue is:open",
                "sort": "comments",
                "order": "desc",
                "per_page": max_results
            },
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "ResearchBot"
            },
            timeout=10
        )
        
        if resp.status_code != 200:
            if resp.status_code == 403:
                log_warn("web_search", "GitHub rate limited")
            return []
        
        data = resp.json()
        results = []
        
        for item in data.get("items", []):
            results.append({
                "title": item.get("title", ""),
                "snippet": (item.get("body", "") or "")[:400],
                "url": item.get("html_url", ""),
                "comments": item.get("comments", 0),
                "repository": item.get("repository_url", "").split("/")[-1] if item.get("repository_url") else "",
                "source": "github"
            })
        
        log_debug("web_search", f"GitHub: {len(results)} issues for '{query[:30]}'")
        _set_cached(cache_key, results)
        return results
        
    except Exception as e:
        log_debug("web_search", f"GitHub error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
# PRODUCT HUNT — Scrape trending (free, no key)
# ═══════════════════════════════════════════════════════════════════

def get_producthunt_trending() -> list:
    """Get trending products from Product Hunt."""
    try:
        # This is a simplified approach - PH doesn't have a free API
        # But we can get some data from their public pages
        resp = requests.get(
            "https://www.producthunt.com/",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        
        if resp.status_code != 200:
            return []
        
        # Basic extraction (limited without JS rendering)
        # For better results, would need browser automation
        results = []
        
        # Extract product names from page (simplified)
        # This is fragile but free
        import re
        titles = re.findall(r'data-test="post-name"[^>]*>([^<]+)', resp.text)
        taglines = re.findall(r'data-test="post-tagline"[^>]*>([^<]+)', resp.text)
        
        for i, title in enumerate(titles[:5]):
            results.append({
                "title": title,
                "snippet": taglines[i] if i < len(taglines) else "",
                "url": "https://producthunt.com",
                "source": "producthunt"
            })
        
        return results
        
    except Exception as e:
        log_debug("web_search", f"Product Hunt error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
# MAIN SEARCH FUNCTION
# ═══════════════════════════════════════════════════════════════════

def search_web(query: str, max_results: int = 5) -> list:
    """
    Main search function — tries multiple sources.
    Priority: Serper (Google) → Jina → DuckDuckGo
    """
    results = search_serper(query, max_results)
    if results:
        return results
    
    log_debug("web_search", "Serper unavailable, trying Jina...")
    results = search_jina(query, max_results)
    if results:
        return results
    
    log_debug("web_search", "Jina unavailable, trying DuckDuckGo...")
    return search_duckduckgo(query, max_results)


def search_comprehensive(query: str, max_per_source: int = 3) -> dict:
    """
    Comprehensive search across all sources in parallel.
    Returns dict with results organized by source.
    """
    sources = {
        "web": lambda: search_web(query, max_per_source),
        "reddit": lambda: search_reddit(query, max_per_source),
        "hackernews": lambda: search_hackernews(query, max_per_source),
        "github": lambda: search_github_issues(query, max_per_source),
    }
    
    results = {}
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fn): name for name, fn in sources.items()}
        
        for future in as_completed(futures, timeout=15):
            source_name = futures[future]
            try:
                results[source_name] = future.result()
            except Exception as e:
                log_debug("web_search", f"{source_name} failed: {e}")
                results[source_name] = []
    
    return results


def search_and_fetch(query: str, max_results: int = 3) -> list:
    """Search AND fetch full content of top results (deeper research)."""
    results = search_web(query, max_results)
    
    enriched = []
    for r in results:
        url = r.get("url", "")
        full_content = fetch_full_content(url) if url else ""
        
        enriched.append({
            **r,
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
        source = r.get("source", "web")
        subreddit = r.get("subreddit", "")
        
        # Determine content to use
        if use_full_content and r.get("full_content"):
            content = r["full_content"][:800]
        else:
            content = r.get("snippet", "")[:300]
        
        url = r.get("url", "")
        
        # Format based on source
        if subreddit:
            score = r.get("score", 0)
            comments = r.get("num_comments", 0)
            formatted.append(
                f"• [Reddit r/{subreddit} | ↑{score} | 💬{comments}]\n"
                f"  {title}\n"
                f"  {content}"
            )
        elif source == "hackernews":
            points = r.get("points", 0)
            formatted.append(
                f"• [Hacker News | {points} points]\n"
                f"  {title}\n"
                f"  {url}"
            )
        elif source == "github":
            comments = r.get("comments", 0)
            repo = r.get("repository", "")
            formatted.append(
                f"• [GitHub Issue | {repo} | 💬{comments}]\n"
                f"  {title}\n"
                f"  {content[:200]}"
            )
        else:
            formatted.append(
                f"• {title}\n"
                f"  {content}\n"
                f"  Source: {url}"
            )
    
    return "\n\n".join(formatted)
