"""Request ID middleware."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from atlas_telemetry.metrics import REQUEST_COUNT, REQUEST_LATENCY
from atlas_telemetry.request_context import reset_request_id, set_request_id
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request IDs and record basic Prometheus HTTP metrics."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming = request.headers.get("x-request-id") or str(uuid.uuid4())
        token = set_request_id(incoming)
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = incoming
            return response
        finally:
            duration = time.perf_counter() - started
            path = request.url.path
            REQUEST_COUNT.labels(request.method, path, str(status_code)).inc()
            REQUEST_LATENCY.labels(request.method, path).observe(duration)
            reset_request_id(token)
