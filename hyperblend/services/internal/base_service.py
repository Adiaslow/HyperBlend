"""Base service for internal database queries."""

from flask import current_app, g
from py2neo import Graph
from hyperblend.app.web.core.exceptions import DatabaseError
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class BaseService:
    """Base class for all internal services."""

    def __init__(self, graph: Graph):
        """
        Initialize the base service.
        
        Args:
            graph: Neo4j graph database connection
        """
        self.graph = graph
        self.logger = logging.getLogger(self.__class__.__name__)

    def _validate_id(self, id_value: str) -> int:
        """
        Validate and convert string ID to integer.

        Args:
            id_value: String ID to validate

        Returns:
            Integer ID

        Raises:
            ValueError: If ID is not valid
        """
        try:
            return int(id_value)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid ID format: {id_value}")

    def _handle_db_error(self, error: Exception, operation: str):
        """
        Handle database errors consistently.

        Args:
            error: The exception that occurred
            operation: Description of the operation that failed

        Raises:
            DatabaseError: With formatted error message
        """
        error_msg = f"Database error during {operation}: {str(error)}"
        self.logger.error(error_msg)
        raise DatabaseError(error_msg)

    def run_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Run a Cypher query safely with error handling.

        Args:
            query: The Cypher query to execute
            parameters: Optional parameters for the query

        Returns:
            List of records as dictionaries

        Raises:
            DatabaseError: If there's an error executing the query
        """
        try:
            result = self.graph.run(query, parameters or {})
            return result.data()
        except Exception as e:
            self._handle_db_error(e, f"executing query: {query}")
