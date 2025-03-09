from typing import List, Dict, Any
from neo4j import GraphDatabase
from hyperblend.app.config.settings import settings
from contextlib import contextmanager
import logging
import time
from neo4j.exceptions import ServiceUnavailable, SessionExpired


class Neo4jConnection:
    """Class for managing Neo4j database connections and queries."""

    def __init__(self):
        """Initialize the Neo4j connection using settings from config."""
        self.driver = None
        self._initialized = False
        self.logger = logging.getLogger(__name__)
        self.connect()

    def connect(self):
        """Establish connection to Neo4j database with retry mechanism."""
        if not self.driver:
            max_retries = 3
            retry_delay = 1  # seconds

            for attempt in range(max_retries):
                try:
                    self.driver = GraphDatabase.driver(
                        settings.NEO4J_URI,
                        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                        max_connection_pool_size=settings.NEO4J_MAX_CONNECTION_POOL_SIZE,
                        max_connection_lifetime=settings.NEO4J_MAX_CONNECTION_LIFETIME,
                    )
                    # Test the connection
                    with self.driver.session() as session:
                        session.run("RETURN 1")
                    self._initialized = True
                    self.logger.info("Successfully connected to Neo4j database")
                    break
                except Exception as e:
                    self.logger.error(
                        f"Attempt {attempt + 1}/{max_retries} failed to connect to Neo4j: {str(e)}"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        self.driver = None
                        self._initialized = False
                        raise

    def close(self):
        """Close the database connection."""
        if self.driver:
            try:
                self.driver.close()
            except Exception as e:
                self.logger.error(f"Error closing Neo4j connection: {str(e)}")
            finally:
                self.driver = None
                self._initialized = False

    def verify_connectivity(self) -> bool:
        """Verify database connection is working with retry mechanism."""
        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                if not self.driver:
                    self.connect()
                with self.driver.session() as session:
                    result = session.run("RETURN 1 as test")
                    value = result.single()
                    return value is not None and value.get("test") == 1
            except (ServiceUnavailable, SessionExpired) as e:
                self.logger.error(
                    f"Attempt {attempt + 1}/{max_retries} failed to verify connectivity: {str(e)}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    # Try to reconnect
                    self.close()
                    self.connect()
                else:
                    return False
            except Exception as e:
                self.logger.error(f"Unexpected error verifying connectivity: {str(e)}")
                return False
        return False

    def remove_duplicates(self):
        """Remove duplicate nodes from the database."""
        with self.driver.session() as session:
            # Remove duplicate molecules
            session.run(
                """
                MATCH (m1:Molecule)
                MATCH (m2:Molecule)
                WHERE m1.inchikey = m2.inchikey
                AND elementId(m1) < elementId(m2)
                DETACH DELETE m2
            """
            )
            # Remove duplicate organisms
            session.run(
                """
                MATCH (o1:Organism)
                MATCH (o2:Organism)
                WHERE o1.name = o2.name
                AND elementId(o1) < elementId(o2)
                DETACH DELETE o2
            """
            )
            # Remove duplicate targets
            session.run(
                """
                MATCH (t1:Target)
                MATCH (t2:Target)
                WHERE t1.name = t2.name
                AND elementId(t1) < elementId(t2)
                DETACH DELETE t2
            """
            )

    def cleanup_source_nodes(self):
        """Clean up incorrectly created source nodes and migrate source information to properties."""
        with self.driver.session() as session:
            # First, migrate source information to properties
            session.run(
                """
                MATCH (m:Molecule)-[r:FROM_ORGANISM]->(o:Organism)
                WHERE o.name IN ['PubChem', 'ChEMBL', 'COCONUT']
                SET m.source = o.name
                DELETE r
                """
            )

            # Then remove the source nodes
            session.run(
                """
                MATCH (o:Organism)
                WHERE o.name IN ['PubChem', 'ChEMBL', 'COCONUT']
                DELETE o
                """
            )

    def _create_constraints(self):
        """Create database constraints."""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Molecule) REQUIRE m.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Target) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (o:Organism) REQUIRE o.name IS UNIQUE",
        ]
        for constraint in constraints:
            self.run(constraint)

    def _create_indexes(self):
        """Create database indexes."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (m:Molecule) ON (m.smiles)",
            "CREATE INDEX IF NOT EXISTS FOR (m:Molecule) ON (m.inchikey)",
            "CREATE INDEX IF NOT EXISTS FOR (t:Target) ON (t.type)",
            "CREATE INDEX IF NOT EXISTS FOR (o:Organism) ON (o.type)",
        ]
        for index in indexes:
            try:
                self.run(index)
            except Exception as e:
                self.logger.error(f"Error creating index: {str(e)}")
                continue

    def _clean_duplicate_nodes(self):
        """Remove duplicate nodes based on name property."""
        queries = [
            """
            MATCH (m1:Molecule)
            WITH m1.name as name, collect(m1) as nodes
            WHERE size(nodes) > 1
            UNWIND tail(nodes) as m2
            DETACH DELETE m2
            """,
            """
            MATCH (t1:Target)
            WITH t1.name as name, collect(t1) as nodes
            WHERE size(nodes) > 1
            UNWIND tail(nodes) as t2
            DETACH DELETE t2
            """,
            """
            MATCH (o1:Organism)
            WITH o1.name as name, collect(o1) as nodes
            WHERE size(nodes) > 1
            UNWIND tail(nodes) as o2
            DETACH DELETE o2
            """,
        ]
        for query in queries:
            self.run(query)

    def create_constraints(self):
        """Create database constraints after cleaning duplicates."""
        # First clean up any duplicate nodes
        self._clean_duplicate_nodes()
        # Then create constraints
        self._create_constraints()

    def create_indexes(self):
        """Create database indexes."""
        self._create_indexes()

    def run(self, query: str, **parameters) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query with parameters.

        Args:
            query: The Cypher query to execute.
            **parameters: Query parameters.

        Returns:
            List[Dict[str, Any]]: List of records returned by the query.
        """
        if not self.driver:
            self.connect()
            if not self.driver:
                self.logger.error("Unable to establish database connection")
                return []

        try:
            with self.driver.session() as session:
                result = session.run(query, **parameters)
                return [dict(record) for record in result]
        except Exception as e:
            self.logger.error(f"Error executing query: {str(e)}")
            # If we get a connection error, try to reconnect once
            if "Connection" in str(e):
                self.close()
                self.connect()
                if self.driver:
                    try:
                        with self.driver.session() as session:
                            result = session.run(query, **parameters)
                            return [dict(record) for record in result]
                    except Exception as e2:
                        self.logger.error(
                            f"Error executing query after reconnect: {str(e2)}"
                        )
            return []

    def create_molecule_target_relationship(
        self,
        molecule_chembl_id: str,
        target_chembl_id: str,
        confidence_score: float,
        activities: List[Dict[str, Any]],
    ) -> bool:
        """
        Create or update a relationship between a molecule and a target.

        Args:
            molecule_chembl_id: ChEMBL molecule ID
            target_chembl_id: ChEMBL target ID
            confidence_score: Confidence score of the relationship
            activities: List of activity measurements

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create Cypher query
            query = """
                MATCH (m:Molecule {chembl_id: $molecule_id})
                MATCH (t:Target {chembl_id: $target_id})
                MERGE (m)-[r:BINDS_TO]->(t)
                SET r.confidence_score = CASE
                        WHEN $confidence_score > r.confidence_score OR r.confidence_score IS NULL
                        THEN $confidence_score
                        ELSE r.confidence_score
                    END,
                    r.activities = $activities,
                    r.updated_at = datetime()
                RETURN r
                """

            # Execute query
            result = self.run(
                query,
                molecule_id=molecule_chembl_id,
                target_id=target_chembl_id,
                confidence_score=confidence_score,
                activities=activities,
            )

            return bool(result)

        except Exception as e:
            self.logger.error(f"Error creating molecule-target relationship: {str(e)}")
            return False


# Create database instance
db = Neo4jConnection()
