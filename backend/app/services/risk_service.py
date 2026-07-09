import numpy as np
import pandas as pd
import json
import math
from app.services.market_service import get_historical_data
from app.core.redis import cache_get, cache_set


def _safe(val):
    """Convert numpy scalars / NaN / inf to plain Python floats safe for JSON."""
    try:
        f = float(val)
        return 0.0 if (math.isnan(f) or math.isinf(f)) else f
    except Exception:
        return 0.0


async def analyze_risk(symbol: str) -> dict:
    cache_key = f"risk:{symbol}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    history = await get_historical_data(symbol, period="1y", interval="1d")
    if not history:
        return {"error": f"No historical data available for {symbol}"}

    df = pd.DataFrame(history)

    # Drop any NaN closes (e.g. today's incomplete bar)
    df = df.dropna(subset=["close"])
    if len(df) < 30:
        return {"error": f"Not enough data to analyze {symbol}"}

    close = df["close"].astype(float)
    returns = close.pct_change().dropna()

    # VaR (historical simulation)
    var_95 = _safe(np.percentile(returns, 5))
    var_99 = _safe(np.percentile(returns, 1))

    # Annualised volatility
    volatility = _safe(returns.std() * np.sqrt(252))

    # Max Drawdown
    cumulative = (1 + returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_drawdown = _safe(drawdown.min())

    # Sharpe ratio (assume 0% risk-free rate for simplicity)
    sharpe = _safe(returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0.0

    # Beta (simplified: stock vol / market vol proxy 18%)
    beta = round(_safe(volatility / 0.18), 2)

    # Risk score 0-100
    vol_component = min(volatility * 100, 60)          # max 60 pts from vol
    dd_component = min(abs(max_drawdown) * 50, 40)     # max 40 pts from drawdown
    risk_score = int(vol_component + dd_component)

    # Stop loss: current price minus 2× daily VaR (as negative number, so add)
    last_price = _safe(close.iloc[-1])
    stop_loss = round(last_price * (1 + var_95 * 2), 2)

    result = {
        "symbol": symbol,
        "current_price": round(last_price, 2),
        "volatility": round(volatility * 100, 2),
        "var_95": round(var_95 * 100, 2),
        "var_99": round(var_99 * 100, 2),
        "max_drawdown": round(max_drawdown * 100, 2),
        "beta": beta,
        "sharpe_ratio": round(sharpe, 2),
        "risk_score": risk_score,
        "stop_loss_recommendation": stop_loss,
        "risk_level": "HIGH" if risk_score > 70 else "MEDIUM" if risk_score > 40 else "LOW",
    }

    await cache_set(cache_key, json.dumps(result), ttl=900)
    return result
