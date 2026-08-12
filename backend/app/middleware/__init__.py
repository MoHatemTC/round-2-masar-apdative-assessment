"""
Lightweight request-timing middleware.

Logs method, path, status code, and wall-clock duration for every HTTP request.
Attach to the FastAPI app via ``app.middleware("http")(timing_middleware)``.
"""

import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("timing")


class TimingMiddleware(BaseHTTPMiddleware):
    """Measure and log the wall-clock time of every request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "%s %s → %d  (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )

        # Expose timing to the client via a response header (useful for DevTools).
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"
        return response
