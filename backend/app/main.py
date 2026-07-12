import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.router import router
from app.api.websocket import stock_ws_handler
from app.middleware.logging import LoggingMiddleware
from fastapi import WebSocket
from prometheus_fastapi_instrumentator import Instrumentator
import structlog

structlog.configure(processors=[structlog.dev.ConsoleRenderer()])


_DASHBOARD_SYMBOLS = [
    "AAPL","MSFT","NVDA","GOOGL","META","AMD","INTC","ORCL","CRM","ADBE",
    "QCOM","TXN","PLTR","SNOW","NET","SHOP","AMZN","TSLA","NFLX","BABA",
    "UBER","ABNB","NKE","SBUX","MCD","WMT","JPM","BAC","GS","MS",
    "BRK-B","V","MA","PYPL","COIN","HOOD","JNJ","PFE","MRNA","UNH",
    "ABBV","LLY","XOM","CVX","COP","SLB","SPY","QQQ","DIA","IWM",
]


async def _prewarm():
    import asyncio
    from app.services.market_service import get_bulk_quotes, get_market_indices, get_market_movers
    from app.services.prediction_service import run_signals_batch, run_prediction
    try:
        # Stage 1: quotes + indices + movers all at once
        await asyncio.gather(
            get_bulk_quotes(_DASHBOARD_SYMBOLS),
            get_market_indices(),
            get_market_movers(),
            return_exceptions=True,
        )
        # Stage 2: signals for all 50 + top 10 full predictions — background tasks
        asyncio.create_task(run_signals_batch(_DASHBOARD_SYMBOLS))
        _top = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "META", "AMZN", "AMD", "SPY", "QQQ"]
        await asyncio.gather(*[run_prediction(s) for s in _top], return_exceptions=True)
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    asyncio.create_task(_prewarm())
    yield


app = FastAPI(
    title="TradeMind AI API",
    version="1.0.0",
    description="Enterprise AI-powered fintech platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(LoggingMiddleware)

_origins = settings.get_cors_origins()
_allow_all = "*" in _origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else _origins,
    allow_credentials=False if _allow_all else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus
Instrumentator().instrument(app).expose(app)

# Routes
app.include_router(router)


@app.websocket("/ws/market/{symbol}")
async def market_ws(websocket: WebSocket, symbol: str):
    await stock_ws_handler(websocket, symbol)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "TradeMind AI"}
