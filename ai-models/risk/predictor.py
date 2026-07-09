"""Risk prediction model using statistical methods and ML."""
import numpy as np
import pandas as pd
from typing import Dict, List


class RiskPredictor:
    """Multi-factor risk scoring model."""

    def __init__(self):
        self.market_volatility = 0.18  # S&P 500 annualized vol baseline

    def compute_var(self, returns: pd.Series, confidence: float = 0.95) -> float:
        return float(np.percentile(returns, (1 - confidence) * 100))

    def compute_cvar(self, returns: pd.Series, confidence: float = 0.95) -> float:
        var = self.compute_var(returns, confidence)
        return float(returns[returns <= var].mean())

    def compute_max_drawdown(self, prices: pd.Series) -> float:
        cumulative = (1 + prices.pct_change()).cumprod()
        rolling_max = cumulative.cummax()
        drawdown = (cumulative - rolling_max) / rolling_max
        return float(drawdown.min())

    def compute_beta(self, stock_returns: pd.Series, market_returns: pd.Series) -> float:
        if len(stock_returns) != len(market_returns):
            min_len = min(len(stock_returns), len(market_returns))
            stock_returns = stock_returns.iloc[-min_len:]
            market_returns = market_returns.iloc[-min_len:]
        cov = np.cov(stock_returns, market_returns)[0][1]
        market_var = np.var(market_returns)
        return float(cov / market_var) if market_var > 0 else 1.0

    def compute_sharpe(self, returns: pd.Series, risk_free: float = 0.02) -> float:
        ann_return = returns.mean() * 252
        ann_vol = returns.std() * np.sqrt(252)
        return float((ann_return - risk_free) / ann_vol) if ann_vol > 0 else 0.0

    def compute_sortino(self, returns: pd.Series, risk_free: float = 0.02) -> float:
        ann_return = returns.mean() * 252
        downside = returns[returns < 0].std() * np.sqrt(252)
        return float((ann_return - risk_free) / downside) if downside > 0 else 0.0

    def score(self, prices: pd.Series) -> Dict:
        """Compute comprehensive risk score 0-100."""
        returns = prices.pct_change().dropna()
        ann_vol = float(returns.std() * np.sqrt(252))
        max_dd = self.compute_max_drawdown(prices)
        var_95 = self.compute_var(returns)
        sharpe = self.compute_sharpe(returns)

        # Weighted risk score
        vol_score = min(ann_vol / 0.5 * 40, 40)
        dd_score = min(abs(max_dd) / 0.5 * 30, 30)
        var_score = min(abs(var_95) / 0.05 * 30, 30)
        total_score = int(vol_score + dd_score + var_score)

        return {
            "risk_score": total_score,
            "risk_level": "HIGH" if total_score > 70 else "MEDIUM" if total_score > 40 else "LOW",
            "volatility": round(ann_vol * 100, 2),
            "var_95": round(var_95 * 100, 2),
            "var_99": round(self.compute_var(returns, 0.99) * 100, 2),
            "cvar_95": round(self.compute_cvar(returns) * 100, 2),
            "max_drawdown": round(max_dd * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "sortino_ratio": round(self.compute_sortino(returns), 3),
            "beta": round(ann_vol / self.market_volatility, 2),
        }

    def portfolio_risk(self, weights: np.ndarray, cov_matrix: np.ndarray) -> Dict:
        """Portfolio-level risk metrics."""
        port_vol = float(np.sqrt(weights @ cov_matrix @ weights))
        return {
            "portfolio_volatility": round(port_vol * 100, 2),
            "portfolio_var_95": round(port_vol * 1.645 * 100, 2),
            "diversification_ratio": round(1 / np.sum(weights ** 2), 2),
        }
