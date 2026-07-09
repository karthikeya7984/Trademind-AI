"""
market_service.py
-----------------
Data priority:
  1. yfinance bulk download  – fast, free, handles all symbols at once
  2. Alpha Vantage            – single quotes, intraday, history fallback
  3. yfinance single Ticker   – last-resort per-symbol

Alpha Vantage free tier: 25 req/day, 5/min — only used when needed.
Redis caching: quotes=2min, history=5min, indices=1min, movers=1min
"""

import json
import math
import asyncio
import importlib
import httpx
from app.core.redis import cache_get, cache_set
from app.core.config import settings

_AV_BASE = "https://www.alphavantage.co/query"
_av_semaphore = asyncio.Semaphore(2)  # max 2 concurrent AV requests


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
        import pandas as pd
        return 0 if (v is None or (isinstance(v, float) and math.isnan(v))) else int(v)
    except Exception:
        return 0


# ── yfinance (bulk – single network call for all symbols) ─────────────────────

def _yf_bulk(symbols: list[str]) -> dict:
    """Download last 5 days for all symbols in ONE yfinance call."""
    try:
        import pandas as pd
        yf = importlib.import_module("yfinance")
        # yfinance uses BRK-B not BRK.B; map back after download
        yf_symbols = [s.replace(".", "-") for s in symbols]
        sym_map = {yf: orig for yf, orig in zip(yf_symbols, symbols)}
        raw = " ".join(yf_symbols)
        df = yf.download(raw, period="5d", interval="1d",
                         group_by="ticker", auto_adjust=True,
                         progress=False, threads=True)
        result = {}
        single = len(yf_symbols) == 1

        for yf_sym in yf_symbols:
            orig_sym = sym_map[yf_sym]
            try:
                if single:
                    sdf = df
                elif isinstance(df.columns, pd.MultiIndex):
                    # yfinance can use either (field, ticker) or (ticker, field) ordering
                    lvl0 = df.columns.get_level_values(0).unique().tolist()
                    lvl1 = df.columns.get_level_values(1).unique().tolist()
                    if yf_sym in lvl1:
                        sdf = df.xs(yf_sym, axis=1, level=1)
                    elif yf_sym in lvl0:
                        sdf = df.xs(yf_sym, axis=1, level=0)
                    else:
                        continue
                else:
                    sdf = df

                if sdf is None or (hasattr(sdf, "empty") and sdf.empty):
                    continue
                # Normalize column names
                sdf = sdf.copy()
                sdf.columns = [c.strip().title() for c in sdf.columns]
                if "Close" not in sdf.columns:
                    continue
                sdf = sdf.dropna(subset=["Close"])
                if len(sdf) < 1:
                    continue

                today = sdf.iloc[-1]
                prev_close = float(sdf.iloc[-2]["Close"]) if len(sdf) >= 2 else float(today.get("Open", today["Close"]))
                price = float(today["Close"])
                if not price or price <= 0:
                    continue

                result[orig_sym] = _sanitize({
                    "symbol": orig_sym,
                    "price": round(price, 2),
                    "change": round(price - prev_close, 2),
                    "change_pct": round((price - prev_close) / prev_close * 100, 2) if prev_close else 0.0,
                    "volume": _fmt_volume(today.get("Volume")),
                    "market_cap": None,
                    "high": _safe_float(today.get("High")),
                    "low": _safe_float(today.get("Low")),
                    "open": _safe_float(today.get("Open")),
                    "prev_close": round(prev_close, 2),
                    "source": "yfinance",
                    "currency": "USD",
                })
            except Exception:
                continue
        return result
    except Exception:
        return {}


def _yf_single(symbol: str) -> dict | None:
    yf_symbol = symbol.replace(".", "-")
    try:
        yf = importlib.import_module("yfinance")
        info = yf.Ticker(yf_symbol).fast_info
        price = _safe_float(info.last_price)
        if not price:
            return None
        prev = _safe_float(info.previous_close) or price
        return _sanitize({
            "symbol": symbol,
            "price": price,
            "change": round(price - prev, 2),
            "change_pct": round((price - prev) / prev * 100, 2) if prev else 0.0,
            "volume": _safe_float(getattr(info, "three_month_average_volume", 0), 0) or 0,
            "market_cap": _safe_float(getattr(info, "market_cap", None), 0),
            "high": _safe_float(getattr(info, "day_high", None)),
            "low": _safe_float(getattr(info, "day_low", None)),
            "open": _safe_float(getattr(info, "open", None)),
            "prev_close": prev,
            "source": "yfinance_single",
            "currency": "USD",
        })
    except Exception:
        return None


def _yf_history(symbol: str, period: str, interval: str) -> list[dict]:
    period_map = {"1w": "5d", "1W": "5d", "1m": "1mo", "1M": "1mo", "1Y": "1y", "5Y": "5y"}
    # yfinance uses BRK-B not BRK.B
    yf_symbol = symbol.replace(".", "-")
    try:
        yf = importlib.import_module("yfinance")
        df = yf.Ticker(yf_symbol).history(period=period_map.get(period, period), interval=interval)
        if df.empty:
            return []
        df.reset_index(inplace=True)
        date_col = "Datetime" if "Datetime" in df.columns else "Date"
        df = df.rename(columns={date_col: "date", "Open": "open", "High": "high",
                                  "Low": "low", "Close": "close", "Volume": "volume"})
        records = []
        for _, row in df[["date", "open", "high", "low", "close", "volume"]].iterrows():
            try:
                o, h, l, c = (_safe_float(row["open"], 4), _safe_float(row["high"], 4),
                               _safe_float(row["low"], 4), _safe_float(row["close"], 4))
                if None in (o, h, l, c):
                    continue
                records.append({
                    "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
                    "open": o, "high": h, "low": l, "close": c,
                    "volume": _fmt_volume(row["volume"]),
                })
            except Exception:
                continue
        return records
    except Exception:
        return []


def _yf_index(ticker_sym: str) -> dict | None:
    try:
        yf = importlib.import_module("yfinance")
        fi = yf.Ticker(ticker_sym).fast_info  # index tickers like ^GSPC don't need dot fix
        price = _safe_float(fi.last_price)
        if not price:
            return None
        prev = _safe_float(fi.previous_close) or price
        return {
            "value": price,
            "change": round(price - prev, 2),
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
            prev = _safe_float(av.get("08. previous close", price))
            if not price:
                return None
            pct = _safe_float(av.get("10. change percent", "0%").replace("%", "")) or 0.0
            return _sanitize({
                "symbol": symbol,
                "price": price,
                "change": round(price - (prev or price), 2),
                "change_pct": pct,
                "volume": int(av.get("06. volume", 0) or 0),
                "market_cap": None,
                "high": _safe_float(av.get("03. high")),
                "low": _safe_float(av.get("04. low")),
                "open": _safe_float(av.get("02. open")),
                "prev_close": prev,
                "source": "alphavantage",
                "currency": "USD",
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
                        "date": dt,
                        "open": _safe_float(v.get("1. open"), 4),
                        "high": _safe_float(v.get("2. high"), 4),
                        "low": _safe_float(v.get("3. low"), 4),
                        "close": _safe_float(v.get("5. adjusted close"), 4),
                        "volume": int(v.get("6. volume", 0) or 0),
                    })
                except Exception:
                    continue
            return records
        except Exception:
            return []


# ── Public API ─────────────────────────────────────────────────────────────────

async def get_stock_quote(symbol: str) -> dict:
    key = f"quote:{symbol}"
    cached = await cache_get(key)
    if cached:
        return json.loads(cached)

    # Try AV first for a single symbol (most accurate)
    data = await _av_quote(symbol)
    # Fallback to yfinance
    if not data:
        data = await asyncio.to_thread(_yf_single, symbol)
    if not data:
        return {"symbol": symbol, "error": "No data available", "price": None}

    data = _sanitize(data)
    await cache_set(key, json.dumps(data), ttl=120)
    return data


async def get_bulk_quotes(symbols: list[str]) -> dict:
    """Chunked yfinance bulk calls — avoids MultiIndex issues with large batches."""
    key = f"bulk:{','.join(sorted(symbols))}"
    cached = await cache_get(key)
    if cached:
        return json.loads(cached)

    result: dict = {}

    # Check per-symbol cache first
    uncached = []
    for sym in symbols:
        c = await cache_get(f"quote:{sym}")
        if c:
            result[sym] = json.loads(c)
        else:
            uncached.append(sym)

    if uncached:
        # Chunk into groups of 20 to avoid yfinance MultiIndex issues with large batches
        CHUNK = 20
        for i in range(0, len(uncached), CHUNK):
            chunk = uncached[i:i + CHUNK]
            bulk = await asyncio.to_thread(_yf_bulk, chunk)
            for sym, q in bulk.items():
                result[sym] = q
                await cache_set(f"quote:{sym}", json.dumps(q), ttl=120)

        # Any still missing → individual yfinance single fallback
        still_missing = [s for s in uncached if s not in result]
        if still_missing:
            async def _one(sym):
                q = await asyncio.to_thread(_yf_single, sym)
                return sym, q
            pairs = await asyncio.gather(*[_one(s) for s in still_missing], return_exceptions=True)
            for item in pairs:
                if isinstance(item, Exception):
                    continue
                sym, q = item
                if q:
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

    # yfinance first (free, fast, no daily limits)
    records = await asyncio.to_thread(_yf_history, symbol, period, interval)

    # AV fallback for daily history only
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

    records: list[dict] = []

    if settings.ALPHA_VANTAGE_KEY:
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
                                "date": dt,
                                "open": _safe_float(v["1. open"], 4),
                                "high": _safe_float(v["2. high"], 4),
                                "low": _safe_float(v["3. low"], 4),
                                "close": _safe_float(v["4. close"], 4),
                                "volume": int(v["5. volume"]),
                            })
                        except Exception:
                            continue
                    records.reverse()
            except Exception:
                pass

    if not records:
        records = await get_historical_data(symbol, period="5d", interval="5m")

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
        "losers": sorted(ql, key=lambda x: x.get("change_pct") or 0)[:6],
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
        *[asyncio.to_thread(_yf_index, t) for t in index_map.values()],
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
    try:
        yf = importlib.import_module("yfinance")
        info = yf.Ticker(query).info
        return [{"symbol": query.upper(), "name": info.get("longName", query), "exchange": info.get("exchange", "")}]
    except Exception:
        return []


async def _av_company_overview(symbol: str) -> dict:
    """Fetch company overview from Alpha Vantage. Cached for 24h."""
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
            data = {
                "name": body.get("Name", ""),
                "sector": body.get("Sector", ""),
                "industry": body.get("Industry", ""),
                "description": body.get("Description", ""),
                "market_cap": _safe_float(body.get("MarketCapitalization"), 0),
                "pe_ratio": _safe_float(body.get("PERatio")),
                "eps": _safe_float(body.get("EPS")),
                "dividend_yield": _safe_float(body.get("DividendYield")),
                "week_52_high": _safe_float(body.get("52WeekHigh")),
                "week_52_low": _safe_float(body.get("52WeekLow")),
                "beta": _safe_float(body.get("Beta")),
                "analyst_target": _safe_float(body.get("AnalystTargetPrice")),
                "exchange": body.get("Exchange", ""),
                "currency": body.get("Currency", "USD"),
            }
            data = _sanitize(data)
            await cache_set(key, json.dumps(data), ttl=86400)  # 24h cache
            return data
        except Exception:
            return {}


async def get_stock_detail(symbol: str) -> dict:
    """Single endpoint: quote + overview in parallel, max 1 AV call for overview."""
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
