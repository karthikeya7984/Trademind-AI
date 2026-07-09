"""
indicators.py
─────────────
Full technical indicator engine.
Computes all indicators from OHLCV data and returns
a structured dict used by predictor.py and response.py.

Indicators:
  SMA20, EMA20, EMA50, EMA200
  MACD (12,26,9)
  RSI(14)
  ATR(14)
  ADX(14)
  OBV
  Bollinger Bands (20, 2σ)
  Stochastic RSI (14)
  VWAP
  Momentum(10)
  ROC(10)
  Volume Ratio
"""

import numpy as np
import pandas as pd
import math


def _safe(val) -> float | None:
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    except Exception:
        return None


def compute_all(df: pd.DataFrame) -> dict:
    """
    Input: DataFrame with columns [date, open, high, low, close, volume]
    Output: dict of all indicator values (latest bar)
    """
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"]).reset_index(drop=True)

    if len(df) < 20:
        return {}

    close  = df["close"]
    high   = df["high"]
    low    = df["low"]
    volume = df["volume"].fillna(0)

    # ── Moving Averages ────────────────────────────────────────────────────────
    sma20  = close.rolling(20).mean()
    ema9   = close.ewm(span=9,   adjust=False).mean()
    ema20  = close.ewm(span=20,  adjust=False).mean()
    ema50  = close.ewm(span=50,  adjust=False).mean()
    ema200 = close.ewm(span=200, adjust=False).mean()

    # ── MACD ──────────────────────────────────────────────────────────────────
    ema12       = close.ewm(span=12, adjust=False).mean()
    ema26       = close.ewm(span=26, adjust=False).mean()
    macd_line   = ema12 - ema26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist   = macd_line - macd_signal

    # ── RSI(14) ───────────────────────────────────────────────────────────────
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = 100 - (100 / (1 + rs))

    # ── Bollinger Bands (20, 2σ) ──────────────────────────────────────────────
    bb_mid   = close.rolling(20).mean()
    bb_std   = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    bb_range = (bb_upper - bb_lower).replace(0, np.nan)
    bb_pct   = (close - bb_lower) / bb_range   # 0=lower band, 1=upper band
    bb_width = (bb_upper - bb_lower) / bb_mid  # band width %

    # ── ATR(14) ───────────────────────────────────────────────────────────────
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()

    # ── ADX(14) ───────────────────────────────────────────────────────────────
    up_move   = high.diff()
    down_move = -low.diff()
    plus_dm   = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm  = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr_s      = pd.Series(tr).rolling(14).sum()
    plus_di   = 100 * pd.Series(plus_dm).rolling(14).sum()  / tr_s.replace(0, np.nan)
    minus_di  = 100 * pd.Series(minus_dm).rolling(14).sum() / tr_s.replace(0, np.nan)
    dx        = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx       = dx.rolling(14).mean()

    # ── OBV ───────────────────────────────────────────────────────────────────
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()

    # ── Stochastic RSI ────────────────────────────────────────────────────────
    rsi_min  = rsi.rolling(14).min()
    rsi_max  = rsi.rolling(14).max()
    stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan)
    stoch_k  = stoch_rsi.rolling(3).mean() * 100
    stoch_d  = stoch_k.rolling(3).mean()

    # ── VWAP (rolling 20-bar approximation) ───────────────────────────────────
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).rolling(20).sum() / volume.rolling(20).sum().replace(0, np.nan)

    # ── Momentum & ROC ────────────────────────────────────────────────────────
    momentum10 = close - close.shift(10)
    roc10      = close.pct_change(10) * 100
    roc20      = close.pct_change(20) * 100

    # ── Volume Ratio ──────────────────────────────────────────────────────────
    vol_ma20  = volume.rolling(20).mean()
    vol_ratio = volume / vol_ma20.replace(0, np.nan)

    # ── Extract last row ──────────────────────────────────────────────────────
    i = -1
    p = -2 if len(df) > 1 else -1   # previous bar index

    cur_price  = _safe(close.iloc[i])
    prev_price = _safe(close.iloc[p])

    return {
        # Price
        "price":       cur_price,
        "prev_close":  prev_price,
        "price_change": _safe(close.iloc[i] - close.iloc[p]) if cur_price and prev_price else None,
        "price_change_pct": _safe((close.iloc[i] - close.iloc[p]) / close.iloc[p] * 100) if prev_price else None,

        # Moving Averages
        "sma20":  _safe(sma20.iloc[i]),
        "ema9":   _safe(ema9.iloc[i]),
        "ema20":  _safe(ema20.iloc[i]),
        "ema50":  _safe(ema50.iloc[i]),
        "ema200": _safe(ema200.iloc[i]),

        # MACD
        "macd":        _safe(macd_line.iloc[i]),
        "macd_signal": _safe(macd_signal.iloc[i]),
        "macd_hist":   _safe(macd_hist.iloc[i]),
        "macd_prev_hist": _safe(macd_hist.iloc[p]),

        # RSI
        "rsi": _safe(rsi.iloc[i]),

        # Bollinger
        "bb_upper": _safe(bb_upper.iloc[i]),
        "bb_lower": _safe(bb_lower.iloc[i]),
        "bb_mid":   _safe(bb_mid.iloc[i]),
        "bb_pct":   _safe(bb_pct.iloc[i]),
        "bb_width": _safe(bb_width.iloc[i]),

        # ATR / ADX
        "atr": _safe(atr.iloc[i]),
        "adx": _safe(adx.iloc[i]),
        "plus_di":  _safe(plus_di.iloc[i]),
        "minus_di": _safe(minus_di.iloc[i]),

        # OBV
        "obv":      _safe(obv.iloc[i]),
        "obv_prev": _safe(obv.iloc[p]),

        # Stochastic RSI
        "stoch_k": _safe(stoch_k.iloc[i]),
        "stoch_d": _safe(stoch_d.iloc[i]),

        # VWAP
        "vwap": _safe(vwap.iloc[i]),

        # Momentum
        "momentum10": _safe(momentum10.iloc[i]),
        "roc10":      _safe(roc10.iloc[i]),
        "roc20":      _safe(roc20.iloc[i]),

        # Volume
        "volume":    _safe(volume.iloc[i]),
        "vol_ma20":  _safe(vol_ma20.iloc[i]),
        "vol_ratio": _safe(vol_ratio.iloc[i]),

        # OHLC
        "open":  _safe(df["open"].iloc[i]),
        "high":  _safe(df["high"].iloc[i]),
        "low":   _safe(df["low"].iloc[i]),
        "close": cur_price,
    }
