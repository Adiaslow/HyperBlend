# hyperblend/app/web/core/exceptions.py

class HyperBlendError(Exception):
    """Base exception for HyperBlend application."""
    pass

class DatabaseError(HyperBlendError):
    """Raised when there is an error with database operations."""
    pass

class ResourceNotFoundError(HyperBlendError):
    """Raised when a requested resource is not found."""
    pass

class ValidationError(HyperBlendError):
    """Raised when data validation fails."""
    pass

class ServiceError(HyperBlendError):
    """Raised when there is an error in service operations."""
    pass

class ExternalServiceError(ServiceError):
    """Raised when there is an error with external service operations."""
    pass 