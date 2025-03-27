#!/usr/bin/env python3
"""Minimal test script for COCONUT authentication."""

import os
import logging
import requests
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class CoconutAuthTest:
    """Simple class to test COCONUT authentication."""

    BASE_URL = "https://coconut.naturalproducts.net/api"

    def __init__(self, email: str, password: str):
        """Initialize with credentials."""
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.session.headers.update(
            {"accept": "application/json", "Content-Type": "application/json"}
        )

    def authenticate(self) -> bool:
        """Test authentication with COCONUT API."""
        try:
            auth_payload = {"email": self.email, "password": self.password}
            logger.info(
                f"Attempting to authenticate with COCONUT API using email: {self.email}"
            )

            response = self.session.post(
                f"{self.BASE_URL}/auth/login", json=auth_payload
            )

            # Log response details
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")

            if response.status_code != 200:
                logger.error(
                    f"Authentication failed with status {response.status_code}"
                )
                logger.error(f"Response body: {response.text}")
                return False

            data = response.json()
            logger.debug(f"Response data: {data}")

            token = data.get("access_token")
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
                logger.info("Successfully authenticated with COCONUT API")
                return True
            else:
                logger.error("No access token received in response")
                return False

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False

    def health_check(self) -> bool:
        """Check if the service is healthy by performing a simple molecule search."""
        try:
            # Try a simpler search payload
            search_payload = {
                "filters": [
                    {"field": "name", "operator": "like", "value": "Mescaline"}
                ],
                "selects": [{"field": "name"}],
                "page": 1,
                "limit": 1,
            }

            response = self.session.post(
                f"{self.BASE_URL}/molecules/search", json=search_payload
            )

            if response.status_code == 200:
                logger.info("Service is available and authenticated")
                return True
            else:
                logger.error(f"Service check failed with status {response.status_code}")
                logger.error(f"Response body: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Health check error: {str(e)}")
            return False


def main():
    """Run the authentication test."""
    # Get credentials from environment
    email = os.getenv("COCONUT_EMAIL")
    password = os.getenv("COCONUT_PASSWORD")

    if not email or not password:
        logger.error("COCONUT_EMAIL or COCONUT_PASSWORD not set in environment")
        return

    # Create test instance
    test = CoconutAuthTest(email, password)

    # Test authentication
    if test.authenticate():
        logger.info("Authentication successful!")

        # Test health check
        if test.health_check():
            logger.info("Health check successful!")
        else:
            logger.error("Health check failed!")
    else:
        logger.error("Authentication failed!")


if __name__ == "__main__":
    main()
