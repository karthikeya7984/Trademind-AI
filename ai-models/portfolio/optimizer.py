"""
Portfolio Optimization Engine
Mean-Variance Optimization with Monte Carlo simulation.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import List, Dict, Optional


class PortfolioOptimizer:
    """Markowitz Mean-Variance Portfolio Optimizer."""

    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate

    def compute_stats(self, weights: np.ndarray, mean_returns: np.ndarray, cov_matrix: np.ndarray) -> tuple:
        ret = np.dot(weights, mean_returns)
        vol = np.sqrt(weights @ cov_matrix @ weights)
        sharpe = (ret - self.risk_free_rate) / vol if vol > 0 else 0
        return ret, vol, sharpe

    def optimize(self, returns_df: pd.DataFrame, objective: str = "sharpe") -> Dict:
        """
        Optimize portfolio weights.
        objective: 'sharpe' | 'min_vol' | 'max_return'
        """
        mean_returns = returns_df.mean() * 252
        cov_matrix = returns_df.cov() * 252
        n = len(returns_df.columns)

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        bounds = [(0.02, 0.6)] * n
        x0 = np.ones(n) / n

        if objective == "sharpe":
            def neg_sharpe(w): return -self.compute_stats(w, mean_returns.values, cov_matrix.values)[2]
            result = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints)
        elif objective == "min_vol":
            def portfolio_vol(w): return self.compute_stats(w, mean_returns.values, cov_matrix.values)[1]
            result = minimize(portfolio_vol, x0, method="SLSQP", bounds=bounds, constraints=constraints)
        else:
            def neg_return(w): return -self.compute_stats(w, mean_returns.values, cov_matrix.values)[0]
            result = minimize(neg_return, x0, method="SLSQP", bounds=bounds, constraints=constraints)

        weights = result.x if result.success else x0
        ret, vol, sharpe = self.compute_stats(weights, mean_returns.values, cov_matrix.values)

        return {
            "weights": {sym: round(float(w), 4) for sym, w in zip(returns_df.columns, weights)},
            "expected_return": round(float(ret) * 100, 2),
            "volatility": round(float(vol) * 100, 2),
            "sharpe_ratio": round(float(sharpe), 3),
            "success": result.success,
        }

    def efficient_frontier(self, returns_df: pd.DataFrame, n_portfolios: int = 500) -> List[Dict]:
        """Generate efficient frontier via Monte Carlo simulation."""
        mean_returns = returns_df.mean() * 252
        cov_matrix = returns_df.cov() * 252
        n = len(returns_df.columns)

        portfolios = []
        for _ in range(n_portfolios):
            w = np.random.dirichlet(np.ones(n))
            ret, vol, sharpe = self.compute_stats(w, mean_returns.values, cov_matrix.values)
            portfolios.append({
                "return": round(float(ret) * 100, 2),
                "volatility": round(float(vol) * 100, 2),
                "sharpe": round(float(sharpe), 3),
            })

        return portfolios

    def var_analysis(self, returns: pd.Series, confidence: float = 0.95) -> Dict:
        """Value at Risk analysis."""
        var = float(np.percentile(returns, (1 - confidence) * 100))
        cvar = float(returns[returns <= var].mean())
        return {
            "var": round(var * 100, 3),
            "cvar": round(cvar * 100, 3),
            "confidence": confidence,
        }
