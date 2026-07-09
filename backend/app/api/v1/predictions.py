from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User, PredictionHistory
from app.schemas.schemas import PredictionOut
from app.services.prediction_service import run_prediction, run_signals_batch
from sqlalchemy import select
from typing import List
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
    user: User = Depends(get_current_user),
):
    """Fast BUY/HOLD/SELL signals for all symbols — used by the dashboard table."""
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()][:100]
    return await run_signals_batch(symbol_list)


@router.get("/batch")
async def predict_batch(
    symbols: str = Query(..., description="Comma-separated symbols, max 20"),
    user: User = Depends(get_current_user),
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
async def predict(symbol: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await run_prediction(symbol.upper())
    if "error" not in result:
        record = PredictionHistory(
            user_id=user.id,
            stock_symbol=symbol.upper(),
            prediction=result["signal"],
            confidence_score=result["confidence_score"],
            predicted_price=result["predicted_price"],
            signal=result["signal"],
        )
        db.add(record)
        await db.commit()
    return result
