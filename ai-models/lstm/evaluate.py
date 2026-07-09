"""Evaluate trained LSTM models and generate performance report."""
import pandas as pd
import numpy as np
import os
import json
from sklearn.metrics import mean_absolute_error, mean_squared_error


def evaluate_model(symbol: str, model_path: str) -> dict:
    """Evaluate model on held-out test data."""
    import yfinance as yf
    from ai_models.lstm.model import LSTMStockPredictor

    ticker = yf.Ticker(symbol)
    df = ticker.history(period="2y", interval="1d")
    df.reset_index(inplace=True)
    df.columns = [c.lower() for c in df.columns]

    predictor = LSTMStockPredictor()
    predictor.load(model_path)

    # Use last 20% as test set
    split = int(len(df) * 0.8)
    test_df = df.iloc[split:]

    predictions = []
    actuals = []

    for i in range(60, len(test_df) - 5):
        window = df.iloc[split + i - 60: split + i]
        pred = predictor.predict(window)
        if "predicted_price" in pred:
            predictions.append(pred["predicted_price"])
            actuals.append(test_df.iloc[i]["close"])

    if not predictions:
        return {"symbol": symbol, "error": "No predictions generated"}

    mae = mean_absolute_error(actuals, predictions)
    rmse = np.sqrt(mean_squared_error(actuals, predictions))
    mape = np.mean(np.abs((np.array(actuals) - np.array(predictions)) / np.array(actuals))) * 100

    return {
        "symbol": symbol,
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "mape": round(mape, 2),
        "accuracy": round(100 - mape, 2),
        "test_samples": len(predictions),
    }


if __name__ == "__main__":
    models_dir = "models"
    results = []

    if os.path.exists(models_dir):
        for fname in os.listdir(models_dir):
            if fname.endswith("_lstm.h5"):
                symbol = fname.replace("_lstm.h5", "")
                result = evaluate_model(symbol, os.path.join(models_dir, fname))
                results.append(result)
                print(f"{symbol}: MAE={result.get('mae')}, MAPE={result.get('mape')}%")

    with open("model_evaluation_report.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nReport saved to model_evaluation_report.json")
