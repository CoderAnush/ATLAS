"""Context-local request correlation identifiers."""

from contextvars import ContextVar, Token

_request_id: ContextVar[str | None] = ContextVar("atlas_request_id", default=None)


def get_request_id() -> str | None:
    """Return the request identifier for the current execution context."""
    return _request_id.get()


def set_request_id(request_id: str | None) -> Token[str | None]:
    """Set and return a reset token for the current request identifier."""
    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the prior request identifier using a context token."""
    _request_id.reset(token)
