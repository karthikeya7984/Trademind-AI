"""
Backtesting engine for trading strategy evaluation.
"""
import pandas as pd
import numpy as np
from typing import Callable, Dict, List
from dataclasses import dataclass, field


@dataclass
class Trade:
    symbol: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    quantity: float
    trade_type: str  # long / short
    pnl: float
    pnl_pct: float


@dataclass
class BacktestResult:
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    trades: List[Trade] = field(default_factory=list)


class Backtester:
    """Simple event-driven backtesting engine."""

    def __init__(self, initial_capital: float = 100_000):
        self.initial_capital = initial_capital

    def run(self, df: pd.DataFrame, strategy_fn: Callable[[pd.DataFrame, int], str]) -> BacktestResult:
        """
        Run backtest.
        strategy_fn(df, i) -> "BUY" | "SELL" | "HOLD"
        """
        capital = self.initial_capital
        position = 0.0
        entry_price = 0.0
        trades: List[Trade] = []
        equity_curve = [capital]

        for i in range(20, len(df)):
            signal = strategy_fn(df, i)
            price = df["close"].iloc[i]
            date = str(df["date"].iloc[i]) if "date" in df.columns else str(i)

            if signal == "BUY" and position == 0:
                quantity = capital * 0.95 / price
                position = quantity
                entry_price = price
                capital -= quantity * price

            elif signal == "SELL" and position > 0:
                proceeds = position * price
                pnl = proceeds - position * entry_price
                pnl_pct = (price - entry_price) / entry_price * 100
                trades.append(Trade(
                    symbol="", entry_date="", exit_date=date,
                    entry_price=entry_price, exit_price=price,
                    quantity=position, trade_type="long",
                    pnl=round(pnl, 2), pnl_pct=round(pnl_pct, 2),
                ))
                capital += proceeds
                position = 0

            equity_curve.append(capital + position * price)

        # Metrics
        equity = np.array(equity_curve)
        total_return = (equity[-1] - self.initial_capital) / self.initial_capital * 100
        returns = np.diff(equity) / equity[:-1]
        ann_return = (1 + total_return / 100) ** (252 / len(equity)) - 1
        sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0

        rolling_max = np.maximum.accumulate(equity)
        drawdowns = (equity - rolling_max) / rolling_max
        max_dd = float(drawdowns.min() * 100)

        wins = [t for t in trades if t.pnl > 0]
        win_rate = len(wins) / len(trades) * 100 if trades else 0

        return BacktestResult(
            total_return=round(total_return, 2),
            annualized_return=round(ann_return * 100, 2),
            sharpe_ratio=round(float(sharpe), 3),
            max_drawdown=round(max_dd, 2),
            win_rate=round(win_rate, 2),
            total_trades=len(trades),
            trades=trades,
        )


def sma_crossover_strategy(df: pd.DataFrame, i: int) -> str:
    """Simple SMA 20/50 crossover strategy."""
    if i < 50:
        return "HOLD"
    ma20 = df["close"].iloc[i - 20:i].mean()
    ma50 = df["close"].iloc[i - 50:i].mean()
    prev_ma20 = df["close"].iloc[i - 21:i - 1].mean()
    prev_ma50 = df["close"].iloc[i - 51:i - 1].mean()

    if prev_ma20 <= prev_ma50 and ma20 > ma50:
        return "BUY"
    if prev_ma20 >= prev_ma50 and ma20 < ma50:
        return "SELL"
    return "HOLD"
