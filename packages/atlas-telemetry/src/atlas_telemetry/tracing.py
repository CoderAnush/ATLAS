"""OpenTelemetry setup with safe no-op behavior when unconfigured."""

import logging

logger = logging.getLogger(__name__)


def setup_tracing(service_name: str, endpoint: str | None = None) -> bool:
    """Configure OTLP tracing when an endpoint and exporter are available.

    Returns ``False`` without side effects when tracing is intentionally not
    configured or the optional OTLP exporter is absent.
    """
    if endpoint is None:
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning("OTLP tracing requested but the optional exporter is not installed.")
        return False

    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    return True
