"""Base service for external API interactions."""

import logging


class BaseService:
    """Base class for external API services."""

    def __init__(self):
        """Initialize the base service."""
        self.logger = logging.getLogger(self.__class__.__name__)
