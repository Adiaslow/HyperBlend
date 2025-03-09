"""Database connection module for Neo4j."""

import os
from py2neo import Graph
from typing import Optional

# Global graph connection
_graph: Optional[Graph] = None


def get_graph() -> Graph:
    """
    Get or create Neo4j graph database connection.

    Returns:
        Graph: Neo4j graph database connection
    """
    global _graph
    if _graph is None:
        # Get connection details from environment variables or use defaults
        host = os.getenv("NEO4J_HOST", "localhost")
        port = os.getenv("NEO4J_PORT", "7474")  # Using HTTP port
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "hyperblend")

        # Create connection
        _graph = Graph(f"http://{host}:{port}", auth=(user, password))

    return _graph
