# hyperblend/app/web/core/__init__.py

from .exceptions import (
    HyperBlendError,
    DatabaseError,
    ResourceNotFoundError,
    ValidationError,
    ServiceError,
    ExternalServiceError
)

from .decorators import (
    handle_db_error,
    handle_service_error,
    validate_json,
    cors_enabled
)

__all__ = [
    'HyperBlendError',
    'DatabaseError',
    'ResourceNotFoundError',
    'ValidationError',
    'ServiceError',
    'ExternalServiceError',
    'handle_db_error',
    'handle_service_error',
    'validate_json',
    'cors_enabled'
]
