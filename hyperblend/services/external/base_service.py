"""Base class for external API services."""

import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from hyperblend.utils.http_utils import HttpClient


class BaseExternalService(ABC):
    """Base class for external API services with common functionality."""

    def __init__(self, base_url: str, rate_limit: float = 0.2):
        """
        Initialize the external service.

        Args:
            base_url: Base URL for the API
            rate_limit: Time in seconds to wait between requests
        """
        self.base_url = base_url
        self.http_client = HttpClient(base_url, rate_limit)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        json_response: bool = True,
    ) -> Any:
        """
        Make a request to the external API with rate limiting and error handling.

        Args:
            endpoint: API endpoint to call
            method: HTTP method to use
            params: Query parameters
            data: Request body data
            headers: Request headers
            json_response: Whether to parse response as JSON

        Returns:
            Any: Response data if successful, None otherwise
        """
        return self.http_client.make_request(
            endpoint, method, params, data, headers, json_response
        )

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the external service is available.

        Returns:
            bool: True if service is available, False otherwise
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.http_client.close()
