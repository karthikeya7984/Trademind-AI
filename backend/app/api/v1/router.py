from fastapi import APIRouter
from app.api.v1 import auth, users, market, predictions, portfolio, watchlist, trading, assistant, news, risk, backtest

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(market.router)
router.include_router(predictions.router)
router.include_router(portfolio.router)
router.include_router(watchlist.router)
router.include_router(trading.router)
router.include_router(assistant.router)
router.include_router(news.router)
router.include_router(risk.router)
router.include_router(backtest.router)
