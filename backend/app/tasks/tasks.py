"""Background Celery tasks."""
import asyncio
from app.tasks.celery_app import celery_app
from app.core.redis import cache_delete
import structlog

logger = structlog.get_logger()

POPULAR_SYMBOLS = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "AMD", "NFLX", "INTC"]


@celery_app.task(name="app.tasks.tasks.refresh_market_cache")
def refresh_market_cache():
    """Clear market cache to force fresh data on next request."""
    async def _run():
        for symbol in POPULAR_SYMBOLS:
            await cache_delete(f"quote:{symbol}")
            await cache_delete(f"prediction:{symbol}")
        await cache_delete("market:movers")
        logger.info("market_cache_refreshed", symbols=len(POPULAR_SYMBOLS))

    asyncio.run(_run())


@celery_app.task(name="app.tasks.tasks.retrain_models")
def retrain_models():
    """Placeholder for model retraining pipeline."""
    logger.info("model_retraining_started")
    # In production: trigger ML training pipeline
    # Could call SageMaker, run training scripts, update model artifacts
    logger.info("model_retraining_completed")
