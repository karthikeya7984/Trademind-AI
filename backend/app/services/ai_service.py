"""
TradeMind AI — Clean Architecture
══════════════════════════════════════════════════════════════════════════════
  User Query
      │
      ▼
  Symbol Extraction + Intent Detection
      │
      ▼
  Data Layer  (market_service + prediction_service + risk_service)
      │
      ▼
  Structured Prediction JSON  ← source of truth
      │
      ▼
  LLM (xAI / OpenAI)  ← EXPLANATION ENGINE ONLY
      │
      ▼
  Professional investor-friendly response

The LLM receives ONLY the structured JSON from the prediction engine.
It NEVER invents prices, indicators, or recommendations.
Configure XAI_API_KEY or OPENAI_API_KEY in backend/.env
"""

import re
import json
import hashlib
import asyncio
import httpx

from app.core.config import settings
from app.core.redis import cache_get, cache_set
from app.services.market_service import get_stock_quote, get_market_movers
from app.services.prediction_service import run_prediction
from app.services.risk_service import analyze_risk

_XAI_BASE    = "https://api.x.ai/v1"
_OPENAI_BASE = "https://api.openai.com/v1"
_GROQ_BASE   = "https://api.groq.com/openai/v1"
_HF_BASE     = "https://api-inference.huggingface.co/models"

OFF_TOPIC_RESPONSE = (
    "This topic is not related to trading — this query is out of my scope.\n"
    "Ask me questions about trading, stocks, or investing."
)

# ── Keyword & Symbol Lookup ────────────────────────────────────────────────────

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
    "tell me about", "give me", "analyze", "analysis of",
]

COMPANY_NAME_MAP = {
    "walmart": "WMT", "apple": "AAPL", "microsoft": "MSFT", "nvidia": "NVDA",
    "google": "GOOGL", "alphabet": "GOOGL", "meta": "META", "facebook": "META",
    "amazon": "AMZN", "tesla": "TSLA", "netflix": "NFLX", "intel": "INTC",
    "oracle": "ORCL", "salesforce": "CRM", "jpmorgan": "JPM", "jp morgan": "JPM",
    "bank of america": "BAC", "visa": "V", "johnson": "JNJ", "pfizer": "PFE",
    "exxon": "XOM", "costco": "COST", "home depot": "HD", "disney": "DIS",
    "alibaba": "BABA", "uber": "UBER", "goldman": "GS", "goldman sachs": "GS",
    "amd": "AMD", "advanced micro": "AMD", "qualcomm": "QCOM", "palantir": "PLTR",
    "shopify": "SHOP", "snowflake": "SNOW", "cloudflare": "NET", "coinbase": "COIN",
    "robinhood": "HOOD", "airbnb": "ABNB", "nike": "NKE", "starbucks": "SBUX",
    "mcdonald": "MCD", "mastercard": "MA", "paypal": "PYPL", "morgan stanley": "MS",
    "berkshire": "BRK-B", "abbvie": "ABBV", "eli lilly": "LLY", "moderna": "MRNA",
    "unitedhealth": "UNH", "chevron": "CVX", "conocophillips": "COP",
}

STOCK_CATALOG = [
    {"symbol": "AAPL",  "name": "Apple Inc.",            "price": 195},
    {"symbol": "MSFT",  "name": "Microsoft Corp.",        "price": 415},
    {"symbol": "GOOGL", "name": "Alphabet Inc.",          "price": 175},
    {"symbol": "AMZN",  "name": "Amazon.com Inc.",        "price": 185},
    {"symbol": "META",  "name": "Meta Platforms",         "price": 490},
    {"symbol": "NVDA",  "name": "NVIDIA Corp.",           "price": 875},
    {"symbol": "TSLA",  "name": "Tesla Inc.",             "price": 175},
    {"symbol": "AMD",   "name": "Advanced Micro Devices", "price": 155},
    {"symbol": "NFLX",  "name": "Netflix Inc.",           "price": 620},
    {"symbol": "INTC",  "name": "Intel Corp.",            "price": 22},
    {"symbol": "ORCL",  "name": "Oracle Corp.",           "price": 125},
    {"symbol": "CRM",   "name": "Salesforce Inc.",        "price": 280},
    {"symbol": "JPM",   "name": "JPMorgan Chase",         "price": 195},
    {"symbol": "BAC",   "name": "Bank of America",        "price": 38},
    {"symbol": "V",     "name": "Visa Inc.",              "price": 270},
    {"symbol": "JNJ",   "name": "Johnson & Johnson",      "price": 155},
    {"symbol": "PFE",   "name": "Pfizer Inc.",            "price": 28},
    {"symbol": "XOM",   "name": "ExxonMobil Corp.",       "price": 110},
    {"symbol": "WMT",   "name": "Walmart Inc.",           "price": 95},
    {"symbol": "COST",  "name": "Costco Wholesale",       "price": 920},
    {"symbol": "SPY",   "name": "S&P 500 ETF",            "price": 520},
    {"symbol": "QQQ",   "name": "NASDAQ 100 ETF",         "price": 445},
]

_STOPWORDS = {
    "I", "A", "THE", "AND", "OR", "IN", "ON", "AT", "TO", "MY", "ME",
    "BUY", "SELL", "CAN", "NOW", "GET", "FOR", "USD", "RSI", "ETF",
    "IPO", "GDP", "FED", "VIX", "ATR", "AI", "GIVE", "ABOUT", "TELL",
    "SHOW", "WHAT", "HOW", "WHY", "WHEN", "IS", "IT", "DO", "BE",
}


# ── System Prompt — LLM is ONLY an explanation engine ─────────────────────────

SYSTEM_PROMPT = """\
You are TradeMind AI — a professional stock market explanation engine.

YOUR ROLE:
You receive a structured JSON object produced by the application's ML prediction engine.
Your ONLY job is to convert that JSON into a clear, professional, investor-friendly explanation.

STRICT RULES:
- Use ONLY the values provided in the JSON. Never invent, assume, or hallucinate any data.
- Never say "I think", "I believe", or "It will definitely".
- Never guarantee returns or profits.
- Never fabricate news, metrics, or prices.
- If confidence < 50%, clearly state the prediction is uncertain.
- If a field is missing or null, state "Insufficient data available for this metric."
- Always explain uncertainty.
- The ML model is the source of truth. You are only the explanation engine.

RESPONSE FORMAT (follow exactly):

## Recommendation
**Signal:** BUY / HOLD / SELL
**Confidence:** X%
**Risk Level:** LOW / MEDIUM / HIGH
**Investment Horizon:** SHORT / MEDIUM

---

## AI Summary
3–5 sentences explaining why the ML engine produced this recommendation based solely on the provided data.

---

## Technical Analysis
Explain what each indicator implies (do not just repeat values):
- **Trend** — price vs MA50/MA200
- **Momentum** — ROC, price direction
- **RSI(14)** — overbought/oversold implication
- **MACD** — crossover status and histogram direction
- **Bollinger Bands** — where price sits in the band
- **Stochastic** — K/D reading implication
- **ATR** — volatility context
- **Volume** — volume ratio vs average

---

## AI Prediction
- Predicted direction and confidence
- Expected price range (entry to target)
- Probability context: bullish vs bearish scenario
- Clearly state these are model predictions, not guarantees

---

## Trading Plan
| Metric | Value |
|--------|-------|
| Current Price | $X.XX |
| Suggested Entry | $X.XX |
| Target | $X.XX |
| Stop Loss | $X.XX |
| Risk/Reward | 1:X |

Explain whether the setup is attractive based on the risk/reward ratio.

---

## Risk Factors
List all risks present in the data. Examples:
- Overbought RSI
- Weak volume confirmation
- High volatility / ATR
- Low confidence score
- Bearish MACD momentum
- Price below MA50/MA200

---

## Final Verdict
- Why the signal was generated
- Key strengths from the data
- Main risks to monitor
- Suggested next action

⚠️ *This is not financial advice. Always conduct your own research before investing.*
"""


# ── Data Collection — builds the structured JSON for the LLM ──────────────────

async def _build_prediction_payload(symbol: str) -> dict:
    """
    Collect all data from the ML engine and risk service.
    Returns a clean structured dict — this is what the LLM receives.
    """
    pred, risk, quote = await asyncio.gather(
        run_prediction(symbol),
        analyze_risk(symbol),
        get_stock_quote(symbol),
        return_exceptions=True,
    )

    payload: dict = {"symbol": symbol, "data_available": False}

    # Quote
    if not isinstance(quote, Exception) and quote and "error" not in quote:
        payload["quote"] = {
            "price":      quote.get("price"),
            "change":     quote.get("change"),
            "change_pct": quote.get("change_pct"),
            "volume":     quote.get("volume"),
            "high":       quote.get("high"),
            "low":        quote.get("low"),
            "prev_close": quote.get("prev_close"),
        }

    # ML Prediction (source of truth)
    if not isinstance(pred, Exception) and pred and "error" not in pred:
        payload["data_available"] = True
        ind = pred.get("indicators", {}) or {}
        payload["prediction"] = {
            "recommendation":   pred.get("signal"),
            "confidence":       round((pred.get("confidence_score", 0.5)) * 100, 1),
            "composite_score":  pred.get("composite_score"),
            "trend":            pred.get("trend"),
            "entry_price":      pred.get("entry_price"),
            "target_price":     pred.get("predicted_price"),
            "stop_loss":        pred.get("stop_loss"),
            "current_price":    pred.get("current_price"),
            "upside_pct":       round(
                ((pred.get("predicted_price", 0) - pred.get("current_price", 1))
                 / max(pred.get("current_price", 1), 1)) * 100, 2
            ) if pred.get("current_price") else None,
        }
        payload["indicators"] = {
            "rsi":         ind.get("rsi"),
            "macd":        ind.get("macd"),
            "macd_signal": ind.get("macd_signal"),
            "macd_hist":   ind.get("macd_hist"),
            "ma10":        ind.get("ma10"),
            "ma20":        ind.get("ma20"),
            "ma50":        ind.get("ma50"),
            "ma200":       ind.get("ma200"),
            "bb_upper":    ind.get("bb_upper"),
            "bb_lower":    ind.get("bb_lower"),
            "bb_pct":      round((ind.get("bb_pct") or 0) * 100, 1),
            "stoch_k":     ind.get("stoch_k"),
            "stoch_d":     ind.get("stoch_d"),
            "atr":         ind.get("atr"),
            "vol_ratio":   ind.get("vol_ratio"),
            "roc10":       ind.get("roc10"),
        }
        payload["signal_breakdown"] = pred.get("signal_breakdown", {})
        payload["advice"] = pred.get("advice", {})

    # Risk metrics
    if not isinstance(risk, Exception) and risk and "error" not in risk:
        payload["risk"] = {
            "risk_level":    risk.get("risk_level"),
            "risk_score":    risk.get("risk_score"),
            "volatility":    risk.get("volatility"),
            "var_95":        risk.get("var_95"),
            "max_drawdown":  risk.get("max_drawdown"),
            "sharpe_ratio":  risk.get("sharpe_ratio"),
            "beta":          risk.get("beta"),
        }

    return payload


async def _build_market_payload() -> dict:
    """Structured market overview payload."""
    try:
        movers = await get_market_movers()
        return {
            "type": "market_overview",
            "gainers": movers.get("gainers", [])[:5],
            "losers":  movers.get("losers",  [])[:5],
        }
    except Exception:
        return {"type": "market_overview", "error": "Market data unavailable"}


# ── LLM Caller ────────────────────────────────────────────────────────────────

async def _call_llm(messages: list[dict], timeout: int = 35) -> str | None:
    """
    Provider waterfall (priority order):
      1. Groq  — free, fastest, Llama 3.3 70B
      2. HF    — free, Mistral-7B via Inference API
      3. xAI   — Grok
      4. OpenAI — GPT-4o-mini
    Returns None if all providers fail.
    """
    # 1. Groq (OpenAI-compatible, free tier)
    if settings.GROQ_API_KEY:
        result = await _call_openai_compat(
            _GROQ_BASE, settings.GROQ_API_KEY, settings.GROQ_MODEL, messages, timeout
        )
        if result:
            return result

    # 2. Hugging Face Inference API
    if settings.HF_API_KEY:
        result = await _call_hf(messages, timeout)
        if result:
            return result

    # 3. xAI Grok
    if settings.XAI_API_KEY:
        result = await _call_openai_compat(
            _XAI_BASE, settings.XAI_API_KEY, settings.XAI_MODEL, messages, timeout
        )
        if result:
            return result

    # 4. OpenAI
    if getattr(settings, "OPENAI_API_KEY", ""):
        result = await _call_openai_compat(
            _OPENAI_BASE, settings.OPENAI_API_KEY, "gpt-4o-mini", messages, timeout
        )
        if result:
            return result

    return None


async def _call_openai_compat(
    base_url: str, api_key: str, model: str,
    messages: list[dict], timeout: int = 35,
) -> str | None:
    """Generic OpenAI-compatible chat completions caller."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "max_tokens": 1200, "temperature": 0.2},
            )
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            return content if content else None
    except Exception:
        pass
    return None


async def _call_hf(messages: list[dict], timeout: int = 35) -> str | None:
    """
    Hugging Face Inference API — converts chat messages to a single prompt
    since most HF models use text-generation, not chat/completions.
    """
    try:
        # Convert messages to a single prompt string
        prompt_parts = []
        for m in messages:
            role = m["role"]
            content = m["content"]
            if role == "system":
                prompt_parts.append(f"<s>[INST] <<SYS>>\n{content}\n<</SYS>>\n")
            elif role == "user":
                prompt_parts.append(f"{content} [/INST]")
            elif role == "assistant":
                prompt_parts.append(f"{content} </s><s>[INST] ")
        full_prompt = "".join(prompt_parts)

        model = settings.HF_MODEL
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{_HF_BASE}/{model}",
                headers={
                    "Authorization": f"Bearer {settings.HF_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "inputs": full_prompt,
                    "parameters": {
                        "max_new_tokens": 1200,
                        "temperature": 0.2,
                        "return_full_text": False,
                    },
                },
            )
        if resp.status_code == 200:
            data = resp.json()
            # HF returns list of generated_text
            if isinstance(data, list) and data:
                return data[0].get("generated_text", "").strip() or None
    except Exception:
        pass
    return None


# ── Structured Fallback — no LLM configured ───────────────────────────────────

def _structured_fallback(payload: dict) -> str:
    """
    When no LLM is configured, generate a structured response directly
    from the prediction payload — no invented data.
    """
    if not payload.get("data_available"):
        return "⚠️ Insufficient data available to provide a reliable analysis."

    pred = payload.get("prediction", {})
    ind  = payload.get("indicators", {})
    risk = payload.get("risk", {})
    adv  = payload.get("advice", {})
    sym  = payload.get("symbol", "")

    signal     = pred.get("recommendation", "HOLD")
    confidence = pred.get("confidence", 50)
    sig_icon   = "✅" if signal == "BUY" else "⚠️" if signal == "SELL" else "🔄"

    rsi      = ind.get("rsi")
    macd     = ind.get("macd")
    macd_sig = ind.get("macd_signal")
    ma50     = ind.get("ma50")
    ma200    = ind.get("ma200")
    cur      = pred.get("current_price")
    entry    = pred.get("entry_price")
    target   = pred.get("target_price")
    stop     = pred.get("stop_loss")
    upside   = pred.get("upside_pct")

    rr = round(abs((target - entry) / (entry - stop)), 2) if entry and target and stop and entry != stop else "N/A"

    lines = [
        f"## Recommendation",
        f"**Signal:** {sig_icon} {signal}  |  **Confidence:** {confidence}%  |  **Risk:** {risk.get('risk_level', 'N/A')}",
        "",
        "---",
        "## AI Summary",
        adv.get("reason", "Analysis based on technical indicators from the prediction engine."),
        "",
        "---",
        "## Technical Analysis",
    ]

    if rsi is not None:
        rsi_note = "oversold — potential reversal zone" if rsi < 30 else "overbought — pullback risk" if rsi > 70 else "neutral range"
        lines.append(f"- **RSI(14):** {rsi:.1f} — {rsi_note}")
    if macd is not None and macd_sig is not None:
        macd_note = "above signal line (bullish)" if macd > macd_sig else "below signal line (bearish)"
        lines.append(f"- **MACD:** {macd:.4f} — {macd_note}")
    if ma50 is not None and cur is not None:
        trend_note = "above MA50 (uptrend)" if cur > ma50 else "below MA50 (downtrend)"
        lines.append(f"- **Trend:** Price ${cur:.2f} is {trend_note}")
    if ma200 is not None and cur is not None:
        lines.append(f"- **MA200:** {'Price above long-term average — bullish structure' if cur > ma200 else 'Price below long-term average — bearish structure'}")
    bb_pct = ind.get("bb_pct")
    if bb_pct is not None:
        bb_note = "near lower band — potential support" if bb_pct < 25 else "near upper band — potential resistance" if bb_pct > 75 else "mid-band — neutral"
        lines.append(f"- **Bollinger Bands:** {bb_pct:.1f}% position — {bb_note}")
    vol_r = ind.get("vol_ratio")
    if vol_r is not None:
        lines.append(f"- **Volume:** {vol_r:.2f}x average — {'above-average activity' if vol_r > 1.2 else 'below-average activity'}")

    lines += [
        "",
        "---",
        "## Trading Plan",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Current Price | ${cur:.2f} |" if cur else "| Current Price | N/A |",
        f"| Suggested Entry | ${entry:.2f} |" if entry else "| Suggested Entry | N/A |",
        f"| Target | ${target:.2f} |" if target else "| Target | N/A |",
        f"| Stop Loss | ${stop:.2f} |" if stop else "| Stop Loss | N/A |",
        f"| Upside | {upside:+.1f}% |" if upside is not None else "| Upside | N/A |",
        f"| Risk/Reward | 1:{rr} |",
        "",
        "---",
        "## Risk Factors",
    ]

    risks = []
    if rsi and rsi > 70:   risks.append("⚠️ RSI overbought — elevated pullback risk")
    if rsi and rsi < 30:   risks.append("⚠️ RSI oversold — high volatility zone")
    if macd and macd_sig and macd < macd_sig: risks.append("⚠️ MACD bearish — downward momentum")
    if vol_r and vol_r < 0.7: risks.append("⚠️ Low volume — weak signal confirmation")
    if confidence < 60:    risks.append(f"⚠️ Low confidence ({confidence}%) — prediction uncertain")
    if risk.get("risk_level") == "HIGH": risks.append("⚠️ High risk score — position sizing caution advised")
    if not risks:          risks.append("No major risk flags detected in current data")
    lines += risks

    lines += [
        "",
        "---",
        "## Final Verdict",
        f"The ML engine generated a **{signal}** signal for **{sym}** with **{confidence}% confidence**.",
        adv.get("reason", ""),
        "",
        f"**Key Strengths:** {', '.join(adv.get('key_factors', ['See indicators above']))}",
        f"**Risk Level:** {risk.get('risk_level', 'N/A')} | Sharpe: {risk.get('sharpe_ratio', 'N/A')} | Max Drawdown: {risk.get('max_drawdown', 'N/A')}%",
        "",
        "⚠️ *This is not financial advice. Always conduct your own research before investing.*",
        "",
        "*(Set XAI_API_KEY or OPENAI_API_KEY in backend/.env for AI-generated explanations)*",
    ]

    return "\n".join(lines)


# ── Symbol & Intent Helpers ────────────────────────────────────────────────────

def _is_trading_related(prompt: str) -> bool:
    p = prompt.lower()
    return any(kw in p for kw in TRADING_KEYWORDS) or any(n in p for n in COMPANY_NAME_MAP)


def _extract_symbol(prompt: str) -> str | None:
    p_lower = prompt.lower()
    p_upper = prompt.upper()
    for name, sym in COMPANY_NAME_MAP.items():
        if name in p_lower:
            return sym
    for s in STOCK_CATALOG:
        if re.search(rf'\b{s["symbol"]}\b', p_upper):
            return s["symbol"]
    match = re.search(r'\b([A-Z]{1,5})\b', p_upper)
    if match and match.group(1) not in _STOPWORDS:
        return match.group(1)
    return None


def _extract_budget(prompt: str) -> float | None:
    p = prompt.lower().replace(",", "")
    match = re.search(r'[\$₹rs\.]?\s*(\d+(?:\.\d+)?)\s*(k|thousand|lakh|lac)?', p)
    if match:
        amount = float(match.group(1))
        suffix = match.group(2) or ""
        if suffix in ("k", "thousand"):   amount *= 1000
        elif suffix in ("lakh", "lac"):   amount *= 100000
        if amount >= 10:
            return amount
    return None


# ── Message Builder ────────────────────────────────────────────────────────────

def _build_messages(user_question: str, payload: dict, history: list[dict]) -> list[dict]:
    """
    System prompt + structured JSON payload + conversation history + user question.
    The LLM receives ONLY the structured payload — never raw indicator strings.
    """
    payload_json = json.dumps(payload, indent=2, default=str)
    system = (
        SYSTEM_PROMPT
        + "\n\n=== STRUCTURED PREDICTION DATA (source of truth) ===\n"
        + payload_json
    )
    messages = [{"role": "system", "content": system}]
    for h in history[-6:]:
        messages.append({"role": "user",      "content": h["prompt"]})
        messages.append({"role": "assistant", "content": h["response"]})
    messages.append({"role": "user", "content": user_question})
    return messages


# ── Main Entry Point ───────────────────────────────────────────────────────────

async def chat_with_ai(prompt: str, history: list[dict] = [], symbol: str = None) -> str:
    if not _is_trading_related(prompt):
        return OFF_TOPIC_RESPONSE

    p = prompt.lower()
    is_market_query = any(w in p for w in ["market", "overview", "today", "movers", "gainers", "losers", "trending"])
    is_budget_query = any(w in p for w in ["budget", "afford", "how much", "suggest", "recommend", "which stock"])

    # Cache key based on prompt + symbol
    cache_key = "ai:" + hashlib.md5((prompt + (symbol or "")).encode()).hexdigest()
    if not history:
        cached = await cache_get(cache_key)
        if cached:
            return cached

    target_symbol = symbol or _extract_symbol(prompt)

    # ── Build structured payload from ML engine ────────────────────────────────
    if target_symbol:
        payload = await _build_prediction_payload(target_symbol)

    elif is_market_query:
        payload = await _build_market_payload()

    elif is_budget_query:
        budget = _extract_budget(prompt)
        affordable = [s for s in STOCK_CATALOG if budget and s["price"] <= budget]
        payload = {
            "type": "budget_query",
            "budget": budget,
            "affordable_stocks": affordable[:8] if affordable else STOCK_CATALOG[:8],
        }

    else:
        payload = {"type": "general_query", "question": prompt}

    # ── LLM explains the payload ───────────────────────────────────────────────
    messages = _build_messages(prompt, payload, history)
    response = await _call_llm(messages)

    # ── Fallback: structured response from payload (no LLM needed) ────────────
    if not response:
        if target_symbol:
            response = _structured_fallback(payload)
        elif is_market_query:
            gainers = payload.get("gainers", [])
            losers  = payload.get("losers",  [])
            g_str = "\n".join(f"- **{g['symbol']}** +{g.get('change_pct', 0):.2f}% @ ${g.get('price', 0):.2f}" for g in gainers)
            l_str = "\n".join(f"- **{l['symbol']}** {l.get('change_pct', 0):.2f}% @ ${l.get('price', 0):.2f}" for l in losers)
            response = f"## Today's Market\n\n**Top Gainers:**\n{g_str}\n\n**Top Losers:**\n{l_str}"
        else:
            response = (
                "⚠️ No AI provider configured.\n\n"
                "Set `XAI_API_KEY` or `OPENAI_API_KEY` in `backend/.env` to enable AI responses.\n\n"
                "The prediction engine is running — ask me to analyze a specific stock like **AAPL** or **NVDA**."
            )

    if not history:
        await cache_set(cache_key, response, ttl=300)

    return response
