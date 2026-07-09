from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User, TradeHistory, PaperTrading, Portfolio
from app.schemas.schemas import TradeCreate, TradeOut, PaperTradingOut
from app.services.market_service import get_stock_quote

router = APIRouter(prefix="/trading", tags=["Trading"])


@router.get("/account", response_model=PaperTradingOut)
async def get_account(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PaperTrading).where(PaperTrading.user_id == user.id))
    account = result.scalar_one_or_none()
    if not account:
        account = PaperTrading(user_id=user.id)
        db.add(account)
        await db.commit()
        await db.refresh(account)
    return account


async def _sync_portfolio(db: AsyncSession, user_id: str, symbol: str, trade_type: str, quantity: float, price: float):
    """Auto-update portfolio when a trade is executed."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id, Portfolio.stock_symbol == symbol)
    )
    position = result.scalar_one_or_none()

    if trade_type == "buy":
        if position:
            # Recalculate weighted average buy price
            total_qty = position.quantity + quantity
            position.average_buy_price = round(
                (position.average_buy_price * position.quantity + price * quantity) / total_qty, 4
            )
            position.quantity = round(total_qty, 4)
        else:
            position = Portfolio(
                user_id=user_id,
                stock_symbol=symbol,
                quantity=round(quantity, 4),
                average_buy_price=round(price, 4),
                allocation_percentage=0.0,
                expected_return=0.0,
                risk_score=0.0,
            )
            db.add(position)
    elif trade_type == "sell" and position:
        new_qty = round(position.quantity - quantity, 4)
        if new_qty <= 0:
            await db.delete(position)
        else:
            position.quantity = new_qty


@router.post("/trade", response_model=TradeOut, status_code=201)
async def execute_trade(body: TradeCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account_result = await db.execute(select(PaperTrading).where(PaperTrading.user_id == user.id))
    account = account_result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "Trading account not found")

    quote = await get_stock_quote(body.stock_symbol.upper())
    price = quote.get("price", body.amount / body.quantity)
    total = price * body.quantity

    if body.trade_type == "buy":
        if account.balance < total:
            raise HTTPException(400, "Insufficient balance")
        account.balance -= total
    else:
        account.balance += total
        account.profit_loss += total - body.amount

    trade = TradeHistory(
        user_id=user.id,
        stock_symbol=body.stock_symbol.upper(),
        trade_type=body.trade_type,
        quantity=body.quantity,
        amount=total,
    )
    db.add(trade)

    # Auto-sync portfolio
    await _sync_portfolio(db, user.id, body.stock_symbol.upper(), body.trade_type, body.quantity, price)

    await db.commit()
    await db.refresh(trade)
    return trade


@router.get("/history", response_model=List[TradeOut])
async def trade_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TradeHistory).where(TradeHistory.user_id == user.id).order_by(TradeHistory.timestamp.desc()).limit(100)
    )
    return result.scalars().all()
