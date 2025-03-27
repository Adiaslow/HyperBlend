"""Database utilities for common database operations."""

import logging
import time
import traceback
from typing import Dict, List, Any, Optional, Union, Tuple
from contextlib import contextmanager
from py2neo import Graph, Node, Relationship, NodeMatcher


class DatabaseError(Exception):
    """Exception raised for database-related errors."""

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        self.message = message
        self.original_exception = original_exception
        super().__init__(self.message)


class DatabaseUtils:
    """Utility class for common database operations."""

    def __init__(self, graph: Graph):
        """
        Initialize the database utilities.

        Args:
            graph: Neo4j graph database connection
        """
        self.graph = graph
        self.matcher = NodeMatcher(graph)
        self.logger = logging.getLogger(__name__)

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
        """
        if parameters is None:
            parameters = {}

        max_retries = 3
        retry_count = 0
        last_error = None

        while retry_count < max_retries:
            try:
                # Only log query details at INFO level for complex/custom queries
                if "CREATE" in query or "DELETE" in query or "MERGE" in query:
                    self.logger.info(
                        f"Executing query: {query[:100]}{'...' if len(query) > 100 else ''}"
                    )

                # Only log sensitive parameters at DEBUG level, which we've now raised to INFO
                # To prevent credentials and other sensitive data from appearing in logs
                filtered_params = {}
                for k, v in parameters.items():
                    if k.lower() in (
                        "password",
                        "token",
                        "key",
                        "secret",
                        "credentials",
                    ):
                        filtered_params[k] = "********"
                    else:
                        filtered_params[k] = v

                # Add timeout to prevent long-running queries
                start_time = time.time()
                result = self.graph.run(query, parameters)

                try:
                    data = result.data()
                    query_time = time.time() - start_time
                    if query_time > 5:  # Log slow queries (>5s)
                        self.logger.warning(
                            f"Slow query ({query_time:.2f}s): {query[:100]}{'...' if len(query) > 100 else ''}"
                        )

                    # Only log the result count, not details, at INFO level
                    if len(data) > 0:
                        self.logger.info(f"Query returned {len(data)} results")
                    return data
                except Exception as e:
                    # Handle error during result processing
                    self.logger.error(f"Error processing query results: {str(e)}")
                    return []

            except Exception as e:
                retry_count += 1
                last_error = e
                self.logger.warning(
                    f"Database error (attempt {retry_count}/{max_retries}): {str(e)}"
                )

                # Only retry on connection/timeout errors
                if "connection" in str(e).lower() or "timeout" in str(e).lower():
                    time.sleep(0.5)  # Wait before retrying
                else:
                    # Don't retry on other errors
                    break

        # Log the final error if all retries failed
        if last_error:
            error_msg = (
                f"Database error after {retry_count} attempts: {str(last_error)}"
            )
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())

        # Return empty results instead of raising
        return []

    def standardize_id(self, id_value: str, entity_type: str = None) -> str:
        """
        Standardize an ID to follow the format X-y where X is the entity type prefix and y is a number.

        Args:
            id_value: ID to standardize
            entity_type: Entity type (e.g., 'Molecule', 'Target')

        Returns:
            Standardized ID
        """
        if id_value is None:
            self.logger.error("None ID provided to standardize_id")
            if entity_type:
                return self.get_next_available_id(entity_type)
            return ""

        if not id_value:
            self.logger.error("Empty ID provided to standardize_id")
            if entity_type:
                return self.get_next_available_id(entity_type)
            return ""

        # Get entity type prefix
        prefix = self._get_entity_prefix(entity_type) if entity_type else None

        # Check if ID already follows the standard format
        if prefix and id_value.startswith(f"{prefix}-"):
            return id_value

        # Generate a new standardized ID
        return self.get_next_available_id(entity_type)

    def get_next_available_id(self, entity_type: str) -> str:
        """
        Get the next available ID for an entity type.
        The ID format is X-y where X is the entity type prefix and y is the lowest available number.

        Args:
            entity_type: Entity type (e.g., 'Molecule', 'Target')

        Returns:
            Next available ID
        """
        prefix = self._get_entity_prefix(entity_type)
        if not prefix:
            self.logger.error(f"Unknown entity type: {entity_type}")
            return f"unknown-{hash(entity_type) % 1000}"

        try:
            # Get all existing IDs for this entity type
            query = f"""
            MATCH (e:{entity_type})
            WHERE e.id =~ '{prefix}-\\d+'
            RETURN e.id AS id
            """

            results = self.run_query(query)

            # Extract numbers from the IDs
            existing_numbers = set()
            for result in results:
                if "id" in result and result["id"]:
                    try:
                        # Extract number part after the prefix
                        id_parts = result["id"].split("-")
                        if len(id_parts) > 1 and id_parts[1].isdigit():
                            existing_numbers.add(int(id_parts[1]))
                    except Exception as e:
                        self.logger.warning(
                            f"Error parsing ID {result['id']}: {str(e)}"
                        )

            # Find the lowest available number
            next_number = 1
            while next_number in existing_numbers:
                next_number += 1

            return f"{prefix}-{next_number}"
        except Exception as e:
            self.logger.error(f"Error getting next available ID: {str(e)}")
            import traceback

            self.logger.error(traceback.format_exc())
            # Fallback to a timestamp-based ID
            import time

            return f"{prefix}-{int(time.time() % 10000)}"

    def _get_entity_prefix(self, entity_type: str) -> str:
        """
        Get the prefix for an entity type.

        Args:
            entity_type: Entity type (e.g., 'Molecule', 'Target')

        Returns:
            Prefix
        """
        prefix_map = {"Molecule": "M", "Target": "T", "Organism": "O", "Effect": "E"}

        return prefix_map.get(entity_type, entity_type[0].upper())

    def validate_id(self, id_value: str) -> int:
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

    def find_node(
        self, label: str, property_name: str, property_value: Any
    ) -> Optional[Node]:
        """
        Find a node by a specific property.

        Args:
            label: Node label
            property_name: Property name to match
            property_value: Property value to match

        Returns:
            Optional[Node]: Found node or None
        """
        try:
            return self.matcher.match(label, **{property_name: property_value}).first()
        except Exception as e:
            self.logger.error(f"Error finding node: {str(e)}")
            return None

    def create_or_merge_node(
        self, label: str, key_properties: Dict[str, Any], properties: Dict[str, Any]
    ) -> Node:
        """
        Create a new node or merge with existing one.

        Args:
            label: Node label
            key_properties: Properties that uniquely identify the node
            properties: All node properties

        Returns:
            Node: Created or merged node
        """
        try:
            node = Node(label, **properties)
            self.graph.merge(node, label, *key_properties.keys())
            return node
        except Exception as e:
            self.logger.error(f"Error creating/merging node: {str(e)}")
            raise

    def create_relationship(
        self,
        from_node: Node,
        relationship_type: str,
        to_node: Node,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Relationship:
        """
        Create a relationship between two nodes.

        Args:
            from_node: Source node
            relationship_type: Type of relationship
            to_node: Target node
            properties: Optional relationship properties

        Returns:
            Relationship: Created relationship
        """
        try:
            rel = Relationship(from_node, relationship_type, to_node)
            if properties:
                for key, value in properties.items():
                    rel[key] = value
            self.graph.create(rel)
            return rel
        except Exception as e:
            self.logger.error(f"Error creating relationship: {str(e)}")
            raise

    def find_or_create_source_node(self, source: str) -> Node:
        """
        Find or create a source node.

        Args:
            source: Source name

        Returns:
            Node: Source node
        """
        try:
            source_node = self.find_node("Source", "name", source)
            if not source_node:
                source_node = Node("Source", name=source)
                self.graph.create(source_node)
            return source_node
        except Exception as e:
            self.logger.error(f"Error finding/creating source node: {str(e)}")
            raise
