"""
AI Pipeline: Single Provider with structured fallback
──────────────────────────────────────────────────────
Provider: xAI (Grok) — configure XAI_API_KEY in .env to enable.
Falls back to structured raw-data response if no provider is configured.
"""

import re
import asyncio
import httpx
from app.core.config import settings
from app.services.market_service import get_stock_quote, get_market_movers
from app.services.prediction_service import run_prediction
from app.services.risk_service import analyze_risk

_XAI_BASE = "https://api.x.ai/v1"

OFF_TOPIC_RESPONSE = (
    "This topic is not related to trading — this query is out of my scope.\n"
    "Ask me questions about trading, stocks, or investing."
)

TRADING_KEYWORDS = [
    "stock", "share", "invest", "buy", "sell", "trade", "trading", "market", "portfolio",
    "price", "chart", "rsi", "macd", "moving average", "support", "resistance", "bullish",
    "bearish", "dividend", "earnings", "ipo", "etf", "option", "future", "crypto", "bitcoin",
    "nasdaq", "nyse", "s&p", "dow", "nifty", "sensex", "broker", "equity", "bond", "fund",
    "profit", "loss", "return", "risk", "hedge", "short", "long", "volume", "volatility",
    "technical", "fundamental", "analysis", "sector", "cap", "valuation", "pe ratio",
    "revenue", "margin", "balance sheet", "cash flow", "inflation", "interest rate",
    "fed", "economy", "gdp", "recession", "bull", "bear", "rally", "correction", "signal",
    "money", "dollar", "currency", "forex", "commodity", "gold", "oil", "silver",
    "watchlist", "prediction", "forecast", "backtest", "strategy", "swing", "day trading",
    "intraday", "scalping", "position", "allocation", "diversif", "rebalance", "stop loss",
    "take profit", "target", "breakout", "trend", "momentum", "oversold", "overbought",
    "aapl", "tsla", "msft", "amzn", "googl", "meta", "nvda", "nflx", "amd", "intc",
    "wmt", "walmart", "costco", "disney", "uber", "alibaba", "goldman",
    "can i invest", "should i buy", "should i sell", "which shares", "which stocks",
    "worth buying", "worth selling", "good time to buy", "good time to sell",
    "suggest", "recommend", "advice", "help me", "what should", "how much",
    "tell me about", "give me", "give about", "analyze", "analysis of",
]

STOCK_CATALOG = [
    {"symbol": "AAPL",  "name": "Apple Inc.",            "price": 195,  "sector": "Technology"},
    {"symbol": "MSFT",  "name": "Microsoft Corp.",        "price": 415,  "sector": "Technology"},
    {"symbol": "GOOGL", "name": "Alphabet Inc.",          "price": 175,  "sector": "Technology"},
    {"symbol": "AMZN",  "name": "Amazon.com Inc.",        "price": 185,  "sector": "E-Commerce"},
    {"symbol": "META",  "name": "Meta Platforms",         "price": 490,  "sector": "Social Media"},
    {"symbol": "NVDA",  "name": "NVIDIA Corp.",           "price": 875,  "sector": "Semiconductors"},
    {"symbol": "TSLA",  "name": "Tesla Inc.",             "price": 175,  "sector": "EV/Auto"},
    {"symbol": "AMD",   "name": "Advanced Micro Devices", "price": 155,  "sector": "Semiconductors"},
    {"symbol": "NFLX",  "name": "Netflix Inc.",           "price": 620,  "sector": "Streaming"},
    {"symbol": "INTC",  "name": "Intel Corp.",            "price": 22,   "sector": "Semiconductors"},
    {"symbol": "ORCL",  "name": "Oracle Corp.",           "price": 125,  "sector": "Cloud/Software"},
    {"symbol": "CRM",   "name": "Salesforce Inc.",        "price": 280,  "sector": "Cloud/CRM"},
    {"symbol": "JPM",   "name": "JPMorgan Chase",         "price": 195,  "sector": "Banking"},
    {"symbol": "BAC",   "name": "Bank of America",        "price": 38,   "sector": "Banking"},
    {"symbol": "V",     "name": "Visa Inc.",              "price": 270,  "sector": "Fintech"},
    {"symbol": "JNJ",   "name": "Johnson & Johnson",      "price": 155,  "sector": "Healthcare"},
    {"symbol": "PFE",   "name": "Pfizer Inc.",            "price": 28,   "sector": "Pharma"},
    {"symbol": "XOM",   "name": "ExxonMobil Corp.",       "price": 110,  "sector": "Energy/Oil"},
    {"symbol": "WMT",   "name": "Walmart Inc.",           "price": 95,   "sector": "Retail"},
    {"symbol": "COST",  "name": "Costco Wholesale",       "price": 920,  "sector": "Retail"},
    {"symbol": "HD",    "name": "Home Depot",             "price": 390,  "sector": "Retail"},
    {"symbol": "DIS",   "name": "Walt Disney Co.",        "price": 110,  "sector": "Entertainment"},
    {"symbol": "BABA",  "name": "Alibaba Group",          "price": 85,   "sector": "E-Commerce"},
    {"symbol": "UBER",  "name": "Uber Technologies",      "price": 75,   "sector": "Transport"},
    {"symbol": "GS",    "name": "Goldman Sachs",          "price": 550,  "sector": "Banking"},
    {"symbol": "SPY",   "name": "S&P 500 ETF",            "price": 520,  "sector": "ETF/Index"},
    {"symbol": "QQQ",   "name": "NASDAQ 100 ETF",         "price": 445,  "sector": "ETF/Tech"},
]

# Company name → ticker (for natural language queries like "tell me about Walmart")
COMPANY_NAME_MAP = {
    "walmart": "WMT", "apple": "AAPL", "microsoft": "MSFT", "nvidia": "NVDA",
    "google": "GOOGL", "alphabet": "GOOGL", "meta": "META", "facebook": "META",
    "amazon": "AMZN", "tesla": "TSLA", "netflix": "NFLX", "intel": "INTC",
    "oracle": "ORCL", "salesforce": "CRM", "jpmorgan": "JPM", "jp morgan": "JPM",
    "bank of america": "BAC", "visa": "V", "johnson": "JNJ", "pfizer": "PFE",
    "exxon": "XOM", "costco": "COST", "home depot": "HD", "disney": "DIS",
    "alibaba": "BABA", "uber": "UBER", "goldman": "GS", "goldman sachs": "GS",
    "amd": "AMD", "advanced micro": "AMD",
}

SYSTEM_PROMPT = """You are TradeMind AI, a professional stock market analyst and trading advisor.
You receive live/latest market data (price, RSI, MACD, moving averages, Bollinger Bands,
ATR, volume, risk metrics, algo signal) and the user's question.

IMPORTANT RULES:
- ALWAYS give a full analysis and recommendation — never say "no data" or "try during market hours"
- US markets are open Mon-Fri 9:30am-4pm ET. Outside hours, use the latest available data and note it
- If the user asks about a company by name (e.g. "Walmart"), analyze that stock
- Always identify the stock ticker from the user's question

Your response format:
1. Start with verdict: ✅ BUY / 🔄 HOLD / ⚠️ SELL + stock name and ticker
2. Current price and today's change
3. 3-4 bullet points with specific reasons backed by the indicator data
4. Trade setup table: Entry | Target | Stop-Loss | Upside %
5. Key indicators: RSI, MACD, trend (above/below MA50/200), volume
6. Conviction level: HIGH / MEDIUM / LOW with brief justification
7. End with: ⚠️ Not financial advice. Always do your own research.

Use $ for all prices. Be specific with numbers from the data provided."""


# ── Helpers ────────────────────────────────────────────────────────────────────

def _is_trading_related(prompt: str) -> bool:
    p = prompt.lower()
    if any(kw in p for kw in TRADING_KEYWORDS):
        return True
    # Also pass if a known company name is mentioned
    if any(name in p for name in COMPANY_NAME_MAP):
        return True
    return False


def _extract_symbol(prompt: str) -> str | None:
    p_lower = prompt.lower()
    p_upper = prompt.upper()

    # 1. Check company names first (highest priority for natural language)
    for name, sym in COMPANY_NAME_MAP.items():
        if name in p_lower:
            return sym

    # 2. Check known catalog symbols (word boundary)
    for s in STOCK_CATALOG:
        if re.search(rf'\b{s["symbol"]}\b', p_upper):
            return s["symbol"]

    # 3. Generic uppercase ticker pattern
    match = re.search(r'\b([A-Z]{1,5})\b', p_upper)
    if match:
        candidate = match.group(1)
        if candidate not in {"I", "A", "THE", "AND", "OR", "IN", "ON", "AT", "TO", "MY", "ME",
                              "BUY", "SELL", "CAN", "NOW", "GET", "FOR", "USD", "RSI",
                              "ETF", "IPO", "GDP", "FED", "VIX", "ATR", "AI", "GIVE",
                              "ABOUT", "TELL", "SHOW", "WHAT", "HOW", "WHY", "WHEN"}:
            return candidate
    return None


def _extract_budget(prompt: str) -> float | None:
    p = prompt.lower().replace(",", "")
    match = re.search(r'[\$₹rs\.]?\s*(\d+(?:\.\d+)?)\s*(k|thousand|lakh|lac)?', p)
    if match:
        amount = float(match.group(1))
        suffix = match.group(2) or ""
        if suffix in ("k", "thousand"):
            amount *= 1000
        elif suffix in ("lakh", "lac"):
            amount *= 100000
        if amount >= 10:
            return amount
    return None


def _build_messages(user_question: str, context: str, history: list[dict]) -> list[dict]:
    """Build the messages array with system prompt + context + history + user question."""
    system = SYSTEM_PROMPT + (f"\n\n=== LIVE MARKET DATA ===\n{context}" if context else "")
    messages = [{"role": "system", "content": system}]
    for h in history[-6:]:
        messages.append({"role": "user",      "content": h["prompt"]})
        messages.append({"role": "assistant", "content": h["response"]})
    messages.append({"role": "user", "content": user_question})
    return messages


async def _gather_stock_context(symbol: str) -> str:
    try:
        pred, risk, quote = await asyncio.gather(
            run_prediction(symbol),
            analyze_risk(symbol),
            get_stock_quote(symbol),
            return_exceptions=True,
        )

        parts = [f"=== RAW MARKET DATA: {symbol} ==="]

        if not isinstance(quote, Exception) and quote and "error" not in quote:
            parts.append(
                f"Price: ${quote.get('price', 0):.2f} | "
                f"Change: {quote.get('change_pct', 0):+.2f}% | "
                f"Volume: {quote.get('volume', 0):,} | "
                f"High: ${quote.get('high', 0):.2f} | Low: ${quote.get('low', 0):.2f} | "
                f"Prev Close: ${quote.get('prev_close', 0):.2f}"
            )

        if not isinstance(pred, Exception) and pred and "error" not in pred:
            ind = pred.get("indicators", {}) or {}
            sig_breakdown = pred.get("signal_breakdown", {}) or {}
            cur = pred.get("current_price", 0)
            tgt = pred.get("predicted_price", 0)

            parts.append(
                f"Algo Signal: {pred.get('signal')} | "
                f"Confidence: {pred.get('confidence_score', 0)*100:.0f}% | "
                f"Trend: {pred.get('trend')} | "
                f"Composite Score: {pred.get('composite_score', 0):+.4f}"
            )
            parts.append(
                f"Entry: ${pred.get('entry_price', 0):.2f} | "
                f"Target: ${tgt:.2f} | "
                f"Stop Loss: ${pred.get('stop_loss', 0):.2f} | "
                f"Upside: {((tgt - cur) / max(cur, 1) * 100):+.1f}%"
            )

            if ind:
                rsi      = ind.get("rsi")
                macd     = ind.get("macd")
                macd_sig = ind.get("macd_signal")
                macd_h   = ind.get("macd_hist")
                ma10     = ind.get("ma10")
                ma20     = ind.get("ma20")
                ma50     = ind.get("ma50")
                ma200    = ind.get("ma200")
                bb_upper = ind.get("bb_upper")
                bb_lower = ind.get("bb_lower")
                bb_pct   = ind.get("bb_pct")
                stoch_k  = ind.get("stoch_k")
                stoch_d  = ind.get("stoch_d")
                atr      = ind.get("atr")
                vol_r    = ind.get("vol_ratio")
                roc10    = ind.get("roc10")

                parts.append(
                    f"RSI(14): {rsi:.2f} | MACD: {macd:.4f} | MACD Signal: {macd_sig:.4f} | MACD Hist: {macd_h:.4f}"
                    if all(v is not None for v in [rsi, macd, macd_sig, macd_h]) else
                    f"RSI(14): {rsi} | MACD: {macd} | MACD Signal: {macd_sig}"
                )
                parts.append(
                    f"MA10: ${ma10:.2f} | MA20: ${ma20:.2f} | MA50: ${ma50:.2f} | MA200: ${ma200:.2f}"
                    if all(v is not None for v in [ma10, ma20, ma50, ma200]) else
                    f"MA50: {ma50} | MA200: {ma200}"
                )
                parts.append(
                    f"BB Upper: ${bb_upper:.2f} | BB Lower: ${bb_lower:.2f} | BB Position: {(bb_pct or 0)*100:.1f}%"
                    if bb_upper and bb_lower else f"BB%: {bb_pct}"
                )
                parts.append(
                    f"Stoch K: {stoch_k:.1f} | Stoch D: {stoch_d:.1f} | "
                    f"ATR: ${atr:.2f} | Vol Ratio: {vol_r:.2f}x | ROC(10): {roc10:.2f}%"
                    if all(v is not None for v in [stoch_k, stoch_d, atr, vol_r, roc10]) else
                    f"Stoch K: {stoch_k} | ATR: {atr} | Vol Ratio: {vol_r}"
                )

            if sig_breakdown:
                parts.append(
                    "Signal Breakdown: " +
                    " | ".join(f"{k.upper()}: {v:+.3f}" for k, v in sig_breakdown.items())
                )

        if not isinstance(risk, Exception) and risk:
            parts.append(
                f"Risk Level: {risk.get('risk_level')} | "
                f"Annual Volatility: {risk.get('volatility', 0):.2f}% | "
                f"VaR(95%): {risk.get('var_95', 0):.3f}% | "
                f"Max Drawdown: {risk.get('max_drawdown', 0):.2f}% | "
                f"Sharpe Ratio: {risk.get('sharpe_ratio', 0):.3f}"
            )

        return "\n".join(parts)
    except Exception:
        return f"Live data for {symbol} is temporarily unavailable."


async def _gather_market_context() -> str:
    try:
        movers = await get_market_movers()
        gainers = movers.get("gainers", [])[:4]
        losers  = movers.get("losers",  [])[:4]
        g = " | ".join(f"{g['symbol']} +{g['change_pct']:.2f}% @ ${g.get('price',0):.2f}" for g in gainers if "change_pct" in g)
        l = " | ".join(f"{l['symbol']} {l['change_pct']:.2f}% @ ${l.get('price',0):.2f}"  for l in losers  if "change_pct" in l)
        return f"=== TODAY'S MARKET ===\nTop Gainers: {g}\nTop Losers: {l}"
    except Exception:
        return ""


# ── Provider caller (OpenAI-compatible) ───────────────────────────────────────

async def _call_openai_compat(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    timeout: int = 30,
    extra_headers: dict | None = None,
) -> str | None:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.3,
                },
            )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return None
    except Exception:
        return None


# ── Waterfall ──────────────────────────────────────────────────────────────────

async def _waterfall(messages: list[dict]) -> str:
    """Try xAI (Grok) if configured, otherwise fall back to structured response."""
    if settings.XAI_API_KEY:
        result = await _call_openai_compat(_XAI_BASE, settings.XAI_API_KEY, settings.XAI_MODEL, messages, 30)
        if result:
            return result
    return _hard_fallback(messages)


def _hard_fallback(messages: list[dict]) -> str:
    """No AI provider configured — extract raw data from the system message and show it."""
    system_content = next((m["content"] for m in messages if m["role"] == "system"), "")
    signal_line = next((l for l in system_content.splitlines() if "Algo Signal:" in l), "")
    price_line  = next((l for l in system_content.splitlines() if "Price:" in l), "")
    if signal_line and price_line:
        return (
            f"📊 **Raw Analysis (no AI provider configured)**\n\n"
            f"{price_line}\n{signal_line}\n\n"
            f"*(Set XAI_API_KEY in backend/.env to enable AI responses)*"
        )
    return "⚠️ No AI provider configured. Set XAI_API_KEY in backend/.env to enable AI responses."


# ── Main entry point ───────────────────────────────────────────────────────────

async def chat_with_ai(prompt: str, history: list[dict] = [], symbol: str = None) -> str:
    if not _is_trading_related(prompt):
        return OFF_TOPIC_RESPONSE

    p = prompt.lower()
    is_budget_query = any(w in p for w in ["budget", "afford", "how much", "suggest", "recommend", "which stock"])
    is_market_query = any(w in p for w in ["market", "overview", "today", "movers", "gainers", "losers", "trending"])

    context_parts = []
    target_symbol = symbol or _extract_symbol(prompt)

    if target_symbol:
        context_parts.append(await _gather_stock_context(target_symbol))
    elif is_market_query or is_budget_query:
        market_ctx = await _gather_market_context()
        if market_ctx:
            context_parts.append(market_ctx)

    budget = _extract_budget(prompt)
    if budget and is_budget_query:
        affordable = [s for s in STOCK_CATALOG if s["price"] <= budget]
        if affordable:
            stocks_str = ", ".join(f"{s['symbol']} (~${s['price']})" for s in affordable[:8])
            context_parts.append(f"Stocks within ${budget:,.0f} budget: {stocks_str}")

    raw_context = "\n\n".join(context_parts)
    messages = _build_messages(prompt, raw_context, history)

    return await _waterfall(messages)
