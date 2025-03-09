"""Database module initialization."""

import os
from py2neo import Graph


def get_graph() -> Graph:
    """Get a connection to the Neo4j database.

    Returns:
        Graph: A py2neo Graph object connected to the Neo4j database.
    """
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")

    return Graph(uri, auth=(username, password))
