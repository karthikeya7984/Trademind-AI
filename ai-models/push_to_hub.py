"""
push_to_hub.py
──────────────────────────────────────────────────────────────────────────────
Trains the TradeMind LSTM stock prediction model and pushes it to HF Hub.

Usage:
    cd ai-models
    pip install huggingface_hub tensorflow yfinance scikit-learn pandas numpy
    python push_to_hub.py --token hf_your_token_here --repo your-username/trademind-lstm

Steps this script performs:
    1. Fetch 2yr daily OHLCV data for top stocks via yfinance
    2. Train LSTMStockPredictor on each symbol
    3. Save model weights + scaler + config as a single bundle
    4. Push to Hugging Face Hub with a model card
"""

import os
import sys
import json
import pickle
import argparse
import asyncio
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lstm.model import LSTMStockPredictor


TRAIN_SYMBOLS = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "AMD", "JPM", "NFLX"]


# ── Fetch data ─────────────────────────────────────────────────────────────────

def fetch_data(symbol: str) -> pd.DataFrame:
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="2y", interval="1d")
    df.reset_index(inplace=True)
    df.columns = [c.lower() for c in df.columns]
    return df


# ── Train all symbols ──────────────────────────────────────────────────────────

def train_all(save_dir: str) -> dict:
    os.makedirs(save_dir, exist_ok=True)
    results = {}

    for symbol in TRAIN_SYMBOLS:
        print(f"\n📈 Training {symbol}...")
        try:
            df = fetch_data(symbol)
            if len(df) < 120:
                print(f"  ⚠️  Skipping {symbol}: only {len(df)} rows")
                continue

            predictor = LSTMStockPredictor(sequence_length=60, forecast_days=5)
            result = predictor.train(df, epochs=30, batch_size=32)

            if "error" in result:
                print(f"  ❌ {symbol}: {result['error']}")
                continue

            # Save Keras model
            model_path = os.path.join(save_dir, f"{symbol}_lstm.keras")
            predictor.save(model_path)

            # Save scaler separately
            scaler_path = os.path.join(save_dir, f"{symbol}_scaler.pkl")
            with open(scaler_path, "wb") as f:
                pickle.dump(predictor.scaler, f)

            results[symbol] = {
                "status": "trained",
                "samples": result.get("samples", 0),
                "model_file": f"{symbol}_lstm.keras",
                "scaler_file": f"{symbol}_scaler.pkl",
            }
            print(f"  ✅ {symbol}: trained on {result.get('samples', 0)} samples")

        except Exception as e:
            print(f"  ❌ {symbol}: {e}")

    # Save metadata
    meta = {
        "model_type": "LSTM",
        "framework": "TensorFlow/Keras",
        "sequence_length": 60,
        "forecast_days": 5,
        "features": ["close", "returns", "ma5", "ma20", "volatility", "rsi", "macd"],
        "trained_symbols": list(results.keys()),
        "task": "stock-price-forecasting",
    }
    with open(os.path.join(save_dir, "config.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n✅ Trained {len(results)}/{len(TRAIN_SYMBOLS)} symbols → saved to {save_dir}/")
    return results


# ── Model Card ─────────────────────────────────────────────────────────────────

MODEL_CARD = """\
---
language: en
tags:
  - stock-prediction
  - lstm
  - time-series
  - finance
  - tensorflow
license: mit
---

# TradeMind LSTM Stock Predictor

LSTM-based stock price forecasting model trained on 2 years of daily OHLCV data.

## Model Details

- **Architecture**: Stacked LSTM (128 → 64 → 32 units) with BatchNorm + Dropout
- **Framework**: TensorFlow / Keras
- **Input**: 60-day sliding window of 7 features
- **Output**: 5-day price forecast
- **Features**: Close price, Returns, MA5, MA20, Volatility, RSI(14), MACD

## Trained Symbols

AAPL, TSLA, NVDA, MSFT, AMZN, GOOGL, META, AMD, JPM, NFLX

## Usage

```python
import pickle
import pandas as pd
from tensorflow.keras.models import load_model
import numpy as np

# Load model and scaler
model = load_model("AAPL_lstm.keras")
with open("AAPL_scaler.pkl", "rb") as f:
    scaler = pickle.load(f)

# Prepare your DataFrame with columns: close, returns, ma5, ma20, volatility, rsi, macd
# df = your_dataframe  (at least 60 rows)

features = ["close", "returns", "ma5", "ma20", "volatility", "rsi", "macd"]
data = df[features].values
scaled = scaler.transform(data)
seq = scaled[-60:].reshape(1, 60, len(features))

pred_scaled = model.predict(seq)[0]
dummy = np.zeros((5, len(features)))
dummy[:, 0] = pred_scaled
predicted_prices = scaler.inverse_transform(dummy)[:, 0]
print("5-day forecast:", predicted_prices)
```

## Disclaimer

This model is for educational and research purposes only.
Not financial advice. Past performance does not guarantee future results.
"""


# ── Push to Hub ────────────────────────────────────────────────────────────────

def push_to_hub(save_dir: str, repo_id: str, token: str):
    from huggingface_hub import HfApi, create_repo

    os.environ["HF_HUB_DISABLE_XET"] = "1"
    api = HfApi(token=token)

    # Create repo if it doesn't exist
    print(f"\n🚀 Creating/verifying repo: {repo_id}")
    create_repo(repo_id=repo_id, token=token, exist_ok=True, repo_type="model")

    # Write model card
    card_path = os.path.join(save_dir, "README.md")
    with open(card_path, "w", encoding="utf-8") as f:
        f.write(MODEL_CARD)

    # Upload entire folder
    print(f"📤 Uploading files to https://huggingface.co/{repo_id} ...")
    api.upload_folder(
        folder_path=save_dir,
        repo_id=repo_id,
        repo_type="model",
        commit_message="Add TradeMind LSTM stock prediction models",
    )

    print(f"\n✅ Model pushed successfully!")
    print(f"🔗 View at: https://huggingface.co/{repo_id}")
    print(f"\n📋 Add this to your backend/.env:")
    print(f"   HF_MODEL_REPO={repo_id}")
    print(f"   HF_API_KEY=your_hf_token")


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train & push TradeMind LSTM to HF Hub")
    parser.add_argument("--token",   required=True, help="HuggingFace API token (hf_...)")
    parser.add_argument("--repo",    required=True, help="HF repo id, e.g. your-username/trademind-lstm")
    parser.add_argument("--save-dir", default="hf_upload", help="Local dir to save models before upload")
    parser.add_argument("--skip-train", action="store_true", help="Skip training, just push existing files")
    args = parser.parse_args()

    if not args.skip_train:
        results = train_all(args.save_dir)
        if not results:
            print("❌ No models trained. Exiting.")
            sys.exit(1)
    else:
        print(f"⏭️  Skipping training, pushing existing files from {args.save_dir}/")

    push_to_hub(args.save_dir, args.repo, args.token)
