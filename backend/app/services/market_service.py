"""
market_service.py
-----------------
Data sources (in priority order):
  1. Yahoo Finance v8 API  — direct HTTP, no library dependency, always works
  2. Alpha Vantage          — fallback for quotes/history

Redis caching: quotes=2min, history=5min, indices=1min, movers=1min
"""

import json
import math
import asyncio
import httpx
from datetime import datetime, timezone
from app.core.redis import cache_get, cache_set
from app.core.config import settings

_AV_BASE  = "https://www.alphavantage.co/query"
_YF_BASE  = "https://query1.finance.yahoo.com/v8/finance/chart"
_YF_BASE2 = "https://query2.finance.yahoo.com/v8/finance/chart"
_HEADERS  = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}
_av_semaphore = asyncio.Semaphore(2)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _safe_float(v, decimals: int = 2):
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, decimals)
    except Exception:
        return None


def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def _fmt_volume(v) -> int:
    try:
        return 0 if (v is None or (isinstance(v, float) and math.isnan(v))) else int(v)
    except Exception:
        return 0


# ── Yahoo Finance v8 direct HTTP ───────────────────────────────────────────────

async def _yf_chart(symbol: str, period: str = "5d", interval: str = "1d") -> dict | None:
    """Fetch raw Yahoo Finance chart JSON. Tries query1 then query2."""
    yf_sym = symbol.replace(".", "-")
    params = {
        "range": period,
        "interval": interval,
        "includePrePost": "false",
        "events": "div,splits",
    }
    for base in (_YF_BASE, _YF_BASE2):
        try:
            async with httpx.AsyncClient(timeout=10, headers=_HEADERS) as client:
                r = await client.get(f"{base}/{yf_sym}", params=params)
            if r.status_code == 200:
                data = r.json()
                result = data.get("chart", {}).get("result")
                if result:
                    return result[0]
        except Exception:
            continue
    return None


async def _yf_quote(symbol: str) -> dict | None:
    """Single quote via Yahoo Finance v8."""
    chart = await _yf_chart(symbol, period="5d", interval="1d")
    if not chart:
        return None
    try:
        meta  = chart["meta"]
        price = _safe_float(meta.get("regularMarketPrice"))
        if not price:
            return None
        prev  = _safe_float(meta.get("chartPreviousClose") or meta.get("previousClose")) or price
        chg   = round(price - prev, 2)
        chgp  = round(chg / prev * 100, 2) if prev else 0.0
        return _sanitize({
            "symbol":     symbol,
            "price":      price,
            "change":     chg,
            "change_pct": chgp,
            "volume":     _fmt_volume(meta.get("regularMarketVolume")),
            "market_cap": None,
            "high":       _safe_float(meta.get("regularMarketDayHigh")),
            "low":        _safe_float(meta.get("regularMarketDayLow")),
            "open":       _safe_float(meta.get("regularMarketOpen")),
            "prev_close": prev,
            "source":     "yahoo",
            "currency":   meta.get("currency", "USD"),
        })
    except Exception:
        return None


async def _yf_history_direct(symbol: str, period: str, interval: str) -> list[dict]:
    """Historical OHLCV via Yahoo Finance v8."""
    period_map = {"1w": "5d", "1W": "5d", "1m": "1mo", "1M": "1mo", "1Y": "1y", "5Y": "5y"}
    yf_period = period_map.get(period, period)
    chart = await _yf_chart(symbol, period=yf_period, interval=interval)
    if not chart:
        return []
    try:
        timestamps = chart.get("timestamp", [])
        indicators = chart.get("indicators", {})
        quote_data = indicators.get("quote", [{}])[0]
        opens   = quote_data.get("open",   [])
        highs   = quote_data.get("high",   [])
        lows    = quote_data.get("low",    [])
        closes  = quote_data.get("close",  [])
        volumes = quote_data.get("volume", [])
        adj = indicators.get("adjclose", [{}])
        adjcloses = adj[0].get("adjclose", []) if adj else []

        records = []
        for i, ts in enumerate(timestamps):
            try:
                raw_c = (adjcloses[i] if adjcloses and i < len(adjcloses) else None) or (closes[i] if i < len(closes) else None)
                c = _safe_float(raw_c, 4)
                o = _safe_float(opens[i]   if i < len(opens)   else None, 4)
                h = _safe_float(highs[i]   if i < len(highs)   else None, 4)
                l = _safe_float(lows[i]    if i < len(lows)    else None, 4)
                v = _fmt_volume(volumes[i] if i < len(volumes) else None)
                if None in (o, h, l, c):
                    continue
                dt = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                records.append({"date": dt, "open": o, "high": h, "low": l, "close": c, "volume": v})
            except Exception:
                continue
        return records
    except Exception:
        return []


async def _yf_index_direct(ticker_sym: str) -> dict | None:
    """Index quote via Yahoo Finance v8."""
    chart = await _yf_chart(ticker_sym, period="5d", interval="1d")
    if not chart:
        return None
    try:
        meta  = chart["meta"]
        price = _safe_float(meta.get("regularMarketPrice"))
        if not price:
            return None
        prev  = _safe_float(meta.get("chartPreviousClose") or meta.get("previousClose")) or price
        return {
            "value":      price,
            "change":     round(price - prev, 2),
            "change_pct": round((price - prev) / prev * 100, 2) if prev else 0.0,
        }
    except Exception:
        return None


# ── Alpha Vantage ──────────────────────────────────────────────────────────────

async def _av_quote(symbol: str) -> dict | None:
    if not settings.ALPHA_VANTAGE_KEY:
        return None
    async with _av_semaphore:
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                resp = await client.get(_AV_BASE, params={
                    "function": "GLOBAL_QUOTE", "symbol": symbol,
                    "apikey": settings.ALPHA_VANTAGE_KEY,
                })
            body = resp.json()
            if "Note" in body or "Information" in body:
                return None
            av = body.get("Global Quote", {})
            if not av.get("05. price"):
                return None
            price = _safe_float(av["05. price"])
            prev  = _safe_float(av.get("08. previous close", price))
            if not price:
                return None
            pct = _safe_float(av.get("10. change percent", "0%").replace("%", "")) or 0.0
            return _sanitize({
                "symbol":     symbol,
                "price":      price,
                "change":     round(price - (prev or price), 2),
                "change_pct": pct,
                "volume":     int(av.get("06. volume", 0) or 0),
                "market_cap": None,
                "high":       _safe_float(av.get("03. high")),
                "low":        _safe_float(av.get("04. low")),
                "open":       _safe_float(av.get("02. open")),
                "prev_close": prev,
                "source":     "alphavantage",
                "currency":   "USD",
            })
        except Exception:
            return None


async def _av_daily_history(symbol: str, compact: bool = True) -> list[dict]:
    if not settings.ALPHA_VANTAGE_KEY:
        return []
    async with _av_semaphore:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(_AV_BASE, params={
                    "function": "TIME_SERIES_DAILY_ADJUSTED",
                    "symbol": symbol,
                    "outputsize": "compact" if compact else "full",
                    "apikey": settings.ALPHA_VANTAGE_KEY,
                })
            ts = resp.json().get("Time Series (Daily)", {})
            records = []
            for dt, v in sorted(ts.items()):
                try:
                    records.append({
                        "date":   dt,
                        "open":   _safe_float(v.get("1. open"), 4),
                        "high":   _safe_float(v.get("2. high"), 4),
                        "low":    _safe_float(v.get("3. low"),  4),
                        "close":  _safe_float(v.get("5. adjusted close"), 4),
                        "volume": int(v.get("6. volume", 0) or 0),
                    })
                except Exception:
                    continue
            return records
        except Exception:
            return []


async def _av_company_overview(symbol: str) -> dict:
    key = f"overview:{symbol}"
    cached = await cache_get(key)
    if cached:
        return json.loads(cached)
    if not settings.ALPHA_VANTAGE_KEY:
        return {}
    async with _av_semaphore:
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                resp = await client.get(_AV_BASE, params={
                    "function": "OVERVIEW", "symbol": symbol,
                    "apikey": settings.ALPHA_VANTAGE_KEY,
                })
            body = resp.json()
            if "Note" in body or "Information" in body or not body.get("Symbol"):
                return {}
            data = _sanitize({
                "name":           body.get("Name", ""),
                "sector":         body.get("Sector", ""),
                "industry":       body.get("Industry", ""),
                "description":    body.get("Description", ""),
                "market_cap":     _safe_float(body.get("MarketCapitalization"), 0),
                "pe_ratio":       _safe_float(body.get("PERatio")),
                "eps":            _safe_float(body.get("EPS")),
                "dividend_yield": _safe_float(body.get("DividendYield")),
                "week_52_high":   _safe_float(body.get("52WeekHigh")),
                "week_52_low":    _safe_float(body.get("52WeekLow")),
                "beta":           _safe_float(body.get("Beta")),
                "analyst_target": _safe_float(body.get("AnalystTargetPrice")),
                "exchange":       body.get("Exchange", ""),
                "currency":       body.get("Currency", "USD"),
            })
            await cache_set(key, json.dumps(data), ttl=86400)
            return data
        except Exception:
            return {}


# ── Public API ─────────────────────────────────────────────────────────────────

async def get_stock_quote(symbol: str) -> dict:
    key = f"quote:{symbol}"
    cached = await cache_get(key)
    if cached:
        return json.loads(cached)

    data = await _yf_quote(symbol)
    if not data:
        data = await _av_quote(symbol)
    if not data:
        return {"symbol": symbol, "error": "No data available", "price": None}

    data = _sanitize(data)
    await cache_set(key, json.dumps(data), ttl=120)
    return data


async def get_bulk_quotes(symbols: list[str]) -> dict:
    """Fetch quotes for multiple symbols concurrently via Yahoo Finance v8."""
    key = f"bulk:{','.join(sorted(symbols))}"
    cached = await cache_get(key)
    if cached:
        return json.loads(cached)

    result: dict = {}
    uncached = []
    for sym in symbols:
        c = await cache_get(f"quote:{sym}")
        if c:
            result[sym] = json.loads(c)
        else:
            uncached.append(sym)

    if uncached:
        CHUNK = 20
        for i in range(0, len(uncached), CHUNK):
            chunk = uncached[i:i + CHUNK]
            quotes = await asyncio.gather(*[_yf_quote(s) for s in chunk], return_exceptions=True)
            for sym, q in zip(chunk, quotes):
                if q and not isinstance(q, Exception):
                    result[sym] = q
                    await cache_set(f"quote:{sym}", json.dumps(q), ttl=120)

        # AV fallback for any still missing
        still_missing = [s for s in uncached if s not in result]
        if still_missing:
            av_quotes = await asyncio.gather(*[_av_quote(s) for s in still_missing], return_exceptions=True)
            for sym, q in zip(still_missing, av_quotes):
                if q and not isinstance(q, Exception):
                    result[sym] = q
                    await cache_set(f"quote:{sym}", json.dumps(q), ttl=120)

    if result:
        await cache_set(key, json.dumps(result), ttl=120)
    return result


async def get_historical_data(symbol: str, period: str = "1y", interval: str = "1d") -> list[dict]:
    key = f"history:{symbol}:{period}:{interval}"
    cached = await cache_get(key)
    if cached:
        return json.loads(cached)

    records = await _yf_history_direct(symbol, period, interval)

    if not records and interval == "1d":
        records = await _av_daily_history(symbol, compact=(period not in ("5y", "5Y")))

    clean = [r for r in records if None not in (r.get("open"), r.get("high"), r.get("low"), r.get("close"))]
    if clean:
        await cache_set(key, json.dumps(clean), ttl=300)
    return clean


async def get_intraday_data(symbol: str, interval: str = "5min") -> list[dict]:
    key = f"intraday:{symbol}:{interval}"
    cached = await cache_get(key)
    if cached:
        return json.loads(cached)

    yf_interval_map = {"1min": "1m", "5min": "5m", "15min": "15m", "30min": "30m", "60min": "60m"}
    yf_interval = yf_interval_map.get(interval, "5m")
    records = await _yf_history_direct(symbol, period="1d", interval=yf_interval)

    if not records and settings.ALPHA_VANTAGE_KEY:
        async with _av_semaphore:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(_AV_BASE, params={
                        "function": "TIME_SERIES_INTRADAY",
                        "symbol": symbol, "interval": interval,
                        "outputsize": "compact",
                        "apikey": settings.ALPHA_VANTAGE_KEY,
                    })
                body = resp.json()
                if "Note" not in body and "Information" not in body:
                    ts = body.get(f"Time Series ({interval})", {})
                    for dt, v in list(ts.items())[:100]:
                        try:
                            records.append({
                                "date":   dt,
                                "open":   _safe_float(v["1. open"], 4),
                                "high":   _safe_float(v["2. high"], 4),
                                "low":    _safe_float(v["3. low"],  4),
                                "close":  _safe_float(v["4. close"], 4),
                                "volume": int(v["5. volume"]),
                            })
                        except Exception:
                            continue
                    records.reverse()
            except Exception:
                pass

    if records:
        await cache_set(key, json.dumps(records), ttl=60)
    return records


async def get_market_movers() -> dict:
    key = "market:movers"
    cached = await cache_get(key)
    if cached:
        return json.loads(cached)

    symbols = ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "NFLX", "AMD", "INTC", "ORCL", "CRM"]
    quotes = await get_bulk_quotes(symbols)
    ql = [v for v in quotes.values() if v and "error" not in v and v.get("price")]
    sorted_q = sorted(ql, key=lambda x: x.get("change_pct") or 0, reverse=True)
    data = _sanitize({
        "gainers": [q for q in sorted_q if (q.get("change_pct") or 0) >= 0][:6],
        "losers":  sorted(ql, key=lambda x: x.get("change_pct") or 0)[:6],
    })
    await cache_set(key, json.dumps(data), ttl=60)
    return data


async def get_market_indices() -> dict:
    key = "market:indices"
    cached = await cache_get(key)
    if cached:
        return json.loads(cached)

    index_map = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "VIX": "^VIX"}
    fallback = {"value": 0.0, "change": 0.0, "change_pct": 0.0}
    values = await asyncio.gather(
        *[_yf_index_direct(t) for t in index_map.values()],
        return_exceptions=True,
    )
    result = _sanitize({
        name: (v if (v and not isinstance(v, Exception)) else fallback)
        for name, v in zip(index_map.keys(), values)
    })
    await cache_set(key, json.dumps(result), ttl=60)
    return result


async def search_stocks(query: str) -> list[dict]:
    if settings.ALPHA_VANTAGE_KEY:
        async with _av_semaphore:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(_AV_BASE, params={
                        "function": "SYMBOL_SEARCH", "keywords": query,
                        "apikey": settings.ALPHA_VANTAGE_KEY,
                    })
                body = resp.json()
                if "Note" not in body and "Information" not in body:
                    matches = body.get("bestMatches", [])
                    if matches:
                        return [{"symbol": m.get("1. symbol", ""), "name": m.get("2. name", ""),
                                 "exchange": m.get("4. region", "")} for m in matches[:10]]
            except Exception:
                pass
    # Yahoo Finance search fallback
    try:
        async with httpx.AsyncClient(timeout=8, headers=_HEADERS) as client:
            r = await client.get(
                "https://query1.finance.yahoo.com/v1/finance/search",
                params={"q": query, "quotesCount": 10, "newsCount": 0},
            )
        hits = r.json().get("quotes", [])
        return [{"symbol": h.get("symbol", ""), "name": h.get("longname") or h.get("shortname", ""),
                 "exchange": h.get("exchange", "")} for h in hits if h.get("symbol")][:10]
    except Exception:
        return []


async def get_stock_detail(symbol: str) -> dict:
    key = f"detail:{symbol}"
    cached = await cache_get(key)
    if cached:
        return json.loads(cached)

    quote, overview = await asyncio.gather(
        get_stock_quote(symbol),
        _av_company_overview(symbol),
        return_exceptions=True,
    )
    if isinstance(quote, Exception):
        quote = {"symbol": symbol, "error": "No data", "price": None}
    if isinstance(overview, Exception):
        overview = {}

    result = _sanitize({**quote, "overview": overview})
    await cache_set(key, json.dumps(result), ttl=120)
    return result
