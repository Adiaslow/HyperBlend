"""Database module initialization."""

import logging
from py2neo import Graph
from hyperblend.app.config.settings import settings

logger = logging.getLogger(__name__)

def get_graph() -> Graph:
    """Get a connection to the Neo4j database.

    Returns:
        Graph: A py2neo Graph object connected to the Neo4j database.
    
    Raises:
        ConnectionError: If unable to connect to the database.
    """
    try:
        graph = Graph(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            name="neo4j"  # Explicitly set database name
        )
        
        # Test the connection and get node count
        result = graph.run("MATCH (n) RETURN count(n) as count").data()
        node_count = result[0]['count'] if result else 0
        logger.info(f"Successfully connected to Neo4j database. Found {node_count} nodes.")
        
        return graph
    except Exception as e:
        error_msg = (
            f"Failed to connect to Neo4j database:\n"
            f"URI: {settings.NEO4J_URI}\n"
            f"Error: {str(e)}\n"
            "Please check:\n"
            "1. Neo4j server is running\n"
            "2. Connection credentials are correct\n"
            "3. Network connectivity to Neo4j server\n"
            "4. Neo4j server logs for any issues"
        )
        logger.error(error_msg)
        raise ConnectionError(error_msg)
