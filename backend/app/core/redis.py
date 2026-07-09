import json
from typing import Optional
import time

_store: dict = {}  # {key: (value, expires_at)}

try:
    import redis.asyncio as aioredis
    from app.core.config import settings
    _redis_client = None
    _redis_available = True
except ImportError:
    _redis_available = False


async def _get_redis():
    global _redis_client
    if not _redis_available:
        return None
    try:
        from app.core.config import settings
        if _redis_client is None:
            import redis.asyncio as aioredis
            _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1)
        await _redis_client.ping()
        return _redis_client
    except Exception:
        return None


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
