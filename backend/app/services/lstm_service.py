"""
lstm_service.py
Downloads trained LSTM models from HuggingFace Hub and runs predictions.
Falls back gracefully if model not available for a symbol.
"""
import os
import pickle
import numpy as np
import pandas as pd
from typing import Optional
from app.core.config import settings

# Local cache dir for downloaded models
_MODEL_CACHE = os.path.join(os.path.dirname(__file__), ".lstm_cache")

# Symbols that have trained models on HF Hub
HF_TRAINED_SYMBOLS = {"AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "JPM", "NFLX"}

_loaded_models: dict = {}   # symbol -> {"model": ..., "scaler": ...}


def _cache_path(symbol: str, ext: str) -> str:
    os.makedirs(_MODEL_CACHE, exist_ok=True)
    return os.path.join(_MODEL_CACHE, f"{symbol}_lstm{ext}")


def _download_from_hf(symbol: str) -> bool:
    """Download model + scaler from HuggingFace Hub into local cache."""
    if not settings.HF_MODEL_REPO or not settings.HF_API_KEY:
        return False
    try:
        from huggingface_hub import hf_hub_download
        hf_hub_download(
            repo_id=settings.HF_MODEL_REPO,
            filename=f"{symbol}_lstm.keras",
            local_dir=_MODEL_CACHE,
            token=settings.HF_API_KEY,
        )
        hf_hub_download(
            repo_id=settings.HF_MODEL_REPO,
            filename=f"{symbol}_scaler.pkl",
            local_dir=_MODEL_CACHE,
            token=settings.HF_API_KEY,
        )
        return True
    except Exception:
        return False


def _load_model(symbol: str) -> Optional[dict]:
    """Load model + scaler for symbol, downloading from HF if needed."""
    if symbol in _loaded_models:
        return _loaded_models[symbol]

    keras_path  = _cache_path(symbol, ".keras")
    scaler_path = _cache_path(symbol, ".pkl")

    # Download if not cached locally
    if not os.path.exists(keras_path) or not os.path.exists(scaler_path):
        if not _download_from_hf(symbol):
            return None

    try:
        from tensorflow.keras.models import load_model
        model  = load_model(keras_path)
        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)
        _loaded_models[symbol] = {"model": model, "scaler": scaler}
        return _loaded_models[symbol]
    except Exception:
        return None


def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close = df["close"]
    df["returns"]    = close.pct_change()
    df["ma5"]        = close.rolling(5).mean()
    df["ma20"]       = close.rolling(20).mean()
    df["volatility"] = close.rolling(20).std()
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    df["rsi"]  = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))
    ema12      = close.ewm(span=12).mean()
    ema26      = close.ewm(span=26).mean()
    df["macd"] = ema12 - ema26
    return df.dropna()


def lstm_predict(symbol: str, df: pd.DataFrame) -> Optional[dict]:
    """
    Run LSTM prediction for symbol using historical price DataFrame.
    Returns dict with predicted_prices, predicted_price, signal, confidence
    or None if model unavailable.
    """
    if symbol not in HF_TRAINED_SYMBOLS:
        return None

    bundle = _load_model(symbol)
    if bundle is None:
        return None

    try:
        model  = bundle["model"]
        scaler = bundle["scaler"]

        features_df = _prepare_features(df)
        if len(features_df) < 60:
            return None

        FEATURE_COLS = ["close", "returns", "ma5", "ma20", "volatility", "rsi", "macd"]
        available    = [c for c in FEATURE_COLS if c in features_df.columns]
        data         = features_df[available].values
        scaled       = scaler.transform(data)

        seq          = scaled[-60:].reshape(1, 60, len(available))
        pred_scaled  = model.predict(seq, verbose=0)[0]

        dummy        = np.zeros((len(pred_scaled), len(available)))
        dummy[:, 0]  = pred_scaled
        pred_prices  = scaler.inverse_transform(dummy)[:, 0]

        current = float(df["close"].iloc[-1])
        final   = float(pred_prices[-1])

        if   final > current * 1.02:  signal = "BUY"
        elif final < current * 0.98:  signal = "SELL"
        else:                          signal = "HOLD"

        # Confidence based on predicted move magnitude
        move       = abs(final - current) / current
        confidence = round(min(0.60 + move * 5, 0.95), 3)

        return {
            "predicted_prices": [round(float(p), 2) for p in pred_prices],
            "predicted_price":  round(final, 2),
            "signal":           signal,
            "confidence_score": confidence,
            "source":           "lstm_hf",
        }
    except Exception:
        return None
