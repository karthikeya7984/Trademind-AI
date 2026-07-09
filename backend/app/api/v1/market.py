from fastapi import APIRouter, Depends, Query
from app.core.deps import get_current_user
from app.models.models import User
from app.services.market_service import (
    get_stock_quote, get_historical_data, search_stocks,
    get_market_movers, get_intraday_data, get_market_indices, get_bulk_quotes,
    get_stock_detail,
)
import asyncio

router = APIRouter(prefix="/market", tags=["Market"])


@router.get("/quote/{symbol}")
async def quote(symbol: str, user: User = Depends(get_current_user)):
    return await get_stock_quote(symbol.upper())


@router.get("/quotes/batch")
async def batch_quotes(symbols: str = Query(..., description="Comma-separated symbols"), user: User = Depends(get_current_user)):
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()][:50]
    return await get_bulk_quotes(symbol_list)


@router.get("/history/{symbol}")
async def history(
    symbol: str,
    period: str = Query("1y"),
    interval: str = Query("1d"),
    user: User = Depends(get_current_user),
):
    return await get_historical_data(symbol.upper(), period, interval)


@router.get("/intraday/{symbol}")
async def intraday(
    symbol: str,
    interval: str = Query("5min"),
    user: User = Depends(get_current_user),
):
    return await get_intraday_data(symbol.upper(), interval)


@router.get("/indices")
async def indices(user: User = Depends(get_current_user)):
    return await get_market_indices()


@router.get("/stock/{symbol}")
async def stock_detail(symbol: str, user: User = Depends(get_current_user)):
    """Quote + company overview in one fast cached call."""
    return await get_stock_detail(symbol.upper())


@router.get("/search")
async def search(q: str = Query(..., min_length=1), user: User = Depends(get_current_user)):
    return await search_stocks(q)


@router.get("/movers")
async def movers(user: User = Depends(get_current_user)):
    return await get_market_movers()
