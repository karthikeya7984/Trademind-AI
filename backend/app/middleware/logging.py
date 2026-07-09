import time
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response: Response = await call_next(request)
        duration = round((time.time() - start) * 1000, 2)
        logger.info("request", method=request.method, path=request.url.path, status=response.status_code, duration_ms=duration)
        return response
