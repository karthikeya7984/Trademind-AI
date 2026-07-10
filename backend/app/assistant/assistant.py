"""
assistant.py
────────────
Main orchestrator for the Stock AI Assistant.

Flow:
  1. classify()      — stock-related? if not → reject immediately
  2. detect_intent() — what does the user want?
  3. fetch data      — live market data via market_service / prediction_service
  4. dispatch        — structured handler OR Gemini for dynamic/education queries
  5. memory.add()    — store turn for pronoun resolution

Provider order for AI responses:
  Gemini (primary) → structured fallback (no LLM needed)
"""

import asyncio
import re
import httpx
import pandas as pd

from app.assistant.classifier import classify, REJECTION_MESSAGE
from app.assistant.intent import detect_intent, Intent
from app.assistant.memory import get_memory
from app.assistant.indicators import compute_all
from app.assistant.predictor import predict
from app.assistant import response as resp

from app.services.market_service import (
    get_historical_data,
    get_stock_quote,
    get_market_movers,
)
from app.services.risk_service import analyze_risk
from app.services.news_service import get_symbol_sentiment


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _safe_news_score(symbol: str) -> float:
    try:
        result = await asyncio.wait_for(get_symbol_sentiment(symbol), timeout=4.0)
        return float((result or {}).get("score", 0.0))
    except Exception:
        return 0.0


async def _build_indicators(symbol: str) -> tuple[dict, list[dict]]:
    history = await get_historical_data(symbol.replace(".", "-"), period="6mo", interval="1d")
    if not history or len(history) < 20:
        return {}, history or []
    df = pd.DataFrame(history)
    ind = compute_all(df)
    return ind, history


async def _run_prediction(symbol: str) -> tuple:
    ind, _ = await _build_indicators(symbol)
    if not ind:
        return None, {}
    news_score = await _safe_news_score(symbol)
    result = predict(symbol, ind, news_score)
    return result, ind


# ── Gemini dynamic response ────────────────────────────────────────────────────

async def _gemini_response(prompt: str, context: str, history: list[dict]) -> str | None:
    """
    Call NVIDIA NIM first, then Gemini as fallback.
    Returns None if both are unavailable — caller falls back to structured response.
    """
    from app.core.config import settings

    system = (
        "You are TradeMind AI, a professional stock market analyst. "
        "You ONLY answer questions about stocks, trading, and financial markets. "
        "If the question is not about stocks or finance, reply: "
        "'I only answer stock and trading related questions.' "
        "Be concise, use markdown formatting, and always end with: "
        "*Not financial advice. Always do your own research.*"
        + (f"\n\n=== LIVE MARKET DATA ===\n{context}" if context else "")
    )

    messages = [{"role": "system", "content": system}]
    for h in history[-4:]:
        messages.append({"role": "user",      "content": h["prompt"]})
        messages.append({"role": "assistant", "content": h["response"]})
    messages.append({"role": "user", "content": prompt})

    # ── 1. Try NVIDIA NIM (primary) ──────────────────────────────────────────
    if settings.NVIDIA_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                resp = await client.post(
                    "https://integrate.api.nvidia.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.NVIDIA_MODEL,
                        "messages": messages,
                        "max_tokens": 1024,
                        "temperature": 0.3,
                    },
                )
            if resp.status_code == 200:
                text = resp.json()["choices"][0]["message"]["content"]
                if text:
                    return text
        except Exception:
            pass

    # ── 2. Gemini fallback ────────────────────────────────────────────────────
    if settings.GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                system_instruction=system,
            )
            gemini_history = []
            for h in history[-4:]:
                gemini_history.append({"role": "user",  "parts": [h["prompt"]]})
                gemini_history.append({"role": "model", "parts": [h["response"]]})
            session  = model.start_chat(history=gemini_history)
            response = await asyncio.to_thread(session.send_message, prompt)
            if response.text:
                return response.text
        except Exception:
            pass

    return None


# ── Follow-up detection ───────────────────────────────────────────────────────

_FOLLOWUP_PATTERNS = [
    r"^explain (this|that|it)",
    r"^what does (this|that) mean",
    r"^what does it mean",
    r"^(can you )?explain( more| further)?",
    r"^(tell me )?more (about this|about that)",
    r"^(what|why) (is|does) (this|that|it)",
    r"^break (this|it|that) down",
    r"^i don.?t understand",
    r"^clarify (this|that)?",
    r"^elaborate",
]


def _is_followup(text: str) -> bool:
    t = text.lower().strip()
    return any(re.search(p, t) for p in _FOLLOWUP_PATTERNS)


async def _handle_price(intent: Intent) -> str:
    quote = await get_stock_quote(intent.symbol)
    if not quote or quote.get("error") or not quote.get("price"):
        return f"⚠️ Could not fetch price for **{intent.symbol}**. Check the ticker and try again."
    return resp.build_price_response(intent.symbol, quote)


async def _handle_prediction(intent: Intent) -> str:
    result, _ = await _run_prediction(intent.symbol)
    if result is None:
        return (
            f"⚠️ Not enough historical data to analyze **{intent.symbol}**. "
            "Please check the ticker symbol and try again."
        )
    return resp.build_prediction_response(result, intent)


async def _handle_compare(intent: Intent) -> str:
    sym1, sym2 = intent.symbol, intent.symbol2
    if not sym2:
        return "Please specify two stocks to compare. Example: *\"Compare AAPL and MSFT\"*"

    r1, r2 = await asyncio.gather(
        _run_prediction(sym1), _run_prediction(sym2), return_exceptions=True
    )
    res1 = r1[0] if not isinstance(r1, Exception) else None
    res2 = r2[0] if not isinstance(r2, Exception) else None

    if res1 is None or res2 is None:
        return f"⚠️ Could not fetch data for one or both symbols ({sym1}, {sym2})."
    return resp.build_compare_response(sym1, res1, sym2, res2)


async def _handle_risk(intent: Intent) -> str:
    risk_data, pred_tuple = await asyncio.gather(
        analyze_risk(intent.symbol), _run_prediction(intent.symbol), return_exceptions=True
    )
    if isinstance(risk_data, Exception) or not risk_data or risk_data.get("error"):
        return f"⚠️ Could not fetch risk data for **{intent.symbol}**."
    result = pred_tuple[0] if not isinstance(pred_tuple, Exception) else None
    if result is None:
        return f"⚠️ Not enough data to analyze **{intent.symbol}**."
    return resp.build_risk_response(intent.symbol, risk_data, result)


async def _handle_market(_intent: Intent) -> str:
    movers = await get_market_movers()
    return resp.build_market_response(movers)


async def _handle_recommendation(intent: Intent) -> str:
    # Full dashboard stock list with name + sector metadata
    SCAN_LIST = [
        {"symbol": "AAPL",  "name": "Apple Inc.",            "sector": "Technology"},
        {"symbol": "MSFT",  "name": "Microsoft Corp.",        "sector": "Technology"},
        {"symbol": "NVDA",  "name": "NVIDIA Corp.",           "sector": "Semiconductors"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.",          "sector": "Technology"},
        {"symbol": "META",  "name": "Meta Platforms",         "sector": "Social Media"},
        {"symbol": "AMZN",  "name": "Amazon.com Inc.",        "sector": "Consumer"},
        {"symbol": "TSLA",  "name": "Tesla Inc.",             "sector": "EV / Auto"},
        {"symbol": "AMD",   "name": "Advanced Micro Devices", "sector": "Semiconductors"},
        {"symbol": "NFLX",  "name": "Netflix Inc.",           "sector": "Streaming"},
        {"symbol": "ORCL",  "name": "Oracle Corp.",           "sector": "Cloud / Software"},
        {"symbol": "CRM",   "name": "Salesforce Inc.",        "sector": "Cloud / CRM"},
        {"symbol": "JPM",   "name": "JPMorgan Chase",         "sector": "Banking"},
        {"symbol": "V",     "name": "Visa Inc.",              "sector": "Fintech"},
        {"symbol": "SPY",   "name": "S&P 500 ETF",            "sector": "ETF / Index"},
        {"symbol": "QQQ",   "name": "NASDAQ 100 ETF",         "sector": "ETF / Tech"},
        {"symbol": "JNJ",   "name": "Johnson & Johnson",      "sector": "Healthcare"},
        {"symbol": "XOM",   "name": "ExxonMobil Corp.",       "sector": "Energy"},
        {"symbol": "WMT",   "name": "Walmart Inc.",           "sector": "Retail"},
        {"symbol": "BAC",   "name": "Bank of America",        "sector": "Banking"},
        {"symbol": "PFE",   "name": "Pfizer Inc.",            "sector": "Pharma"},
    ]

    async def _score_one(entry: dict) -> dict | None:
        sym = entry["symbol"]
        try:
            result, _ = await _run_prediction(sym)
            if result:
                # Use live price from indicators (fetched during prediction)
                live_price = result.indicators.get("price", 0)
                return {
                    "symbol":     sym,
                    "name":       entry["name"],
                    "sector":     entry["sector"],
                    "signal":     result.signal,
                    "score":      result.score,
                    "confidence": result.confidence,
                    "entry":      result.entry,
                    "target":     result.target,
                    "stop_loss":  result.stop_loss,
                    "upside_pct": result.upside_pct,
                    "price":      live_price,
                }
        except Exception:
            pass
        return None

    results = await asyncio.gather(*[_score_one(s) for s in SCAN_LIST], return_exceptions=True)
    picks = [r for r in results if r and not isinstance(r, Exception)]

    # Apply sort based on intent modifier
    if intent.sort_by == "price_asc":
        picks.sort(key=lambda x: x.get("price", 0) or x.get("entry", 0))
    elif intent.sort_by == "price_desc":
        picks.sort(key=lambda x: x.get("price", 0) or x.get("entry", 0), reverse=True)
    else:
        picks.sort(key=lambda x: x["score"], reverse=True)

    # Clamp to requested count
    count = getattr(intent, "count", 5)

    if intent.budget:
        affordable = [p for p in picks if 0 < p.get("price", 0) <= intent.budget]
        return resp.build_budget_response(intent.budget, (affordable if affordable else picks)[:count])

    return resp.build_recommendation_response(picks[:count], intent)


async def _handle_education(intent: Intent, memory_history: list[dict]) -> str:
    """Use Gemini for education queries — richer explanations than static templates."""
    gemini = await _gemini_response(intent.raw, "", memory_history)
    if gemini:
        return gemini
    # Fallback to static templates
    return resp.build_education_response(intent.raw)


# ── Intent dispatch ────────────────────────────────────────────────────────────

_HANDLERS = {
    "PRICE":          _handle_price,
    "PREDICTION":     _handle_prediction,
    "COMPARE":        _handle_compare,
    "RISK":           _handle_risk,
    "MARKET":         _handle_market,
    "RECOMMENDATION": _handle_recommendation,
    "BUDGET":         _handle_recommendation,
}


# ── Main entry point ───────────────────────────────────────────────────────────

def _build_explain_fallback(last_response: str) -> str:
    """Structured fallback explanation when Gemini is unavailable."""
    return (
        "## 📖 Explanation of Previous Result\n\n"
        "Here's what each metric means:\n\n"
        "- **Signal** (BUY / SELL / HOLD) — the overall recommendation based on all indicators combined\n"
        "- **Score /100** — composite strength of the signal; higher = stronger conviction\n"
        "- **Confidence %** — how many individual indicators agree with the signal\n"
        "- **Price** — the live market price at the time of analysis\n"
        "- **Entry** — the suggested price to open your position\n"
        "- **Target** — the projected price where you should take profit\n"
        "- **Stop Loss** — the price where you should exit to limit your loss\n"
        "- **Upside %** — potential gain from Entry to Target; negative means the signal is bearish\n"
        "- **Shares per $1k** — how many whole shares you can buy with $1,000\n\n"
        f"---\n*Previous result for reference:*\n\n{last_response}\n\n"
        "*Not financial advice. Always do your own research.*"
    )


async def chat(prompt: str, user_id: str = "anonymous", symbol: str | None = None) -> str:
    # ── Step 1: Classify — reject non-stock queries immediately ───────────────
    is_stock, detected_ticker = classify(prompt)
    if not is_stock:
        return REJECTION_MESSAGE

    # ── Step 2: Memory — resolve pronouns ("it", "that stock") ───────────────
    memory = get_memory(user_id)
    context_symbol = symbol or memory.get_context_symbol()

    # ── Step 2b: Follow-up shortcut — "explain this", "what does that mean" ──
    if _is_followup(prompt) and memory.last_response:
        system_explain = (
            "You are TradeMind AI, a professional stock market analyst. "
            "The user is asking you to explain the previous response shown below. "
            "Break down every metric clearly in plain English: Score, Confidence, "
            "Entry, Target, Stop Loss, Upside %, Signal, and Shares per $1k. "
            "Use bullet points. Be concise. "
            "End with: *Not financial advice. Always do your own research.*\n\n"
            f"=== PREVIOUS RESPONSE ===\n{memory.last_response}"
        )
        # Temporarily override system prompt by injecting context into history
        explain_history = memory.get_history()
        explanation = await _gemini_response(prompt, memory.last_response, explain_history)
        if not explanation:
            explanation = _build_explain_fallback(memory.last_response)
        memory.add(prompt=prompt, response=explanation, symbol=context_symbol, intent="EDUCATION")
        return explanation

    # ── Step 3: Detect intent ─────────────────────────────────────────────────
    intent = detect_intent(prompt, context_symbol)

    # Symbol resolution priority: frontend hint > intent > classifier > memory
    if symbol and not intent.symbol:
        intent.symbol = symbol.upper()
    if not intent.symbol and detected_ticker:
        intent.symbol = detected_ticker

    # ── Step 4: Dispatch ──────────────────────────────────────────────────────
    try:
        if intent.type == "EDUCATION":
            response_text = await _handle_education(intent, memory.get_history())

        elif intent.type in ("RECOMMENDATION", "BUDGET"):
            response_text = await _handle_recommendation(intent)

        elif intent.type == "MARKET":
            response_text = await _handle_market(intent)

        elif intent.type in ("UNKNOWN",) and not intent.symbol:
            # Generic stock question with no symbol — let Gemini handle it
            response_text = await _gemini_response(prompt, "", memory.get_history()) \
                            or await _handle_recommendation(intent)

        else:
            # All symbol-specific intents need a symbol
            if not intent.symbol:
                return (
                    "Please specify a stock symbol or company name. "
                    "Example: *\"Analyze AAPL\"* or *\"Should I buy Tesla?\"*"
                )

            handler = _HANDLERS.get(intent.type)
            if handler:
                response_text = await handler(intent)
            else:
                # Dynamic query with a symbol — fetch context and use Gemini
                quote, pred = await asyncio.gather(
                    get_stock_quote(intent.symbol),
                    _run_prediction(intent.symbol),
                    return_exceptions=True,
                )
                context_parts = []
                if not isinstance(quote, Exception) and quote and "error" not in quote:
                    context_parts.append(
                        f"{intent.symbol} — Price: ${quote.get('price', 0):.2f} | "
                        f"Change: {quote.get('change_pct', 0):+.2f}%"
                    )
                if not isinstance(pred, Exception) and pred[0]:
                    r = pred[0]
                    context_parts.append(
                        f"Signal: {r.signal} | Score: {r.score:.0f}/100 | "
                        f"Entry: ${r.entry:.2f} | Target: ${r.target:.2f} | "
                        f"Stop: ${r.stop_loss:.2f}"
                    )
                ctx = "\n".join(context_parts)
                response_text = await _gemini_response(prompt, ctx, memory.get_history()) \
                                or resp.build_prediction_response(pred[0], intent) if not isinstance(pred, Exception) and pred[0] \
                                else f"⚠️ Could not analyze **{intent.symbol}**. Please try again."

    except Exception as e:
        response_text = (
            f"⚠️ An error occurred while analyzing your request. "
            f"Please try again. *(Error: {type(e).__name__})*"
        )

    # ── Step 5: Store in memory ───────────────────────────────────────────────
    memory.add(
        prompt=prompt,
        response=response_text,
        symbol=intent.symbol,
        intent=intent.type,
    )

    return response_text
