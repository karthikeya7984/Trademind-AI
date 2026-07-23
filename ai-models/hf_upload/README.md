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
