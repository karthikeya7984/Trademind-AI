from fastapi import APIRouter, Depends, Query
from app.core.deps import get_current_user
from app.models.models import User
from app.services.backtest_service import Backtester, sma_crossover_strategy
from app.services.market_service import get_historical_data
import pandas as pd

router = APIRouter(prefix="/backtest", tags=["Backtesting"])


@router.get("/{symbol}")
async def run_backtest(
    symbol: str,
    period: str = Query("1y"),
    initial_capital: float = Query(100_000, ge=1000),
    user: User = Depends(get_current_user),
):
    history = await get_historical_data(symbol.upper(), period=period, interval="1d")
    if not history:
        return {"error": "No data available"}

    df = pd.DataFrame(history)
    backtester = Backtester(initial_capital=initial_capital)
    result = backtester.run(df, sma_crossover_strategy)

    return {
        "symbol": symbol.upper(),
        "strategy": "SMA 20/50 Crossover",
        "period": period,
        "initial_capital": initial_capital,
        "total_return": result.total_return,
        "annualized_return": result.annualized_return,
        "sharpe_ratio": result.sharpe_ratio,
        "max_drawdown": result.max_drawdown,
        "win_rate": result.win_rate,
        "total_trades": result.total_trades,
        "trades": [
            {"exit_date": t.exit_date, "entry_price": t.entry_price, "exit_price": t.exit_price, "pnl": t.pnl, "pnl_pct": t.pnl_pct}
            for t in result.trades[-20:]
        ],
    }
