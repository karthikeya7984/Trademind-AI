from fastapi import APIRouter, Query
from app.services.news_service import get_news, get_symbol_sentiment

router = APIRouter(prefix="/news", tags=["News"])


@router.get("/")
async def news(q: str = Query("stock market"), page_size: int = Query(20, le=50)):
    return await get_news(q, page_size)


@router.get("/symbol/{symbol}")
async def symbol_news(symbol: str):
    return await get_news(symbol, 15)


@router.get("/sentiment/{symbol}")
async def symbol_sentiment(symbol: str):
    return await get_symbol_sentiment(symbol.upper())
