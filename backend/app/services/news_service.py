import httpx
import json
import re
from app.core.config import settings
from app.core.redis import cache_get, cache_set

# Financial sentiment lexicon — weighted scores
BULL_WORDS = {
    "surge": 2, "surged": 2, "soar": 2, "soared": 2, "rally": 2, "rallied": 2,
    "beat": 1.5, "beats": 1.5, "outperform": 1.5, "upgrade": 1.5, "upgraded": 1.5,
    "gain": 1, "gains": 1, "rise": 1, "rises": 1, "rose": 1, "up": 0.5,
    "growth": 1, "profit": 1.5, "profits": 1.5, "revenue": 0.5, "strong": 1,
    "bull": 1.5, "bullish": 1.5, "buy": 1, "positive": 1, "record": 1.5,
    "high": 0.5, "higher": 0.5, "boost": 1, "boosted": 1, "jump": 1.5,
    "jumped": 1.5, "breakout": 2, "momentum": 1, "opportunity": 1,
}
BEAR_WORDS = {
    "crash": 2, "crashed": 2, "plunge": 2, "plunged": 2, "collapse": 2,
    "fall": 1, "falls": 1, "fell": 1, "drop": 1, "drops": 1, "dropped": 1,
    "loss": 1.5, "losses": 1.5, "miss": 1.5, "misses": 1.5, "missed": 1.5,
    "downgrade": 1.5, "downgraded": 1.5, "weak": 1, "weakness": 1,
    "bear": 1.5, "bearish": 1.5, "sell": 1, "negative": 1, "low": 0.5,
    "lower": 0.5, "decline": 1, "declined": 1, "risk": 0.5, "concern": 0.5,
    "warning": 1.5, "layoff": 1.5, "layoffs": 1.5, "lawsuit": 1, "fraud": 2,
    "investigation": 1, "recall": 1, "debt": 0.5, "bankrupt": 2,
}


def _score_text(text: str) -> tuple[float, str]:
    """Return (score -1..1, label) for a piece of text."""
    words = re.findall(r"\b\w+\b", text.lower())
    bull = sum(BULL_WORDS.get(w, 0) for w in words)
    bear = sum(BEAR_WORDS.get(w, 0) for w in words)
    total = bull + bear
    if total == 0:
        return 0.0, "neutral"
    score = (bull - bear) / total
    label = "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral"
    return round(score, 3), label


def _format_articles(articles: list, page_size: int) -> list[dict]:
    """Normalize and score a list of raw article dicts."""
    results = []
    for a in articles[:page_size]:
        title       = a.get("title") or ""
        description = a.get("description") or ""
        # skip removed/deleted articles
        if title in ("[Removed]", "") or not title:
            continue
        score, label = _score_text(f"{title} {description}")
        results.append({
            "title":           title,
            "description":     description,
            "url":             a.get("url"),
            "source":          a.get("source", {}).get("name") if isinstance(a.get("source"), dict) else a.get("source"),
            "published_at":    a.get("publishedAt") or a.get("published_at"),
            "image":           a.get("urlToImage") or a.get("image"),
            "sentiment":       label,
            "sentiment_score": score,
        })
    return results


async def _fetch_newsapi(query: str, page_size: int) -> list[dict]:
    """Fetch from NewsAPI /v2/everything — works with valid API key."""
    if not settings.NEWS_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q":        query,
                    "pageSize": min(page_size, 100),
                    "sortBy":   "publishedAt",
                    "language": "en",
                },
                headers={"X-Api-Key": settings.NEWS_API_KEY},
            )
        body = resp.json()
        if resp.status_code != 200 or body.get("status") != "ok":
            return []
        return body.get("articles", [])
    except Exception:
        return []


async def _fetch_newsapi_headlines(query: str, page_size: int) -> list[dict]:
    """Fallback: NewsAPI /v2/top-headlines (works on free tier from any host)."""
    if not settings.NEWS_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://newsapi.org/v2/top-headlines",
                params={
                    "q":        query,
                    "pageSize": min(page_size, 100),
                    "language": "en",
                    "category": "business",
                },
                headers={"X-Api-Key": settings.NEWS_API_KEY},
            )
        body = resp.json()
        if resp.status_code != 200 or body.get("status") != "ok":
            return []
        return body.get("articles", [])
    except Exception:
        return []


async def _fetch_gnews(query: str, page_size: int) -> list[dict]:
    """GNews free API — no key needed, good fallback for dev."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://gnews.io/api/v4/search",
                params={
                    "q":        query,
                    "max":      min(page_size, 10),
                    "lang":     "en",
                    "topic":    "business",
                    "apikey":   "free",   # GNews free tier
                },
            )
        if resp.status_code != 200:
            return []
        articles = resp.json().get("articles", [])
        # Normalize GNews schema to NewsAPI schema
        return [{
            "title":       a.get("title"),
            "description": a.get("description"),
            "url":         a.get("url"),
            "source":      {"name": a.get("source", {}).get("name", "")},
            "publishedAt": a.get("publishedAt"),
            "urlToImage":  a.get("image"),
        } for a in articles]
    except Exception:
        return []


async def get_news(query: str = "stock market", page_size: int = 20) -> list[dict]:
    cache_key = f"news:{query}:{page_size}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    # Try /everything first, fall back to /top-headlines, then GNews
    raw = await _fetch_newsapi(query, page_size)
    if not raw:
        raw = await _fetch_newsapi_headlines(query, page_size)
    if not raw:
        raw = await _fetch_gnews(query, page_size)

    results = _format_articles(raw, page_size)

    if results:
        await cache_set(cache_key, json.dumps(results), ttl=1800)
    return results


async def get_symbol_sentiment(symbol: str) -> dict:
    """Aggregate sentiment score for a symbol from recent news."""
    cache_key = f"sentiment:{symbol}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    empty_result = {
        "symbol": symbol, "score": 0.0, "label": "neutral",
        "article_count": 0, "recent_headlines": [],
    }

    articles = await get_news(symbol, page_size=20)
    if not articles:
        await cache_set(cache_key, json.dumps(empty_result), ttl=1800)
        return empty_result

    scores    = [a["sentiment_score"] for a in articles]
    avg_score = round(sum(scores) / len(scores), 3)
    label     = "positive" if avg_score > 0.1 else "negative" if avg_score < -0.1 else "neutral"

    result = {
        "symbol":           symbol,
        "score":            avg_score,
        "label":            label,
        "article_count":    len(articles),
        "recent_headlines": [a["title"] for a in articles[:3]],
    }
    await cache_set(cache_key, json.dumps(result), ttl=1800)
    return result
