from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User, Portfolio
from app.schemas.schemas import PortfolioItem, PortfolioOut
from app.services.portfolio_service import optimize_portfolio

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.get("/", response_model=List[PortfolioOut])
async def get_portfolio(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user.id))
    return result.scalars().all()


@router.post("/", response_model=PortfolioOut, status_code=201)
async def add_position(body: PortfolioItem, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = Portfolio(user_id=user.id, **body.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def remove_position(item_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Portfolio).where(Portfolio.id == item_id, Portfolio.user_id == user.id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Position not found")
    await db.delete(item)
    await db.commit()


@router.post("/optimize")
async def optimize(symbols: List[str], risk_tolerance: float = 0.5, user: User = Depends(get_current_user)):
    if len(symbols) < 2:
        raise HTTPException(400, "Need at least 2 symbols")
    return await optimize_portfolio(symbols, risk_tolerance)
