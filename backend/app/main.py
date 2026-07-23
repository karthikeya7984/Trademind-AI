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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create DB tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        pass

    # Pre-warm cache in background so dashboard loads fast on first visit
    import asyncio
    async def _prewarm():
        try:
            from app.services.market_service import get_market_indices, get_market_movers, get_bulk_quotes
            from app.services.prediction_service import run_signals_batch
            TOP_SYMBOLS = [
                "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA",
                "AMD", "NFLX", "JPM", "V", "SPY", "QQQ",
            ]
            await asyncio.gather(
                get_market_indices(),
                get_market_movers(),
                get_bulk_quotes(TOP_SYMBOLS),
                return_exceptions=True,
            )
            # Signals pre-warm in background (slower, don't block startup)
            asyncio.create_task(run_signals_batch(TOP_SYMBOLS))
        except Exception:
            pass
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


@app.get("/")
async def root():
    return {"status": "ok", "service": "TradeMind AI"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "TradeMind AI"}
