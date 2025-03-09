# hyperblend/scripts/clear_data.py

import logging
from typing import Optional, Dict
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable
import argparse
from dotenv import load_dotenv
import os

logger = logging.getLogger(__name__)


class DatabaseCleaner:
    """Class for cleaning data from the Neo4j database."""

    def __init__(self):
        """Initialize the database connection."""
        load_dotenv()
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")

        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # Test the connection
            self.driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j database")
        except ServiceUnavailable as e:
            logger.error(f"Failed to connect to Neo4j database: {str(e)}")
            raise

    def close(self):
        """Close the database connection."""
        if hasattr(self, "driver"):
            self.driver.close()

    def _execute_delete_query(self, label: str) -> int:
        """
        Execute a delete query for a specific node label.

        Args:
            label: The node label to delete (e.g., 'Target', 'Molecule', 'Organism')

        Returns:
            int: Number of nodes deleted
        """
        with self.driver.session() as session:
            try:
                result = session.run(
                    f"""
                    MATCH (n:{label})
                    WITH n
                    OPTIONAL MATCH (n)-[r]-()
                    WITH n, collect(r) as rels
                    CALL {{ WITH n, rels
                        FOREACH (r IN rels | DELETE r)
                        DELETE n
                    }}
                    RETURN count(n) as deleted_count
                    """
                )
                record = result.single()
                if record is None:
                    return 0
                return record.get("deleted_count", 0)
            except Neo4jError as e:
                logger.error(f"Error clearing {label}s: {str(e)}")
                return 0

    def clear_targets(self) -> int:
        """
        Clear all targets and their relationships from the database.

        Returns:
            int: Number of targets deleted
        """
        deleted_count = self._execute_delete_query("Target")
        logger.info(f"Deleted {deleted_count} targets and their relationships")
        return deleted_count

    def clear_molecules(self) -> int:
        """
        Clear all molecules and their relationships from the database.

        Returns:
            int: Number of molecules deleted
        """
        deleted_count = self._execute_delete_query("Molecule")
        logger.info(f"Deleted {deleted_count} molecules and their relationships")
        return deleted_count

    def clear_organisms(self) -> int:
        """
        Clear all organisms and their relationships from the database.

        Returns:
            int: Number of organisms deleted
        """
        deleted_count = self._execute_delete_query("Organism")
        logger.info(f"Deleted {deleted_count} organisms and their relationships")
        return deleted_count

    def clear_all(self) -> Dict[str, int]:
        """
        Clear all data from the database.

        Returns:
            dict: Dictionary containing counts of deleted nodes by type
        """
        return {
            "targets": self.clear_targets(),
            "molecules": self.clear_molecules(),
            "organisms": self.clear_organisms(),
        }

    def verify_empty_database(self) -> Dict[str, int]:
        """
        Verify that the database is empty by checking node counts.

        Returns:
            dict: Dictionary containing current counts of each node type
        """
        with self.driver.session() as session:
            try:
                result = session.run(
                    """
                    MATCH (n)
                    WHERE n:Target OR n:Molecule OR n:Organism
                    RETURN 
                        count(n:Target) as target_count,
                        count(n:Molecule) as molecule_count,
                        count(n:Organism) as organism_count
                """
                )
                record = result.single()
                if record is None:
                    return {"targets": 0, "molecules": 0, "organisms": 0}

                return {
                    "targets": record.get("target_count", 0),
                    "molecules": record.get("molecule_count", 0),
                    "organisms": record.get("organism_count", 0),
                }
            except Neo4jError as e:
                logger.error(f"Error verifying database state: {str(e)}")
                return {"error": str(e)}


def main():
    """Main function to handle command line arguments and execute cleaning operations."""
    parser = argparse.ArgumentParser(description="Clear data from the Neo4j database")
    parser.add_argument(
        "--type",
        choices=["targets", "molecules", "organisms", "all"],
        help="Type of data to clear from the database",
    )
    parser.add_argument(
        "--verify", action="store_true", help="Verify database state after clearing"
    )

    args = parser.parse_args()

    if not args.type:
        parser.print_help()
        return

    try:
        cleaner = DatabaseCleaner()

        if args.type == "all":
            counts = cleaner.clear_all()
            print(
                f"Cleared {counts['targets']} targets, {counts['molecules']} molecules, "
                f"and {counts['organisms']} organisms from the database"
            )
        elif args.type == "targets":
            count = cleaner.clear_targets()
            print(f"Cleared {count} targets from the database")
        elif args.type == "molecules":
            count = cleaner.clear_molecules()
            print(f"Cleared {count} molecules from the database")
        elif args.type == "organisms":
            count = cleaner.clear_organisms()
            print(f"Cleared {count} organisms from the database")

        if args.verify:
            remaining = cleaner.verify_empty_database()
            print("\nVerification results:")
            print(f"Remaining targets: {remaining['targets']}")
            print(f"Remaining molecules: {remaining['molecules']}")
            print(f"Remaining organisms: {remaining['organisms']}")

    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    finally:
        cleaner.close()

    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    exit(main())
