"""Exception hierarchy for predictable ATLAS failures."""


class AtlasError(Exception):
    """Base exception for application-level ATLAS errors."""


class ConfigError(AtlasError):
    """Raised when required configuration is missing or invalid."""


class NotFoundError(AtlasError):
    """Raised when a requested ATLAS resource cannot be found."""


class DependencyError(AtlasError):
    """Raised when an infrastructure dependency is unavailable."""


class UnauthorizedError(AtlasError):
    """Raised when authentication is missing or invalid."""


class ForbiddenError(AtlasError):
    """Raised when the caller lacks permission."""
