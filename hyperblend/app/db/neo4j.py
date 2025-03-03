from typing import Optional, List, Dict, Any
from neo4j import GraphDatabase, Driver, Session
from contextlib import contextmanager
from hyperblend.config.settings import settings
import logging
import threading

logger = logging.getLogger(__name__)


class Neo4jDatabase:
    def __init__(self):
        self.driver = None
        self._initialized = False
        self._constraints_created = False
        self._indexes_created = False
        self._lock = threading.Lock()

    def connect(self):
        """Establish connection to Neo4j database."""
        try:
            logger.info("Attempting to connect to Neo4j database...")
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                max_connection_pool_size=50,
                connection_timeout=5,
                keep_alive=True,
            )

            # Verify connection
            with self.driver.session() as session:
                result = session.run("RETURN 1")
                result.single()
                logger.info("Successfully connected to Neo4j database")
                return True
        except Exception as e:
            logger.error(
                f"Failed to connect to Neo4j database: {str(e)}", exc_info=True
            )
            raise

    def close(self):
        """Close the database connection."""
        try:
            if self.driver:
                self.driver.close()
                logger.info("Neo4j database connection closed")
        except Exception as e:
            logger.error(f"Error closing Neo4j connection: {str(e)}", exc_info=True)

    def verify_connection(self):
        """Verify the database connection is active."""
        if not self.driver:
            self.connect()
        try:
            self.driver.verify_connectivity()
        except Exception as e:
            logger.error(f"Failed to verify Neo4j connection: {str(e)}")
            raise

    def create_constraints(self):
        """Create database constraints if they don't exist."""
        if self._constraints_created:
            return

        with self._lock:
            if not self._constraints_created:
                with self.driver.session() as session:
                    try:
                        # Create constraints for unique names
                        session.run(
                            """
                            CREATE CONSTRAINT compound_name IF NOT EXISTS
                            FOR (c:Compound) REQUIRE c.name IS UNIQUE
                        """
                        )
                        session.run(
                            """
                            CREATE CONSTRAINT source_name IF NOT EXISTS
                            FOR (s:Source) REQUIRE s.name IS UNIQUE
                        """
                        )
                        session.run(
                            """
                            CREATE CONSTRAINT target_name IF NOT EXISTS
                            FOR (t:Target) REQUIRE t.name IS UNIQUE
                        """
                        )
                        logger.info("Successfully created database constraints")
                        self._constraints_created = True
                    except Exception as e:
                        logger.error(f"Failed to create constraints: {str(e)}")
                        raise

    def create_indexes(self):
        """Create database indexes if they don't exist."""
        if self._indexes_created:
            return

        with self._lock:
            if not self._indexes_created:
                with self.driver.session() as session:
                    try:
                        # Create indexes for frequently queried properties
                        session.run(
                            """
                            CREATE INDEX compound_smiles IF NOT EXISTS
                            FOR (c:Compound) ON (c.smiles)
                        """
                        )
                        session.run(
                            """
                            CREATE INDEX source_type IF NOT EXISTS
                            FOR (s:Source) ON (s.type)
                        """
                        )
                        session.run(
                            """
                            CREATE INDEX target_type IF NOT EXISTS
                            FOR (t:Target) ON (t.type)
                        """
                        )
                        logger.info("Successfully created database indexes")
                        self._indexes_created = True
                        self._initialized = True
                    except Exception as e:
                        logger.error(f"Failed to create indexes: {str(e)}")
                        raise

    def remove_duplicates(self):
        """Remove duplicate compounds from the database."""
        with self.driver.session() as session:
            try:
                # Use a more efficient query to remove duplicates
                session.run(
                    """
                    MATCH (c:Compound)
                    WITH c.name as name, collect(c) as compounds
                    WHERE size(compounds) > 1
                    UNWIND compounds[1..] as duplicate
                    DETACH DELETE duplicate
                """
                )
                logger.info("Successfully removed duplicate compounds")
            except Exception as e:
                logger.error(f"Failed to remove duplicates: {str(e)}")
                raise

    @contextmanager
    def session(self):
        """Context manager for database sessions."""
        if not self.driver:
            self.connect()
        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()

    def execute_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return the results."""
        with self.session() as session:
            try:
                result = session.run(query, params or {})
                return [dict(record) for record in result]
            except Exception as e:
                logger.error(f"Failed to execute query: {str(e)}")
                raise

    def get_compound(self, compound_id: str) -> Optional[Dict[str, Any]]:
        """Get a compound by ID."""
        query = """
        MATCH (c:Compound)
        WHERE elementId(c) = $compound_id
        RETURN c
        """
        results = self.execute_query(query, {"compound_id": compound_id})
        return results[0]["c"] if results else None

    def get_compound_targets(self, compound_id: str) -> List[Dict[str, Any]]:
        """Get all targets for a compound."""
        query = """
        MATCH (c:Compound)-[r:INTERACTS_WITH]->(t:Target)
        WHERE elementId(c) = $compound_id
        RETURN t, r
        """
        return self.execute_query(query, {"compound_id": compound_id})

    def get_compound_sources(self, compound_id: str) -> List[Dict[str, Any]]:
        """Get all sources for a compound."""
        query = """
        MATCH (s:Source)-[r:PROVIDES]->(c:Compound)
        WHERE elementId(c) = $compound_id
        RETURN s, r
        """
        return self.execute_query(query, {"compound_id": compound_id})

    def get_graph_data(self, query: str = "") -> Dict[str, Any]:
        """Get graph data for visualization."""
        if query:
            cypher_query = """
            MATCH (c:Compound)
            WHERE c.name CONTAINS $query OR c.smiles CONTAINS $query
            OPTIONAL MATCH (c)-[r1:INTERACTS_WITH]->(t:Target)
            OPTIONAL MATCH (s:Source)-[r2:PROVIDES]->(c)
            RETURN c, collect(DISTINCT t) as targets, collect(DISTINCT s) as sources
            """
        else:
            cypher_query = """
            MATCH (c:Compound)
            OPTIONAL MATCH (c)-[r1:INTERACTS_WITH]->(t:Target)
            OPTIONAL MATCH (s:Source)-[r2:PROVIDES]->(c)
            RETURN c, collect(DISTINCT t) as targets, collect(DISTINCT s) as sources
            """

        results = self.execute_query(cypher_query, {"query": query})
        return {
            "nodes": [
                {
                    "id": record["c"].element_id,
                    "name": record["c"]["name"],
                    "type": "Compound",
                }
                for record in results
            ],
            "links": [
                {
                    "source": record["c"].element_id,
                    "target": target.element_id,
                    "type": "INTERACTS_WITH",
                }
                for record in results
                for target in record["targets"]
            ]
            + [
                {
                    "source": source.element_id,
                    "target": record["c"].element_id,
                    "type": "PROVIDES",
                }
                for record in results
                for source in record["sources"]
            ],
        }

    def get_statistics(self) -> Dict[str, int]:
        """Get database statistics."""
        query = """
        MATCH (c:Compound) WITH count(c) as compounds
        MATCH (s:Source) WITH compounds, count(s) as sources
        MATCH (t:Target) WITH compounds, sources, count(t) as targets
        RETURN compounds, sources, targets
        """
        results = self.execute_query(query)
        return results[0] if results else {"compounds": 0, "sources": 0, "targets": 0}


# Create global database instance
db = Neo4jDatabase()
