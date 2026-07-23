import json
from typing import Optional
import time

_store: dict = {}  # {key: (value, expires_at)}
_redis_client = None
_redis_checked = False  # only attempt connection once


async def _get_redis():
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    try:
        from app.core.config import settings
        import redis.asyncio as aioredis
        client = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1.0
        )
        await client.ping()
        _redis_client = client
    except Exception:
        _redis_client = None  # Falls back to in-memory _store
    return _redis_client


async def cache_set(key: str, value: str, ttl: int = 300):
    r = await _get_redis()
    if r:
        try:
            await r.setex(key, ttl, value)
            return
        except Exception:
            pass
    _store[key] = (value, time.time() + ttl)


async def cache_get(key: str) -> Optional[str]:
    r = await _get_redis()
    if r:
        try:
            return await r.get(key)
        except Exception:
            pass
    entry = _store.get(key)
    if entry and time.time() < entry[1]:
        return entry[0]
    _store.pop(key, None)
    return None


async def cache_delete(key: str):
    r = await _get_redis()
    if r:
        try:
            await r.delete(key)
        except Exception:
            pass
    _store.pop(key, None)
