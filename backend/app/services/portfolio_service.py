import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import List
import json
from app.services.market_service import get_historical_data
from app.core.redis import cache_get, cache_set


async def optimize_portfolio(symbols: List[str], risk_tolerance: float = 0.5) -> dict:
    cache_key = f"portfolio:opt:{'-'.join(sorted(symbols))}:{risk_tolerance}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    returns_data = {}
    for symbol in symbols:
        history = await get_historical_data(symbol, period="1y", interval="1d")
        if history:
            df = pd.DataFrame(history)
            returns_data[symbol] = df["close"].pct_change().dropna().values

    if len(returns_data) < 2:
        return {"error": "Need at least 2 symbols with data"}

    min_len = min(len(v) for v in returns_data.values())
    returns_matrix = np.array([v[:min_len] for v in returns_data.values()]).T
    mean_returns = returns_matrix.mean(axis=0) * 252
    cov_matrix = np.cov(returns_matrix.T) * 252
    n = len(symbols)

    def portfolio_stats(weights):
        ret = np.dot(weights, mean_returns)
        vol = np.sqrt(weights @ cov_matrix @ weights)
        sharpe = (ret - 0.02) / vol if vol > 0 else 0
        return ret, vol, sharpe

    def neg_sharpe(weights):
        _, _, sharpe = portfolio_stats(weights)
        return -sharpe

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = [(0.05, 0.6)] * n
    x0 = np.ones(n) / n

    result = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints)
    weights = result.x if result.success else x0

    ret, vol, sharpe = portfolio_stats(weights)

    # Monte Carlo simulation
    mc_returns = []
    for _ in range(500):
        w = np.random.dirichlet(np.ones(n))
        r, v, _ = portfolio_stats(w)
        mc_returns.append({"return": round(r, 4), "volatility": round(v, 4)})

    allocation = {sym: round(float(w) * 100, 2) for sym, w in zip(symbols, weights)}

    output = {
        "allocation": allocation,
        "expected_return": round(float(ret) * 100, 2),
        "volatility": round(float(vol) * 100, 2),
        "sharpe_ratio": round(float(sharpe), 3),
        "efficient_frontier": mc_returns[:100],
        "risk_scores": {sym: round(float(np.std(returns_data[sym]) * np.sqrt(252) * 100), 2) for sym in symbols},
    }

    await cache_set(cache_key, json.dumps(output), ttl=1800)
    return output
