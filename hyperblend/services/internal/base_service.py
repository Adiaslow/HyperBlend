"""Base service for internal database queries."""

import logging
from typing import Any, Dict, List, Optional, Union
from py2neo import Graph
from hyperblend.utils.db_utils import DatabaseUtils, DatabaseError


class BaseService:
    """Base class for all internal services."""

    def __init__(self, graph: Graph):
        """
        Initialize the base service.

        Args:
            graph: Neo4j graph database connection
        """
        self.graph = graph
        self.db_utils = DatabaseUtils(graph)
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
        return self.db_utils.validate_id(id_value)

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

    def run_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
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
            return self.db_utils.run_query(query, parameters)
        except DatabaseError as e:
            # Re-raise with original message
            raise
        except Exception as e:
            self._handle_db_error(e, f"executing query: {query}")

    def standardize_id(
        self, id_value: Union[str, int], entity_type: str = "molecule"
    ) -> str:
        """
        Standardize ID formats across the application.

        Args:
            id_value: The ID value to standardize
            entity_type: Type of entity ('molecule', 'target', 'organism', 'effect')

        Returns:
            A standardized ID string suitable for database queries
        """
        return self.db_utils.standardize_id(id_value, entity_type)

    def generate_next_id(self, entity_type: str) -> str:
        """
        Generate the next available ID for a given entity type.

        Args:
            entity_type: The type of entity ('molecule', 'organism', 'target', 'effect')

        Returns:
            A string ID in the format {prefix}-{next_number}
        """
        return self.db_utils.generate_next_id(entity_type)
