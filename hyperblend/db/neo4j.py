from typing import List, Dict, Any
from neo4j import GraphDatabase
from hyperblend.config.settings import settings


class Neo4jConnection:
    """Class for managing Neo4j database connections and queries."""

    def __init__(self):
        """Initialize the Neo4j connection using settings from config."""
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

    def close(self):
        """Close the database connection."""
        self.driver.close()

    def run(self, query: str, **parameters) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query with parameters.

        Args:
            query: The Cypher query to execute.
            **parameters: Query parameters.

        Returns:
            List[Dict[str, Any]]: List of records returned by the query.
        """
        with self.driver.session() as session:
            result = session.run(query, **parameters)
            return [dict(record) for record in result]

    def verify_connectivity(self) -> bool:
        """
        Verify that the database connection is working.

        Returns:
            bool: True if connection is successful, False otherwise.
        """
        try:
            self.driver.verify_connectivity()
            return True
        except Exception:
            return False
