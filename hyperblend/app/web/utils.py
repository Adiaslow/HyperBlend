from py2neo import Graph
from hyperblend.app.config.settings import settings
import logging
import time

logger = logging.getLogger(__name__)


def get_neo4j_connection():
    """Get Neo4j graph connection with retries and exponential backoff."""
    max_retries = 3
    retry_count = 0
    base_delay = 1  # Base delay in seconds

    while retry_count < max_retries:
        try:
            logger.info(
                f"Attempting to establish Neo4j connection (attempt {retry_count + 1}/{max_retries})"
            )
            graph = Graph(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                name="neo4j",  # Explicitly set database name
            )
            # Test the connection with a simple query
            graph.run("MATCH (n) RETURN count(n) as count LIMIT 1")
            logger.info("Successfully established Neo4j connection")
            return graph
        except Exception as e:
            retry_count += 1
            delay = base_delay * (2 ** (retry_count - 1))  # Exponential backoff
            logger.error(
                f"Failed to establish Neo4j connection (attempt {retry_count}/{max_retries}): {str(e)}\n"
                f"Connection details: URI={settings.NEO4J_URI}\n"
                f"Will retry in {delay} seconds..."
            )
            if retry_count < max_retries:
                time.sleep(delay)
            else:
                logger.error(
                    "All Neo4j connection attempts failed. Please check:\n"
                    "1. Neo4j server is running\n"
                    "2. Connection credentials are correct\n"
                    "3. Network connectivity to Neo4j server\n"
                    "4. Neo4j server logs for any issues"
                )
                return None
    return None


def get_molecule_repository():
    """Get the MoleculeRepository from Flask global context or create a new one."""
    from flask import g
    from hyperblend.repository.molecule_repository import MoleculeRepository

    if hasattr(g, "molecule_repository"):
        return g.molecule_repository

    # If no repository in context, create one
    graph = get_neo4j_connection()
    if not graph:
        logger.error("Unable to establish database connection for MoleculeRepository")
        return None

    try:
        return MoleculeRepository(graph)
    except Exception as e:
        logger.error(f"Error creating MoleculeRepository: {str(e)}")
        return None


def get_target_repository():
    """Get the TargetRepository from Flask global context or create a new one."""
    from flask import g
    from hyperblend.repository.target_repository import TargetRepository

    if hasattr(g, "target_repository"):
        return g.target_repository

    # If no repository in context, create one
    graph = get_neo4j_connection()
    if not graph:
        logger.error("Unable to establish database connection for TargetRepository")
        return None

    try:
        return TargetRepository(graph)
    except Exception as e:
        logger.error(f"Error creating TargetRepository: {str(e)}")
        return None


def get_organism_repository():
    """Get the OrganismRepository from Flask global context or create a new one."""
    from flask import g
    from hyperblend.repository.organism_repository import OrganismRepository

    if hasattr(g, "organism_repository"):
        return g.organism_repository

    # If no repository in context, create one
    graph = get_neo4j_connection()
    if not graph:
        logger.error("Unable to establish database connection for OrganismRepository")
        return None

    try:
        return OrganismRepository(graph)
    except Exception as e:
        logger.error(f"Error creating OrganismRepository: {str(e)}")
        return None


def get_effect_repository():
    """Get the EffectRepository from Flask global context or create a new one."""
    from flask import g
    from hyperblend.repository.effect_repository import EffectRepository

    if hasattr(g, "effect_repository"):
        return g.effect_repository

    # If no repository in context, create one
    graph = get_neo4j_connection()
    if not graph:
        logger.error("Unable to establish database connection for EffectRepository")
        return None

    try:
        return EffectRepository(graph)
    except Exception as e:
        logger.error(f"Error creating EffectRepository: {str(e)}")
        return None
