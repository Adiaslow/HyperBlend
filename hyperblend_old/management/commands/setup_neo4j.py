"""Command to set up Neo4j database with initial constraints and indexes."""

import argparse
import logging
from typing import List, Optional
from neo4j import Driver
from neo4j.work import Query
from hyperblend_old.config.neo4j import get_driver, Labels, Props, RelTypes
from hyperblend_old.management import register_command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_constraints_and_indexes(driver: Driver) -> None:
    """Set up Neo4j constraints and indexes."""
    with driver.session() as session:
        # Node constraints
        constraints = [
            Query(
                f"CREATE CONSTRAINT compound_id IF NOT EXISTS FOR (n:{Labels.COMPOUND}) REQUIRE n.{Props.ID} IS UNIQUE"
            ),
            Query(
                f"CREATE CONSTRAINT compound_canonical_name IF NOT EXISTS FOR (n:{Labels.COMPOUND}) REQUIRE n.{Props.CANONICAL_NAME} IS UNIQUE"
            ),
            Query(
                f"CREATE CONSTRAINT compound_pubchem IF NOT EXISTS FOR (n:{Labels.COMPOUND}) REQUIRE n.{Props.PUBCHEM_ID} IS UNIQUE"
            ),
            Query(
                f"CREATE CONSTRAINT compound_chembl IF NOT EXISTS FOR (n:{Labels.COMPOUND}) REQUIRE n.{Props.CHEMBL_ID} IS UNIQUE"
            ),
            # Source constraints
            Query(
                f"CREATE CONSTRAINT source_id IF NOT EXISTS FOR (n:{Labels.SOURCE}) REQUIRE n.{Props.ID} IS UNIQUE"
            ),
            Query(
                f"CREATE CONSTRAINT source_name IF NOT EXISTS FOR (n:{Labels.SOURCE}) REQUIRE n.{Props.NAME} IS UNIQUE"
            ),
            # Target constraints
            Query(
                f"CREATE CONSTRAINT target_id IF NOT EXISTS FOR (n:{Labels.TARGET}) REQUIRE n.{Props.ID} IS UNIQUE"
            ),
            Query(
                f"CREATE CONSTRAINT target_uniprot IF NOT EXISTS FOR (n:{Labels.TARGET}) REQUIRE n.{Props.UNIPROT_ID} IS UNIQUE"
            ),
            Query(
                f"CREATE CONSTRAINT target_chembl IF NOT EXISTS FOR (n:{Labels.TARGET}) REQUIRE n.{Props.CHEMBL_ID} IS UNIQUE"
            ),
            # Chemical Class constraints
            Query(
                f"CREATE CONSTRAINT class_id IF NOT EXISTS FOR (n:{Labels.CHEMICAL_CLASS}) REQUIRE n.{Props.ID} IS UNIQUE"
            ),
            Query(
                f"CREATE CONSTRAINT class_name IF NOT EXISTS FOR (n:{Labels.CHEMICAL_CLASS}) REQUIRE n.{Props.NAME} IS UNIQUE"
            ),
            # Effect constraints
            Query(
                f"CREATE CONSTRAINT effect_id IF NOT EXISTS FOR (n:{Labels.EFFECT}) REQUIRE n.{Props.ID} IS UNIQUE"
            ),
            Query(
                f"CREATE CONSTRAINT effect_name IF NOT EXISTS FOR (n:{Labels.EFFECT}) REQUIRE n.{Props.NAME} IS UNIQUE"
            ),
        ]

        # Indexes for properties we'll frequently search by
        indexes = [
            # Compound indexes
            Query(
                f"CREATE INDEX compound_smiles IF NOT EXISTS FOR (n:{Labels.COMPOUND}) ON (n.{Props.SMILES})"
            ),
            Query(
                f"CREATE INDEX compound_formula IF NOT EXISTS FOR (n:{Labels.COMPOUND}) ON (n.{Props.MOLECULAR_FORMULA})"
            ),
            # Target indexes
            Query(
                f"CREATE INDEX target_std_name IF NOT EXISTS FOR (n:{Labels.TARGET}) ON (n.standardized_name)"
            ),
            Query(
                f"CREATE INDEX target_gene IF NOT EXISTS FOR (n:{Labels.TARGET}) ON (n.gene_name)"
            ),
            # Source indexes
            Query(
                f"CREATE INDEX source_type IF NOT EXISTS FOR (n:{Labels.SOURCE}) ON (n.{Props.TYPE})"
            ),
            # Relationship indexes
            Query(
                f"CREATE INDEX compound_source_rel IF NOT EXISTS FOR ()-[r:{RelTypes.FOUND_IN}]-() ON (r.{Props.CREATED_AT})"
            ),
            Query(
                f"CREATE INDEX compound_target_rel IF NOT EXISTS FOR ()-[r:{RelTypes.BINDS_TO}]-() ON (r.{Props.ACTION_TYPE})"
            ),
        ]

        # Create constraints
        for constraint in constraints:
            try:
                session.run(constraint)
                logger.info(f"Created constraint: {str(constraint)}")
            except Exception as e:
                logger.error(f"Error creating constraint: {str(e)}")

        # Create indexes
        for index in indexes:
            try:
                session.run(index)
                logger.info(f"Created index: {str(index)}")
            except Exception as e:
                logger.error(f"Error creating index: {str(e)}")


@register_command("setup_neo4j")
async def command_setup_neo4j(args: List[str]) -> None:
    """Set up Neo4j database with initial constraints and indexes."""
    parser = argparse.ArgumentParser(
        description="Set up Neo4j database with initial constraints and indexes"
    )
    parser.parse_args(args)

    driver: Optional[Driver] = None
    try:
        driver = get_driver()
        setup_constraints_and_indexes(driver)
        logger.info("Neo4j database setup completed successfully!")

    except Exception as e:
        logger.error(f"Neo4j database setup failed: {str(e)}")
        raise

    finally:
        if driver:
            driver.close()
