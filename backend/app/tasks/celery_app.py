"""Celery task queue configuration."""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "trademind",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "refresh-market-cache": {
            "task": "app.tasks.tasks.refresh_market_cache",
            "schedule": 60.0,
        },
        "retrain-models-weekly": {
            "task": "app.tasks.tasks.retrain_models",
            "schedule": 604800.0,  # 7 days
        },
    },
)
