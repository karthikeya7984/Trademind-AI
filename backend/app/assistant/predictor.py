"""
predictor.py
────────────
Stock Intelligence Prediction Engine.

Scoring formula (no LLM):
  Final Score = 0.25×RSI + 0.20×MACD + 0.15×EMA_Trend
              + 0.10×Volume + 0.10×ADX + 0.10×Bollinger
              + 0.10×Momentum

Score → Decision:
  ≥ 80  → STRONG BUY
  65-79 → BUY
  45-64 → HOLD
  25-44 → SELL
  < 25  → STRONG SELL

Confidence = how strongly the indicators agree (0-100%).
"""

import math
import numpy as np
import pandas as pd
from dataclasses import dataclass


@dataclass
class PredictionResult:
    symbol:       str
    signal:       str        # STRONG BUY | BUY | HOLD | SELL | STRONG SELL
    score:        float      # 0-100
    confidence:   float      # 0-100 %
    entry:        float
    target:       float
    stop_loss:    float
    upside_pct:   float
    risk_reward:  float
    trend:        str        # bullish | bearish | sideways
    reasons:      list[str]  # human-readable reasons
    warnings:     list[str]  # risk warnings
    indicators:   dict       # raw indicator values
    signal_scores: dict      # per-indicator scores


def _safe(v, default=0.0) -> float:
    try:
        f = float(v)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except Exception:
        return default


# ── Individual indicator scorers (each returns 0-100) ─────────────────────────

def _score_rsi(rsi: float) -> tuple[float, str]:
    """RSI score + reason."""
    if rsi <= 20:   return 95, f"RSI {rsi:.1f} — extremely oversold, strong bounce potential"
    if rsi <= 30:   return 85, f"RSI {rsi:.1f} — oversold, buyers likely stepping in"
    if rsi <= 40:   return 65, f"RSI {rsi:.1f} — approaching oversold territory"
    if rsi <= 55:   return 50, f"RSI {rsi:.1f} — neutral zone"
    if rsi <= 65:   return 40, f"RSI {rsi:.1f} — slightly elevated, watch for reversal"
    if rsi <= 75:   return 25, f"RSI {rsi:.1f} — overbought, pullback risk elevated"
    return 10,              f"RSI {rsi:.1f} — extremely overbought, high reversal risk"


def _score_macd(macd: float, signal: float, hist: float, prev_hist: float) -> tuple[float, str]:
    """MACD score + reason."""
    crossover_bull = hist > 0 and prev_hist <= 0
    crossover_bear = hist < 0 and prev_hist >= 0

    if crossover_bull and macd > 0:  return 95, "MACD bullish crossover above zero — strong buy signal"
    if crossover_bull:               return 80, "MACD bullish crossover — momentum turning positive"
    if crossover_bear and macd < 0:  return 5,  "MACD bearish crossover below zero — strong sell signal"
    if crossover_bear:               return 20, "MACD bearish crossover — momentum turning negative"
    if macd > signal and hist > 0:   return 65, f"MACD ({macd:.3f}) above signal — bullish momentum"
    if macd < signal and hist < 0:   return 35, f"MACD ({macd:.3f}) below signal — bearish pressure"
    return 50, "MACD neutral"


def _score_ema_trend(price: float, ema20: float, ema50: float, ema200: float) -> tuple[float, str]:
    """EMA trend score + reason."""
    above_20  = price > ema20
    above_50  = price > ema50
    above_200 = price > ema200
    golden    = ema50 > ema200
    death     = ema50 < ema200

    count = sum([above_20, above_50, above_200])

    if count == 3 and golden:
        return 90, f"Price above EMA20/50/200 with golden cross — strong uptrend"
    if count == 3:
        return 75, f"Price above all EMAs — uptrend intact"
    if count == 2:
        return 60, f"Price above EMA20 & EMA50 — moderate bullish trend"
    if count == 1:
        return 40, f"Price only above EMA20 — weak trend"
    if count == 0 and death:
        return 10, f"Price below all EMAs with death cross — strong downtrend"
    return 25, f"Price below key EMAs — bearish trend"


def _score_volume(vol_ratio: float, price_change: float) -> tuple[float, str]:
    """Volume confirmation score + reason."""
    if vol_ratio >= 2.0 and price_change > 0:
        return 90, f"Volume {vol_ratio:.1f}x average with price up — strong buying pressure"
    if vol_ratio >= 1.5 and price_change > 0:
        return 75, f"Volume {vol_ratio:.1f}x average — buyers active"
    if vol_ratio >= 2.0 and price_change < 0:
        return 10, f"Volume {vol_ratio:.1f}x average with price down — heavy selling"
    if vol_ratio >= 1.5 and price_change < 0:
        return 25, f"Volume {vol_ratio:.1f}x average — sellers active"
    if vol_ratio < 0.5:
        return 50, f"Low volume ({vol_ratio:.1f}x) — weak conviction"
    return 50, f"Volume {vol_ratio:.1f}x average — normal"


def _score_adx(adx: float, plus_di: float, minus_di: float) -> tuple[float, str]:
    """ADX trend strength score + reason."""
    if adx < 20:
        return 50, f"ADX {adx:.1f} — no clear trend, ranging market"
    if adx >= 40 and plus_di > minus_di:
        return 85, f"ADX {adx:.1f} — very strong uptrend"
    if adx >= 40 and plus_di < minus_di:
        return 15, f"ADX {adx:.1f} — very strong downtrend"
    if adx >= 25 and plus_di > minus_di:
        return 70, f"ADX {adx:.1f} — strong uptrend confirmed"
    if adx >= 25 and plus_di < minus_di:
        return 30, f"ADX {adx:.1f} — strong downtrend confirmed"
    return 50, f"ADX {adx:.1f} — weak trend"


def _score_bollinger(bb_pct: float, bb_width: float) -> tuple[float, str]:
    """Bollinger Band position score + reason."""
    if bb_pct <= 0.05:   return 90, f"Price at lower Bollinger Band ({bb_pct*100:.0f}%) — oversold, mean reversion likely"
    if bb_pct <= 0.20:   return 75, f"Price near lower band ({bb_pct*100:.0f}%) — potential bounce zone"
    if bb_pct <= 0.40:   return 60, f"Price in lower half of bands ({bb_pct*100:.0f}%)"
    if bb_pct <= 0.60:   return 50, f"Price mid-band ({bb_pct*100:.0f}%) — neutral"
    if bb_pct <= 0.80:   return 40, f"Price in upper half of bands ({bb_pct*100:.0f}%)"
    if bb_pct <= 0.95:   return 25, f"Price near upper band ({bb_pct*100:.0f}%) — overbought warning"
    return 10,               f"Price at upper Bollinger Band ({bb_pct*100:.0f}%) — overbought"


def _score_momentum(roc10: float, momentum10: float) -> tuple[float, str]:
    """Momentum score + reason."""
    if roc10 >= 5:    return 80, f"Strong positive momentum +{roc10:.1f}% over 10 days"
    if roc10 >= 2:    return 65, f"Positive momentum +{roc10:.1f}% over 10 days"
    if roc10 >= -2:   return 50, f"Flat momentum {roc10:.1f}% over 10 days"
    if roc10 >= -5:   return 35, f"Negative momentum {roc10:.1f}% over 10 days"
    return 20,            f"Strong negative momentum {roc10:.1f}% over 10 days"


# ── Price target calculator ────────────────────────────────────────────────────

def _calculate_targets(price: float, atr: float, signal: str,
                        bb_upper: float, bb_lower: float, ema50: float) -> tuple[float, float, float]:
    """Returns (entry, target, stop_loss)."""
    atr = atr or price * 0.02

    if signal in ("STRONG BUY", "BUY"):
        entry     = round(price * 1.001, 2)
        target    = round(min(bb_upper or price * 1.06, price + atr * 3), 2)
        stop_loss = round(max(bb_lower or price * 0.94, price - atr * 1.5), 2)
    elif signal in ("STRONG SELL", "SELL"):
        entry     = round(price * 0.999, 2)
        target    = round(max(bb_lower or price * 0.94, price - atr * 3), 2)
        stop_loss = round(min(bb_upper or price * 1.06, price + atr * 1.5), 2)
    else:
        entry     = round(price, 2)
        target    = round(ema50 or price * 1.02, 2)
        stop_loss = round(price - atr * 2, 2)

    return entry, target, stop_loss


# ── Main prediction function ───────────────────────────────────────────────────

def predict(symbol: str, ind: dict, news_score: float = 0.0) -> PredictionResult:
    """
    Run the full scoring formula on computed indicators.
    ind: output of indicators.compute_all()
    news_score: sentiment score -1..1 from news_service
    """
    price      = _safe(ind.get("price"), 100)
    prev_close = _safe(ind.get("prev_close"), price)
    rsi        = _safe(ind.get("rsi"), 50)
    macd       = _safe(ind.get("macd"), 0)
    macd_sig   = _safe(ind.get("macd_signal"), 0)
    macd_hist  = _safe(ind.get("macd_hist"), 0)
    macd_prev  = _safe(ind.get("macd_prev_hist"), 0)
    ema20      = _safe(ind.get("ema20"), price)
    ema50      = _safe(ind.get("ema50"), price)
    ema200     = _safe(ind.get("ema200"), price)
    vol_ratio  = _safe(ind.get("vol_ratio"), 1.0)
    adx        = _safe(ind.get("adx"), 20)
    plus_di    = _safe(ind.get("plus_di"), 25)
    minus_di   = _safe(ind.get("minus_di"), 25)
    bb_pct     = _safe(ind.get("bb_pct"), 0.5)
    bb_width   = _safe(ind.get("bb_width"), 0.05)
    bb_upper   = _safe(ind.get("bb_upper"), price * 1.05)
    bb_lower   = _safe(ind.get("bb_lower"), price * 0.95)
    roc10      = _safe(ind.get("roc10"), 0)
    momentum10 = _safe(ind.get("momentum10"), 0)
    atr        = _safe(ind.get("atr"), price * 0.02)
    price_chg  = price - prev_close

    # ── Score each component ──────────────────────────────────────────────────
    rsi_score,  rsi_reason  = _score_rsi(rsi)
    macd_score, macd_reason = _score_macd(macd, macd_sig, macd_hist, macd_prev)
    ema_score,  ema_reason  = _score_ema_trend(price, ema20, ema50, ema200)
    vol_score,  vol_reason  = _score_volume(vol_ratio, price_chg)
    adx_score,  adx_reason  = _score_adx(adx, plus_di, minus_di)
    bb_score,   bb_reason   = _score_bollinger(bb_pct, bb_width)
    mom_score,  mom_reason  = _score_momentum(roc10, momentum10)

    # News sentiment → 0-100
    news_score_100 = 50 + (news_score * 50)

    # ── Weighted composite score ──────────────────────────────────────────────
    weights = {
        "rsi":      0.25,
        "macd":     0.20,
        "ema":      0.15,
        "volume":   0.10,
        "adx":      0.10,
        "bollinger":0.10,
        "momentum": 0.10,
    }
    scores = {
        "rsi": rsi_score, "macd": macd_score, "ema": ema_score,
        "volume": vol_score, "adx": adx_score, "bollinger": bb_score,
        "momentum": mom_score,
    }
    final_score = sum(scores[k] * weights[k] for k in weights)
    # Blend in news (5% weight)
    final_score = final_score * 0.95 + news_score_100 * 0.05
    final_score = round(final_score, 1)

    # ── Signal decision ───────────────────────────────────────────────────────
    if   final_score >= 80: signal = "STRONG BUY"
    elif final_score >= 65: signal = "BUY"
    elif final_score >= 45: signal = "HOLD"
    elif final_score >= 25: signal = "SELL"
    else:                   signal = "STRONG SELL"

    # ── Confidence: how many indicators agree with the signal ─────────────────
    bullish_count = sum(1 for s in scores.values() if s >= 60)
    bearish_count = sum(1 for s in scores.values() if s <= 40)
    total = len(scores)
    if signal in ("STRONG BUY", "BUY"):
        confidence = round((bullish_count / total) * 100, 1)
    elif signal in ("STRONG SELL", "SELL"):
        confidence = round((bearish_count / total) * 100, 1)
    else:
        neutral = total - bullish_count - bearish_count
        confidence = round((neutral / total) * 100, 1)

    # ── Trend ─────────────────────────────────────────────────────────────────
    if ema20 > ema50 > ema200:   trend = "bullish"
    elif ema20 < ema50 < ema200: trend = "bearish"
    else:                        trend = "sideways"

    # ── Price targets ─────────────────────────────────────────────────────────
    entry, target, stop_loss = _calculate_targets(
        price, atr, signal, bb_upper, bb_lower, ema50
    )
    upside_pct  = round((target - entry) / entry * 100, 2) if entry else 0
    risk        = abs(entry - stop_loss)
    reward      = abs(target - entry)
    risk_reward = round(reward / risk, 2) if risk > 0 else 0

    # ── Build reasons (top 3 strongest signals) ───────────────────────────────
    reason_map = [
        (rsi_score,  rsi_reason,  "rsi"),
        (macd_score, macd_reason, "macd"),
        (ema_score,  ema_reason,  "ema"),
        (vol_score,  vol_reason,  "volume"),
        (adx_score,  adx_reason,  "adx"),
        (bb_score,   bb_reason,   "bollinger"),
        (mom_score,  mom_reason,  "momentum"),
    ]
    # Sort by distance from 50 (strongest signal first)
    reason_map.sort(key=lambda x: abs(x[0] - 50), reverse=True)
    reasons = [r[1] for r in reason_map[:4]]

    # ── Warnings ──────────────────────────────────────────────────────────────
    warnings = []
    if rsi > 70:   warnings.append(f"⚠️ RSI overbought ({rsi:.1f}) — consider waiting for pullback")
    if rsi < 30:   warnings.append(f"⚠️ RSI oversold ({rsi:.1f}) — high volatility expected")
    if adx < 20:   warnings.append("⚠️ Low ADX — market is ranging, signals less reliable")
    if vol_ratio < 0.5: warnings.append("⚠️ Low volume — weak conviction in current move")
    if risk_reward < 1.5 and signal in ("BUY", "STRONG BUY"):
        warnings.append(f"⚠️ Risk/Reward ratio {risk_reward:.1f} — consider tighter stop-loss")

    return PredictionResult(
        symbol=symbol,
        signal=signal,
        score=final_score,
        confidence=confidence,
        entry=entry,
        target=target,
        stop_loss=stop_loss,
        upside_pct=upside_pct,
        risk_reward=risk_reward,
        trend=trend,
        reasons=reasons,
        warnings=warnings,
        indicators=ind,
        signal_scores=scores,
    )
