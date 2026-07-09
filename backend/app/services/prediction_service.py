import asyncio
import numpy as np
import pandas as pd
import json
from app.services.market_service import get_historical_data
from app.services.news_service import get_symbol_sentiment
from app.core.redis import cache_get, cache_set


# ── Technical Indicators ──────────────────────────────────────────────────────

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close  = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series([1] * len(df), index=df.index)
    high   = df["high"]   if "high"   in df.columns else close * 1.01
    low    = df["low"]    if "low"    in df.columns else close * 0.99

    df["ma10"]  = close.rolling(10).mean()
    df["ma20"]  = close.rolling(20).mean()
    df["ma50"]  = close.rolling(50).mean()
    df["ma200"] = close.rolling(200).mean()
    df["ema9"]  = close.ewm(span=9,  adjust=False).mean()
    df["ema21"] = close.ewm(span=21, adjust=False).mean()

    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    df["rsi"] = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd"]        = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]   = df["macd"] - df["macd_signal"]

    df["bb_mid"]   = close.rolling(20).mean()
    std20          = close.rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * std20
    df["bb_lower"] = df["bb_mid"] - 2 * std20
    bb_range       = (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
    df["bb_pct"]   = (close - df["bb_lower"]) / bb_range

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs(),
    ], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()

    vol_s           = pd.to_numeric(volume, errors="coerce").fillna(1)
    df["vol_ma20"]  = vol_s.rolling(20).mean()
    df["vol_ratio"] = vol_s / df["vol_ma20"].replace(0, np.nan)

    low14          = low.rolling(14).min()
    high14         = high.rolling(14).max()
    df["stoch_k"]  = 100 * (close - low14) / (high14 - low14).replace(0, np.nan)
    df["stoch_d"]  = df["stoch_k"].rolling(3).mean()

    df["roc10"] = close.pct_change(10) * 100
    df["roc20"] = close.pct_change(20) * 100
    return df


# ── Signal Scoring ────────────────────────────────────────────────────────────

def score_signals(df: pd.DataFrame, news_sentiment: float = 0.0) -> dict:
    row   = df.iloc[-1]
    prev  = df.iloc[-2] if len(df) > 1 else row
    close = float(row["close"])

    def g(key, default=0.0):
        v = row.get(key, default)
        return default if (v is None or (isinstance(v, float) and np.isnan(v))) else float(v)

    def gp(key, default=0.0):
        v = prev.get(key, default)
        return default if (v is None or (isinstance(v, float) and np.isnan(v))) else float(v)

    signals = {}

    rsi = g("rsi", 50)
    if   rsi < 30: signals["rsi"] =  1.0
    elif rsi < 40: signals["rsi"] =  0.5
    elif rsi > 70: signals["rsi"] = -1.0
    elif rsi > 60: signals["rsi"] = -0.5
    else:          signals["rsi"] =  0.0

    macd, macd_sig, macd_hist, prev_hist = g("macd"), g("macd_signal"), g("macd_hist"), gp("macd_hist")
    if   macd > macd_sig and prev_hist <= 0 and macd_hist > 0: signals["macd"] =  1.0
    elif macd < macd_sig and prev_hist >= 0 and macd_hist < 0: signals["macd"] = -1.0
    elif macd > macd_sig:                                       signals["macd"] =  0.4
    elif macd < macd_sig:                                       signals["macd"] = -0.4
    else:                                                       signals["macd"] =  0.0

    bb_pct = g("bb_pct", 0.5)
    if   bb_pct < 0.10: signals["bollinger"] =  1.0
    elif bb_pct < 0.25: signals["bollinger"] =  0.5
    elif bb_pct > 0.90: signals["bollinger"] = -1.0
    elif bb_pct > 0.75: signals["bollinger"] = -0.5
    else:               signals["bollinger"] =  0.0

    ma10, ma20, ma50, ma200 = g("ma10", close), g("ma20", close), g("ma50", close), g("ma200", close)
    prev_ma10, prev_ma20    = gp("ma10", ma10), gp("ma20", ma20)
    if   ma10 > ma20 and prev_ma10 <= prev_ma20: signals["ma_cross"] =  1.0
    elif ma10 < ma20 and prev_ma10 >= prev_ma20: signals["ma_cross"] = -1.0
    elif close > ma50 and close > ma200:         signals["ma_cross"] =  0.5
    elif close < ma50 and close < ma200:         signals["ma_cross"] = -0.5
    elif close > ma50:                           signals["ma_cross"] =  0.3
    elif close < ma50:                           signals["ma_cross"] = -0.3
    else:                                        signals["ma_cross"] =  0.0

    vol_ratio    = g("vol_ratio", 1.0)
    price_change = close - float(prev["close"]) if float(prev["close"]) else 0
    if   vol_ratio > 1.5 and price_change > 0: signals["volume"] =  0.8
    elif vol_ratio > 1.5 and price_change < 0: signals["volume"] = -0.8
    elif vol_ratio < 0.5:                      signals["volume"] =  0.0
    else:                                      signals["volume"] =  0.1 if price_change > 0 else -0.1

    stoch_k, stoch_d = g("stoch_k", 50), g("stoch_d", 50)
    if   stoch_k < 20 and stoch_d < 20:      signals["stochastic"] =  1.0
    elif stoch_k > 80 and stoch_d > 80:      signals["stochastic"] = -1.0
    elif stoch_k > stoch_d and stoch_k < 50: signals["stochastic"] =  0.4
    elif stoch_k < stoch_d and stoch_k > 50: signals["stochastic"] = -0.4
    else:                                    signals["stochastic"] =  0.0

    signals["news"] = max(-1.0, min(1.0, news_sentiment * 2))

    weights = {
        "rsi": 0.20, "macd": 0.22, "bollinger": 0.15,
        "ma_cross": 0.22, "volume": 0.10, "stochastic": 0.08, "news": 0.03,
    }
    composite = sum(signals[k] * weights[k] for k in signals)
    return {"signals": signals, "composite": round(composite, 4)}


# ── Price Targets ─────────────────────────────────────────────────────────────

def calculate_price_target(df: pd.DataFrame, signal: str) -> dict:
    close   = float(df["close"].iloc[-1])
    atr_v   = df["atr"].iloc[-1]
    bb_up_v = df["bb_upper"].iloc[-1]
    bb_lo_v = df["bb_lower"].iloc[-1]
    ma50_v  = df["ma50"].iloc[-1]

    atr  = float(atr_v)   if not pd.isna(atr_v)   else close * 0.02
    bb_u = float(bb_up_v) if not pd.isna(bb_up_v) else close * 1.05
    bb_l = float(bb_lo_v) if not pd.isna(bb_lo_v) else close * 0.95
    ma50 = float(ma50_v)  if not pd.isna(ma50_v)  else close

    if signal == "BUY":
        return {"target": round(min(bb_u, close + atr * 3), 2),
                "stop_loss": round(max(bb_l, close - atr * 1.5), 2),
                "entry": round(close * 1.001, 2)}
    if signal == "SELL":
        return {"target": round(max(bb_l, close - atr * 3), 2),
                "stop_loss": round(min(bb_u, close + atr * 1.5), 2),
                "entry": round(close * 0.999, 2)}
    return {"target": round(ma50, 2), "stop_loss": round(close - atr * 2, 2), "entry": round(close, 2)}


# ── Advice Builder ────────────────────────────────────────────────────────────

def build_advice(symbol: str, score_data: dict, indicators: dict,
                 price_targets: dict, current_price: float, news_sentiment: dict) -> dict:
    composite = score_data["composite"]
    sigs      = score_data["signals"]
    rsi       = indicators.get("rsi") or 50.0
    news_lbl  = news_sentiment.get("label", "neutral")

    if composite > 0.25:
        action, urgency = "INVEST", ("HIGH" if composite > 0.55 else "MEDIUM")
    elif composite < -0.25:
        action, urgency = "WITHDRAW", ("HIGH" if composite < -0.55 else "MEDIUM")
    else:
        action, urgency = "HOLD", "LOW"

    reasons = []
    if sigs.get("rsi", 0) >= 0.5:
        reasons.append(f"RSI {rsi:.1f} oversold — buyers likely to step in")
    elif sigs.get("rsi", 0) <= -0.5:
        reasons.append(f"RSI {rsi:.1f} overbought — pullback risk elevated")

    if sigs.get("macd", 0) >= 0.8:
        reasons.append("MACD bullish crossover confirmed — momentum turning positive")
    elif sigs.get("macd", 0) > 0:
        reasons.append("MACD above signal line — bullish momentum")
    elif sigs.get("macd", 0) <= -0.8:
        reasons.append("MACD bearish crossover — downward momentum accelerating")
    elif sigs.get("macd", 0) < 0:
        reasons.append("MACD below signal line — bearish pressure")

    if sigs.get("ma_cross", 0) >= 0.8:
        reasons.append("Golden cross MA10/MA20 — strong bullish trend")
    elif sigs.get("ma_cross", 0) <= -0.8:
        reasons.append("Death cross MA10/MA20 — bearish trend confirmed")
    elif sigs.get("ma_cross", 0) > 0:
        reasons.append("Price above MA50/MA200 — uptrend intact")
    elif sigs.get("ma_cross", 0) < 0:
        reasons.append("Price below key moving averages — downtrend in effect")

    if not reasons:
        reasons.append(f"Mixed signals, composite score: {composite:+.3f}")

    reason = ". ".join(reasons[:3]) + f". Score: {composite:+.3f}."
    risk   = "HIGH" if abs(composite) > 0.55 else "MEDIUM" if abs(composite) > 0.25 else "LOW"

    return {
        "action": action, "urgency": urgency, "reason": reason,
        "entry_price": price_targets["entry"], "exit_price": price_targets["target"],
        "stop_loss": price_targets["stop_loss"], "risk_level": risk,
        "time_horizon": "SHORT" if abs(composite) > 0.50 else "MEDIUM",
        "key_factors": [
            f"RSI(14): {rsi:.1f}",
            f"MACD: {'bullish' if sigs.get('macd', 0) > 0 else 'bearish'}",
            f"Trend: {'above' if sigs.get('ma_cross', 0) > 0 else 'below'} MA50",
            f"BB: {(indicators.get('bb_pct') or 0.5)*100:.0f}% in band",
            f"News: {news_lbl}",
        ],
        "source": "algorithm",
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _safe_news(symbol: str) -> dict:
    try:
        return await get_symbol_sentiment(symbol)
    except Exception:
        return {"symbol": symbol, "score": 0.0, "label": "neutral", "article_count": 0}


# ── Main Prediction Runner ────────────────────────────────────────────────────

async def run_prediction(symbol: str, fast: bool = False) -> dict:
    """fast=True: skips news, uses 6mo history — much faster, used for batch signals."""
    symbol    = symbol.upper().strip()
    # Normalize dot to dash for yfinance (e.g. BRK.B -> BRK-B)
    yf_symbol = symbol.replace(".", "-")
    cache_key = f"pred:{'f' if fast else 'v'}:{symbol}"
    cached    = await cache_get(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass

    if fast:
        history        = await get_historical_data(yf_symbol, period="6mo", interval="1d")
        news_sentiment = {"symbol": symbol, "score": 0.0, "label": "neutral", "article_count": 0}
    else:
        # Run history + news concurrently with a 5s news timeout
        async def _news_with_timeout(sym: str) -> dict:
            try:
                return await asyncio.wait_for(_safe_news(sym), timeout=5.0)
            except Exception:
                return {"symbol": sym, "score": 0.0, "label": "neutral", "article_count": 0}

        history, news_sentiment = await asyncio.gather(
            get_historical_data(yf_symbol, period="6mo", interval="1d"),
            _news_with_timeout(symbol),
        )

    if not history:
        return {"error": f"No historical data for {symbol}.", "symbol": symbol}

    df = pd.DataFrame(history)
    df.columns = [c.lower() for c in df.columns]

    for col in ["close", "open", "high", "low", "volume"]:
        if col not in df.columns:
            df[col] = 1 if col == "volume" else None
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["close"]).reset_index(drop=True)
    if len(df) < 30:
        return {"error": f"Insufficient data for {symbol}.", "symbol": symbol}

    df            = compute_indicators(df)
    current_price = float(df["close"].iloc[-1])
    news_score    = float((news_sentiment or {}).get("score", 0.0))

    score_data = score_signals(df, news_score)
    composite  = score_data["composite"]

    if   composite >  0.15: signal = "BUY"
    elif composite < -0.15: signal = "SELL"
    else:                   signal = "HOLD"

    confidence    = round(0.50 + min(abs(composite) / 0.8, 1.0) * 0.45, 3)
    price_targets = calculate_price_target(df, signal)

    prices_20   = df["close"].tail(20).values.astype(float)
    trend_slope = float(np.polyfit(range(len(prices_20)), prices_20, 1)[0])
    trend       = "bullish" if trend_slope > 0 else "bearish"

    last = df.iloc[-1]
    def safe(val):
        try:
            f = float(val)
            return round(f, 4) if not np.isnan(f) else None
        except Exception:
            return None

    indicators = {k: safe(last.get(k)) for k in [
        "rsi", "macd", "macd_signal", "macd_hist",
        "ma10", "ma20", "ma50", "ma200",
        "bb_upper", "bb_lower", "bb_mid", "bb_pct",
        "atr", "vol_ratio", "stoch_k", "stoch_d", "roc10",
    ]}

    advice = build_advice(symbol, score_data, indicators, price_targets, current_price, news_sentiment)

    result = {
        "symbol":           symbol,
        "signal":           signal,
        "composite_score":  composite,
        "confidence_score": confidence,
        "current_price":    current_price,
        "predicted_price":  price_targets["target"],
        "entry_price":      price_targets["entry"],
        "stop_loss":        price_targets["stop_loss"],
        "trend":            trend,
        "indicators":       indicators,
        "signal_breakdown": score_data["signals"],
        "news_sentiment":   news_sentiment,
        "advice":           advice,
    }

    await cache_set(cache_key, json.dumps(result), ttl=1800)
    return result


# ── Batch Signals (for dashboard table) ──────────────────────────────────────

async def run_signals_batch(symbols: list[str]) -> dict:
    """All 50 symbols concurrently, fast mode, 30-min cache."""
    cache_key = f"sig_batch:{','.join(sorted(symbols))}"
    cached    = await cache_get(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass

    async def _one(sym: str):
        try:
            r = await run_prediction(sym, fast=True)
            return sym, {
                "signal":     r.get("signal", "HOLD"),
                "confidence": r.get("confidence_score", 0.5),
                "composite":  r.get("composite_score", 0.0),
            }
        except Exception:
            return sym, {"signal": "HOLD", "confidence": 0.5, "composite": 0.0}

    # Process in chunks of 10 to avoid overwhelming yfinance
    CHUNK = 10
    result = {}
    for i in range(0, len(symbols), CHUNK):
        chunk_pairs = await asyncio.gather(*[_one(s) for s in symbols[i:i+CHUNK]])
        result.update(dict(chunk_pairs))
    await cache_set(cache_key, json.dumps(result), ttl=1800)
    return result
