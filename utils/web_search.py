"""
WEB SEARCH v4 — multi-source search that tells you when a source is dead
=========================================================================
Same public functions as v3 (agents don't need changes). New:
- Failures are logged as warnings with the HTTP status/message (once per 15 min)
- A source that returns auth/credit/rate-limit errors is paused for a few hours
- Hacker News / GitHub retry with keywords when the full sentence finds nothing
- GitHub uses GITHUB_TOKEN if set (falls back to anonymous if the token is bad)
- search_comprehensive no longer crashes on a slow source
- diagnose_search() probes every source and returns a one-line report
"""

import os
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from utils.logger import log_info, log_warn, log_debug, log_error

# API Keys
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
JINA_API_KEY = os.getenv("JINA_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Cache + health tracking
_search_cache = {}
_cache_ttl = 3600  # 1 hour
_status = {}       # source -> last status string
_disabled = {}     # source -> epoch seconds until it may be tried again
_warned = {}       # warning key -> last time we logged it
_gh_token_bad = False

REDDIT_UA = "script:agent-research-hub:v4 (by /u/research_bot)"


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def _get_cached(key: str):
    if key in _search_cache:
        result, timestamp = _search_cache[key]
        if time.time() - timestamp < _cache_ttl:
            return result
    return None


def _set_cached(key: str, value):
    if not value:          # never cache empty results
        return
    _search_cache[key] = (value, time.time())
    if len(_search_cache) > 100:
        oldest = min(_search_cache, key=lambda k: _search_cache[k][1])
        del _search_cache[oldest]


def _warn_once(key: str, msg: str, every: int = 900):
    now = time.time()
    if now - _warned.get(key, 0) >= every:
        _warned[key] = now
        log_warn("web_search", msg)


def _is_disabled(source: str) -> bool:
    return _disabled.get(source, 0) > time.time()


def _disable(source: str, hours: float, why: str):
    _disabled[source] = time.time() + hours * 3600
    _warn_once(f"{source}_disabled", f"{source} paused for {hours}h — {why}", every=3600)


_STOP = set("""a an the of for and or to in on at by with from about into over than that this those these
why do does did how what when where which who is are was were be been being can could should would will
people most nobody has have had yet ever still really more less very just""".split())
_MONTHS = set("""january february march april may june july august september october november december""".split())


def _keywords(query: str, n: int = 4) -> str:
    """'most complained about productivity apps May 2026' -> 'complained productivity apps'"""
    words = re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", query.lower())
    kept = [w for w in words if w not in _STOP and w not in _MONTHS]
    return " ".join(kept[:n])


# ═══════════════════════════════════════════════════════════════════
# SERPER (Google Search) — free credits are limited, check your dashboard
# ═══════════════════════════════════════════════════════════════════

def search_serper(query: str, max_results: int = 5) -> list:
    if not SERPER_API_KEY:
        _status["serper"] = "no key"
        return []
    if _is_disabled("serper"):
        return []

    cache_key = f"serper:{query}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": max_results},
            timeout=10
        )

        if resp.status_code != 200:
            body = resp.text[:120].replace("\n", " ")
            _status["serper"] = f"HTTP {resp.status_code}: {body}"
            if resp.status_code in (400, 401, 402, 403, 429):
                _disable("serper", 6, f"HTTP {resp.status_code}: {body} (out of credits / bad key / rate limit?)")
            else:
                _warn_once("serper_http", f"Serper HTTP {resp.status_code}: {body}")
            return []

        data = resp.json()
        results = []

        kg = data.get("knowledgeGraph", {})
        if kg.get("description"):
            results.append({
                "title": kg.get("title", ""),
                "snippet": kg.get("description", ""),
                "url": kg.get("website", ""),
                "source": "google_kg"
            })

        for r in data.get("organic", [])[:max_results]:
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("snippet", ""),
                "url": r.get("link", ""),
                "source": "google"
            })

        results = results[:max_results]
        _status["serper"] = f"ok ({len(results)})" if results else "0 results"
        _set_cached(cache_key, results)
        return results

    except Exception as e:
        _status["serper"] = f"error: {e}"
        _warn_once("serper_exc", f"Serper error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
# JINA AI
# ═══════════════════════════════════════════════════════════════════

def fetch_full_content(url: str) -> str:
    """Fetch full article content using Jina Reader API."""
    if not url or not JINA_API_KEY or _is_disabled("jina"):
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
            if resp.status_code in (401, 402, 429):
                _disable("jina", 6, f"HTTP {resp.status_code} (quota/key?)")
            return ""
        return resp.text[:4000]
    except Exception as e:
        log_debug("web_search", f"Jina reader error: {e}")
        return ""


def search_jina(query: str, max_results: int = 5) -> list:
    if not JINA_API_KEY:
        _status["jina"] = "no key"
        return []
    if _is_disabled("jina"):
        return []

    cache_key = f"jina:{query}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        resp = requests.get(
            f"https://s.jina.ai/{requests.utils.quote(query)}",
            headers={"Authorization": f"Bearer {JINA_API_KEY}", "Accept": "application/json"},
            timeout=15
        )

        if resp.status_code != 200:
            body = resp.text[:120].replace("\n", " ")
            _status["jina"] = f"HTTP {resp.status_code}: {body}"
            if resp.status_code in (401, 402, 403, 429):
                _disable("jina", 6, f"HTTP {resp.status_code}: {body} (quota / bad key?)")
            else:
                _warn_once("jina_http", f"Jina HTTP {resp.status_code}: {body}")
            return []

        data = resp.json()
        results = []
        for r in data.get("data", [])[:max_results]:
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("description", "") or (r.get("content", "") or "")[:300],
                "url": r.get("url", ""),
                "source": "jina"
            })

        _status["jina"] = f"ok ({len(results)})" if results else "0 results"
        _set_cached(cache_key, results)
        return results

    except Exception as e:
        _status["jina"] = f"error: {e}"
        _warn_once("jina_exc", f"Jina search error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
# DUCKDUCKGO — instant answers only (weak for long queries)
# ═══════════════════════════════════════════════════════════════════

def search_duckduckgo(query: str, max_results: int = 5) -> list:
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1"},
            headers={"User-Agent": "Mozilla/5.0 (ResearchBot)"},
            timeout=10
        )
        data = resp.json()
        results = []

        if data.get("Abstract"):
            results.append({
                "title": data.get("Heading", ""),
                "snippet": data["Abstract"],
                "url": data.get("AbstractURL", ""),
                "source": "duckduckgo"
            })

        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "")[:100],
                    "snippet": topic.get("Text", ""),
                    "url": topic.get("FirstURL", ""),
                    "source": "duckduckgo"
                })

        results = results[:max_results]
        _status["duckduckgo"] = f"ok ({len(results)})" if results else "0 results"
        return results

    except Exception as e:
        _status["duckduckgo"] = f"error: {e}"
        log_debug("web_search", f"DuckDuckGo error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
# REDDIT — no key, but often blocked from cloud IPs
# ═══════════════════════════════════════════════════════════════════

def search_reddit(query: str, max_results: int = 5) -> list:
    if _is_disabled("reddit"):
        return []

    cache_key = f"reddit:{query}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        resp = requests.get(
            "https://www.reddit.com/search.json",
            params={"q": query, "sort": "relevance", "t": "year", "limit": max_results + 5},
            headers={"User-Agent": REDDIT_UA},
            timeout=10
        )

        if resp.status_code != 200:
            _status["reddit"] = f"HTTP {resp.status_code}"
            if resp.status_code in (403, 429):
                _disable("reddit", 2, f"HTTP {resp.status_code} (Reddit blocks many cloud/datacenter IPs)")
            else:
                _warn_once("reddit_http", f"Reddit HTTP {resp.status_code}")
            return []

        data = resp.json()
        results = []
        for post in data.get("data", {}).get("children", []):
            p = post.get("data", {})
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
        _status["reddit"] = f"ok ({len(results)})" if results else "0 results"
        _set_cached(cache_key, results)
        return results

    except Exception as e:
        _status["reddit"] = f"error: {e}"
        log_debug("web_search", f"Reddit error: {e}")
        return []


def get_reddit_comments(url: str, max_comments: int = 5) -> list:
    """Fetch top comments from a Reddit post."""
    if _is_disabled("reddit"):
        return []
    try:
        resp = requests.get(url.rstrip('/') + ".json", headers={"User-Agent": REDDIT_UA}, timeout=10)
        if resp.status_code != 200:
            return []

        data = resp.json()
        comments = []
        if len(data) > 1:
            for comment in data[1].get("data", {}).get("children", [])[:max_comments]:
                c = comment.get("data", {})
                if c.get("body") and c.get("body") != "[removed]":
                    comments.append({"text": c["body"][:400], "score": c.get("score", 0)})
        return comments
    except Exception as e:
        log_debug("web_search", f"Reddit comments error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
# HACKER NEWS — free, no key
# ═══════════════════════════════════════════════════════════════════

def search_hackernews(query: str, max_results: int = 5) -> list:
    cache_key = f"hn:{query}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    def _run(q):
        resp = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": q, "tags": "story", "hitsPerPage": max_results},
            timeout=10
        )
        if resp.status_code != 200:
            _status["hackernews"] = f"HTTP {resp.status_code}"
            return None
        return resp.json().get("hits", [])

    try:
        hits = _run(query)
        if hits is None:
            return []
        if not hits:
            kw = _keywords(query)
            if kw and kw != query.lower():
                hits = _run(kw) or []

        results = []
        for hit in hits:
            results.append({
                "title": hit.get("title", ""),
                "snippet": hit.get("title", ""),
                "url": hit.get("url", "") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                "points": hit.get("points", 0),
                "num_comments": hit.get("num_comments", 0),
                "source": "hackernews"
            })

        _status["hackernews"] = f"ok ({len(results)})" if results else "0 results"
        _set_cached(cache_key, results)
        return results

    except Exception as e:
        _status["hackernews"] = f"error: {e}"
        log_debug("web_search", f"Hacker News error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
# GITHUB ISSUES — uses GITHUB_TOKEN if set (5000/h) else anonymous (60/h)
# ═══════════════════════════════════════════════════════════════════

def search_github_issues(query: str, max_results: int = 5) -> list:
    global _gh_token_bad
    if _is_disabled("github"):
        return []

    cache_key = f"github:{query}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    def _run(q):
        global _gh_token_bad
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "ResearchBot"}
        if GITHUB_TOKEN and not _gh_token_bad:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
        params = {"q": f"{q} is:issue is:open", "sort": "comments", "order": "desc", "per_page": max_results}
        resp = requests.get("https://api.github.com/search/issues", params=params, headers=headers, timeout=10)

        if resp.status_code == 401 and "Authorization" in headers:
            _gh_token_bad = True
            _warn_once("gh_token", "GITHUB_TOKEN rejected (401) — falling back to anonymous GitHub search")
            headers.pop("Authorization")
            resp = requests.get("https://api.github.com/search/issues", params=params, headers=headers, timeout=10)

        if resp.status_code != 200:
            _status["github"] = f"HTTP {resp.status_code}"
            if resp.status_code in (403, 429):
                _disable("github", 1, f"HTTP {resp.status_code} (rate limited)")
            return None
        return resp.json().get("items", [])

    try:
        items = _run(query)
        if items is None:
            return []
        if not items:
            kw = _keywords(query)
            if kw and kw != query.lower():
                items = _run(kw) or []

        results = []
        for item in items:
            results.append({
                "title": item.get("title", ""),
                "snippet": (item.get("body", "") or "")[:400],
                "url": item.get("html_url", ""),
                "comments": item.get("comments", 0),
                "repository": item.get("repository_url", "").split("/")[-1] if item.get("repository_url") else "",
                "source": "github"
            })

        _status["github"] = f"ok ({len(results)})" if results else "0 results"
        _set_cached(cache_key, results)
        return results

    except Exception as e:
        _status["github"] = f"error: {e}"
        log_debug("web_search", f"GitHub error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
# PRODUCT HUNT — fragile scrape, kept for compatibility
# ═══════════════════════════════════════════════════════════════════

def get_producthunt_trending() -> list:
    try:
        resp = requests.get("https://www.producthunt.com/", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code != 200:
            return []

        titles = re.findall(r'data-test="post-name"[^>]*>([^<]+)', resp.text)
        taglines = re.findall(r'data-test="post-tagline"[^>]*>([^<]+)', resp.text)

        results = []
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
# MAIN SEARCH FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def search_web(query: str, max_results: int = 5, allow_hn_fallback: bool = True) -> list:
    """Serper (Google) -> Jina -> DuckDuckGo -> (last resort) Hacker News."""
    results = search_serper(query, max_results)
    if results:
        return results

    results = search_jina(query, max_results)
    if results:
        return results

    results = search_duckduckgo(query, max_results)
    if results:
        return results

    if allow_hn_fallback:
        return search_hackernews(query, max_results)
    return []


def search_comprehensive(query: str, max_per_source: int = 3) -> dict:
    """Search all sources in parallel. Returns {source_name: [results]}."""
    sources = {
        "web": lambda: search_web(query, max_per_source, allow_hn_fallback=False),
        "reddit": lambda: search_reddit(query, max_per_source),
        "hackernews": lambda: search_hackernews(query, max_per_source),
        "github": lambda: search_github_issues(query, max_per_source),
    }

    results = {name: [] for name in sources}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fn): name for name, fn in sources.items()}
        try:
            for future in as_completed(futures, timeout=20):
                name = futures[future]
                try:
                    results[name] = future.result()
                except Exception as e:
                    log_debug("web_search", f"{name} failed: {e}")
        except FuturesTimeout:
            _warn_once("search_timeout", "search_comprehensive timed out — using partial results")

    return results


def search_and_fetch(query: str, max_results: int = 3) -> list:
    """Search AND fetch full content of top results (deeper research)."""
    results = search_web(query, max_results)

    enriched = []
    for r in results:
        url = r.get("url", "")
        full_content = fetch_full_content(url) if url else ""
        enriched.append({**r, "full_content": full_content or r.get("snippet", "")})
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

        if use_full_content and r.get("full_content"):
            content = r["full_content"][:800]
        else:
            content = r.get("snippet", "")[:300]

        url = r.get("url", "")

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


# ═══════════════════════════════════════════════════════════════════
# DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════

def get_search_health() -> dict:
    now = time.time()
    return {
        "status": dict(_status),
        "paused": {k: int(v - now) for k, v in _disabled.items() if v > now},
    }


def diagnose_search(query: str = "note taking app complaints") -> str:
    """Probe every source once and return a one-line report for the logs."""
    _disabled.clear()
    _search_cache.clear()

    probes = {
        "serper": lambda: search_serper(query, 3),
        "jina": lambda: search_jina(query, 3),
        "duckduckgo": lambda: search_duckduckgo(query, 3),
        "reddit": lambda: search_reddit(query, 3),
        "hackernews": lambda: search_hackernews(query, 3),
        "github": lambda: search_github_issues(query, 3),
    }

    parts = []
    for name, fn in probes.items():
        try:
            fn()
        except Exception as e:
            _status[name] = f"error: {e}"
        parts.append(f"{name}={_status.get(name, '?')}")
    return " | ".join(parts)
