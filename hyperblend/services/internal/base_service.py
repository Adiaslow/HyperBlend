"""Base service for internal database queries."""

import logging
from typing import Optional
from py2neo import Graph


class BaseInternalService:
    """Base class for internal database services."""

    def __init__(self, graph: Graph):
        """
        Initialize the internal service.

        Args:
            graph: Neo4j graph database connection
        """
        self.graph = graph
        self.logger = logging.getLogger(self.__class__.__name__)
