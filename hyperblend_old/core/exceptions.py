"""Core exceptions for the HyperBlend package."""


class HyperBlendError(Exception):
    """Base exception for all HyperBlend errors."""

    pass


class ValidationError(HyperBlendError):
    """Raised when data validation fails."""

    pass


class DatabaseError(HyperBlendError):
    """Raised when database operations fail."""

    pass


class APIError(HyperBlendError):
    """Raised when external API calls fail."""

    pass


class ConfigurationError(HyperBlendError):
    """Raised when configuration is invalid or missing."""

    pass


class AuthenticationError(HyperBlendError):
    """Raised when authentication fails."""

    pass
