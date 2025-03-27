#!/usr/bin/env python3
"""Simple test script for COCONUT authentication."""

import os
import logging
from hyperblend.services.external.coconut_service import CoconutService
from hyperblend.database import get_graph

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main():
    """Test COCONUT authentication."""
    try:
        # Get credentials from environment
        email = os.getenv("COCONUT_EMAIL")
        password = os.getenv("COCONUT_PASSWORD")

        if not email or not password:
            logger.error("COCONUT_EMAIL or COCONUT_PASSWORD not set in environment")
            return

        logger.info(f"Testing authentication with email: {email}")

        # Initialize service
        service = CoconutService(email=email, password=password, graph=get_graph())

        # Test health check
        if service.health_check():
            logger.info("Authentication successful!")
        else:
            logger.error("Authentication failed!")

    except Exception as e:
        logger.error(f"Error during authentication test: {str(e)}")


if __name__ == "__main__":
    main()
