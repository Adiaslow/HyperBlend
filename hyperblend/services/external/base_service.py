"""Base class for external API services."""

import requests
import logging
import time
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod


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
        self.rate_limit = rate_limit
        self.session = self._create_session()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _create_session(self) -> requests.Session:
        """Create a session with retry capabilities."""
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            max_retries=3, pool_connections=10, pool_maxsize=10
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Make a request to the external API with rate limiting and error handling.

        Args:
            endpoint: API endpoint to call
            method: HTTP method to use
            params: Query parameters
            data: Request body data
            headers: Request headers

        Returns:
            Optional[Dict[str, Any]]: Response data if successful, None otherwise
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(
                method=method, url=url, params=params, json=data, headers=headers
            )
            response.raise_for_status()

            # Rate limiting
            time.sleep(self.rate_limit)

            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {str(e)}")
            return None

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
        self.session.close()
