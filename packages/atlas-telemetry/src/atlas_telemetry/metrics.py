"""Prometheus metrics primitives for HTTP-serving ATLAS components."""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUEST_COUNT = Counter(
    "atlas_http_requests_total",
    "Total number of HTTP requests handled by ATLAS.",
    ("method", "path", "status"),
)
REQUEST_LATENCY = Histogram(
    "atlas_http_request_duration_seconds",
    "Duration of HTTP requests handled by ATLAS.",
    ("method", "path"),
)


def generate_metrics() -> tuple[bytes, str]:
    """Return the Prometheus exposition payload and its content type."""
    return generate_latest(), CONTENT_TYPE_LATEST
