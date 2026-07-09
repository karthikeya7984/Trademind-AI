"""
assistant.py
────────────
Main Stock AI Engine orchestrator.

Flow:
  1. classify()     — is it stock-related? if not, reject immediately
  2. detect_intent()— what does the user want?
  3. fetch data     — Alpha Vantage / yfinance via existing market_service
  4. compute_all()  — full indicator suite
  5. predict()      — weighted scoring formula → signal + confidence
  6. build_*()      — structured markdown response, no LLM
  7. memory.add()   — store turn for pronoun resolution
"""

import asyncio
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
    """Returns sentiment score -1..1, never raises."""
    try:
        result = await asyncio.wait_for(get_symbol_sentiment(symbol), timeout=4.0)
        return float((result or {}).get("score", 0.0))
    except Exception:
        return 0.0


async def _build_indicators(symbol: str) -> tuple[dict, list[dict]]:
    """Fetch 6-month history and compute all indicators. Returns (ind_dict, raw_history)."""
    history = await get_historical_data(symbol.replace(".", "-"), period="6mo", interval="1d")
    if not history or len(history) < 20:
        return {}, history or []
    df = pd.DataFrame(history)
    ind = compute_all(df)
    return ind, history


async def _run_prediction(symbol: str) -> tuple:
    """Returns (PredictionResult | None, indicators_dict)."""
    ind, _ = await _build_indicators(symbol)
    if not ind:
        return None, {}
    news_score = await _safe_news_score(symbol)
    result = predict(symbol, ind, news_score)
    return result, ind


# ── Intent handlers ────────────────────────────────────────────────────────────

async def _handle_price(intent: Intent) -> str:
    symbol = intent.symbol
    quote = await get_stock_quote(symbol)
    if not quote or quote.get("error") or not quote.get("price"):
        return f"⚠️ Could not fetch price for **{symbol}**. It may be an invalid ticker or market is closed."
    return resp.build_price_response(symbol, quote)


async def _handle_prediction(intent: Intent) -> str:
    symbol = intent.symbol
    result, _ = await _run_prediction(symbol)
    if result is None:
        return (
            f"⚠️ Not enough historical data to analyze **{symbol}**. "
            "Please check the ticker symbol and try again."
        )
    return resp.build_prediction_response(result, intent)


async def _handle_compare(intent: Intent) -> str:
    sym1, sym2 = intent.symbol, intent.symbol2
    if not sym2:
        return f"Please specify two stocks to compare. Example: *\"Compare AAPL and MSFT\"*"

    r1, r2 = await asyncio.gather(
        _run_prediction(sym1),
        _run_prediction(sym2),
        return_exceptions=True,
    )
    res1 = r1[0] if not isinstance(r1, Exception) else None
    res2 = r2[0] if not isinstance(r2, Exception) else None

    if res1 is None or res2 is None:
        return f"⚠️ Could not fetch data for one or both symbols ({sym1}, {sym2}). Please check the tickers."
    return resp.build_compare_response(sym1, res1, sym2, res2)


async def _handle_risk(intent: Intent) -> str:
    symbol = intent.symbol
    risk_data, pred_tuple = await asyncio.gather(
        analyze_risk(symbol),
        _run_prediction(symbol),
        return_exceptions=True,
    )
    if isinstance(risk_data, Exception) or not risk_data or risk_data.get("error"):
        return f"⚠️ Could not fetch risk data for **{symbol}**."
    result = pred_tuple[0] if not isinstance(pred_tuple, Exception) else None
    if result is None:
        return f"⚠️ Not enough data to analyze **{symbol}**."
    return resp.build_risk_response(symbol, risk_data, result)


async def _handle_market(_intent: Intent) -> str:
    movers = await get_market_movers()
    return resp.build_market_response(movers)


async def _handle_recommendation(intent: Intent) -> str:
    # Scan a curated watchlist and return top picks by score
    SCAN_LIST = [
        "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "AMD",
        "NFLX", "ORCL", "CRM", "JPM", "V", "SPY", "QQQ",
    ]

    async def _score_one(sym: str) -> dict | None:
        try:
            result, _ = await _run_prediction(sym)
            if result:
                return {
                    "symbol":     sym,
                    "signal":     result.signal,
                    "score":      result.score,
                    "confidence": result.confidence,
                    "entry":      result.entry,
                    "target":     result.target,
                    "stop_loss":  result.stop_loss,
                    "upside_pct": result.upside_pct,
                    "price":      result.indicators.get("price", 0),
                }
        except Exception:
            pass
        return None

    results = await asyncio.gather(*[_score_one(s) for s in SCAN_LIST], return_exceptions=True)
    # Include ALL picks sorted by score — not just BUY signals
    picks = [r for r in results if r and not isinstance(r, Exception)]
    picks.sort(key=lambda x: x["score"], reverse=True)

    # Budget filter
    if intent.budget:
        affordable = [p for p in picks if p.get("price", 0) <= intent.budget]
        if affordable:
            return resp.build_budget_response(intent.budget, affordable)
        return resp.build_budget_response(intent.budget, picks[:5])  # show best even if over budget

    return resp.build_recommendation_response(picks)


async def _handle_budget(intent: Intent) -> str:
    # Reuse recommendation handler — it already handles budget filtering
    return await _handle_recommendation(intent)


async def _handle_education(intent: Intent) -> str:
    return resp.build_education_response(intent.raw)


# ── Intent dispatch table ──────────────────────────────────────────────────────

_HANDLERS = {
    "PRICE":          _handle_price,
    "PREDICTION":     _handle_prediction,
    "COMPARE":        _handle_compare,
    "RISK":           _handle_risk,
    "MARKET":         _handle_market,
    "RECOMMENDATION": _handle_recommendation,
    "BUDGET":         _handle_budget,
    "EDUCATION":      _handle_education,
}


# ── Main entry point ───────────────────────────────────────────────────────────

async def chat(prompt: str, user_id: str = "anonymous", symbol: str | None = None) -> str:
    """
    Main chat function — drop-in replacement for ai_service.chat_with_ai().

    Args:
        prompt:  User's message
        user_id: Used for per-user conversation memory
        symbol:  Optional symbol hint from frontend (e.g. user is on AAPL page)

    Returns:
        Markdown-formatted response string
    """
    # ── Step 1: Classify ──────────────────────────────────────────────────────
    is_stock, detected_ticker = classify(prompt)
    if not is_stock:
        return REJECTION_MESSAGE

    # ── Step 2: Memory — resolve pronouns ("it", "now", "that stock") ─────────
    memory = get_memory(user_id)
    context_symbol = symbol or memory.get_context_symbol()

    # ── Step 3: Detect intent ─────────────────────────────────────────────────
    intent = detect_intent(prompt, context_symbol)

    # Symbol override: frontend-provided symbol takes priority
    if symbol and not intent.symbol:
        intent.symbol = symbol.upper()
    # Fallback: use detected ticker from classifier
    if not intent.symbol and detected_ticker:
        intent.symbol = detected_ticker

    # ── Step 4: Dispatch to handler ───────────────────────────────────────────
    handler = _HANDLERS.get(intent.type, _handle_prediction)

    # EDUCATION, MARKET, RECOMMENDATION, BUDGET don't need a specific symbol
    if intent.type not in ("EDUCATION", "MARKET", "RECOMMENDATION", "BUDGET", "UNKNOWN") and not intent.symbol:
        return (
            "Please specify a stock symbol or company name. "
            "Example: *\"Analyze AAPL\"* or *\"Should I buy Tesla?\"*"
        )

    # UNKNOWN with no symbol and no budget → helpful fallback
    if intent.type == "UNKNOWN" and not intent.symbol:
        return await _handle_recommendation(intent)

    try:
        response_text = await handler(intent)
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
