from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User, Watchlist
from app.schemas.schemas import WatchlistAdd, WatchlistOut

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


@router.get("/", response_model=List[WatchlistOut])
async def get_watchlist(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Watchlist).where(Watchlist.user_id == user.id).order_by(Watchlist.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=WatchlistOut, status_code=201)
async def add_to_watchlist(body: WatchlistAdd, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Watchlist).where(Watchlist.user_id == user.id, Watchlist.stock_symbol == body.stock_symbol.upper()))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Already in watchlist")
    item = Watchlist(user_id=user.id, stock_symbol=body.stock_symbol.upper())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{symbol}", status_code=204)
async def remove_from_watchlist(symbol: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Watchlist).where(Watchlist.user_id == user.id, Watchlist.stock_symbol == symbol.upper()))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Not in watchlist")
    await db.delete(item)
    await db.commit()
