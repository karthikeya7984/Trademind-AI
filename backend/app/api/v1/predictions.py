from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User, PredictionHistory
from app.schemas.schemas import PredictionOut
from app.services.prediction_service import run_prediction, run_signals_batch
from sqlalchemy import select
from typing import List, Optional
import asyncio

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get("/history/me", response_model=List[PredictionOut])
async def prediction_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PredictionHistory).where(PredictionHistory.user_id == user.id).order_by(PredictionHistory.created_at.desc()).limit(50)
    )
    return result.scalars().all()


@router.get("/signals")
async def signals_batch(
    symbols: str = Query(..., description="Comma-separated symbols, max 50"),
):
    """Fast BUY/HOLD/SELL signals for all symbols — public, used by dashboard table."""
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()][:100]
    return await run_signals_batch(symbol_list)


@router.get("/batch")
async def predict_batch(
    symbols: str = Query(..., description="Comma-separated symbols, max 20"),
):
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()][:20]

    async def _one(sym: str):
        try:
            return sym, await run_prediction(sym)
        except Exception:
            return sym, {"symbol": sym, "error": "Failed"}

    pairs = await asyncio.gather(*[_one(s) for s in symbol_list])
    return {sym: result for sym, result in pairs}


@router.get("/{symbol}")
async def predict(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(lambda: None),  # optional auth
):
    result = await run_prediction(symbol.upper())
    return result
