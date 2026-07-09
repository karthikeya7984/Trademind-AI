"""Training pipeline for LSTM stock prediction model."""
import asyncio
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from ai_models.lstm.model import LSTMStockPredictor


SYMBOLS = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "AMD"]


async def fetch_data(symbol: str) -> pd.DataFrame:
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="2y", interval="1d")
    df.reset_index(inplace=True)
    df.columns = [c.lower() for c in df.columns]
    return df


async def train_symbol(symbol: str):
    print(f"Training {symbol}...")
    df = await fetch_data(symbol)
    if len(df) < 100:
        print(f"  Skipping {symbol}: insufficient data")
        return

    predictor = LSTMStockPredictor(sequence_length=60, forecast_days=5)
    result = predictor.train(df, epochs=30, batch_size=32)
    print(f"  {symbol}: {result}")

    os.makedirs("models", exist_ok=True)
    predictor.save(f"models/{symbol}_lstm.h5")
    print(f"  Saved models/{symbol}_lstm.h5")


async def main():
    for symbol in SYMBOLS:
        try:
            await train_symbol(symbol)
        except Exception as e:
            print(f"  Error training {symbol}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
