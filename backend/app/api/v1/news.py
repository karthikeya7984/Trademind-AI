from fastapi import APIRouter, Depends, Query
from app.core.deps import get_current_user
from app.models.models import User
from app.services.news_service import get_news, get_symbol_sentiment
from app.services.risk_service import analyze_risk

router = APIRouter(prefix="/news", tags=["News"])


@router.get("/")
async def news(q: str = Query("stock market"), page_size: int = Query(20, le=50), user: User = Depends(get_current_user)):
    return await get_news(q, page_size)


@router.get("/symbol/{symbol}")
async def symbol_news(symbol: str, user: User = Depends(get_current_user)):
    return await get_news(symbol, 15)


@router.get("/sentiment/{symbol}")
async def symbol_sentiment(symbol: str, user: User = Depends(get_current_user)):
    return await get_symbol_sentiment(symbol.upper())
