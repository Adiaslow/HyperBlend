# hyperblend/management/commands/migrate_to_neo4j.py

"""Command to migrate data from SQLite to Neo4j."""

import argparse
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import sqlite3
from tqdm import tqdm
from neo4j import Driver
from hyperblend_old.config.neo4j import get_driver, Labels, Props, RelTypes
from hyperblend_old.management import register_command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_constraints(driver: Driver) -> None:
    """Create Neo4j constraints for uniqueness and indexes."""
    constraints = [
        # Compound constraints
        f"CREATE CONSTRAINT compound_id IF NOT EXISTS FOR (n:{Labels.COMPOUND}) REQUIRE n.{Props.ID} IS UNIQUE",
        f"CREATE CONSTRAINT compound_canonical_name IF NOT EXISTS FOR (n:{Labels.COMPOUND}) REQUIRE n.{Props.CANONICAL_NAME} IS UNIQUE",
        f"CREATE CONSTRAINT compound_pubchem IF NOT EXISTS FOR (n:{Labels.COMPOUND}) REQUIRE n.{Props.PUBCHEM_ID} IS UNIQUE",
        f"CREATE CONSTRAINT compound_chembl IF NOT EXISTS FOR (n:{Labels.COMPOUND}) REQUIRE n.{Props.CHEMBL_ID} IS UNIQUE",
        # Source constraints
        f"CREATE CONSTRAINT source_id IF NOT EXISTS FOR (n:{Labels.SOURCE}) REQUIRE n.{Props.ID} IS UNIQUE",
        f"CREATE CONSTRAINT source_name IF NOT EXISTS FOR (n:{Labels.SOURCE}) REQUIRE n.{Props.NAME} IS UNIQUE",
        # Target constraints
        f"CREATE CONSTRAINT target_id IF NOT EXISTS FOR (n:{Labels.TARGET}) REQUIRE n.{Props.ID} IS UNIQUE",
        f"CREATE CONSTRAINT target_uniprot IF NOT EXISTS FOR (n:{Labels.TARGET}) REQUIRE n.{Props.UNIPROT_ID} IS UNIQUE",
        f"CREATE CONSTRAINT target_chembl IF NOT EXISTS FOR (n:{Labels.TARGET}) REQUIRE n.{Props.CHEMBL_ID} IS UNIQUE",
        # Chemical Class constraints
        f"CREATE CONSTRAINT class_id IF NOT EXISTS FOR (n:{Labels.CHEMICAL_CLASS}) REQUIRE n.{Props.ID} IS UNIQUE",
        f"CREATE CONSTRAINT class_name IF NOT EXISTS FOR (n:{Labels.CHEMICAL_CLASS}) REQUIRE n.{Props.NAME} IS UNIQUE",
        # Effect constraints
        f"CREATE CONSTRAINT effect_id IF NOT EXISTS FOR (n:{Labels.EFFECT}) REQUIRE n.{Props.ID} IS UNIQUE",
        f"CREATE CONSTRAINT effect_name IF NOT EXISTS FOR (n:{Labels.EFFECT}) REQUIRE n.{Props.NAME} IS UNIQUE",
    ]

    with driver.session() as session:
        for constraint in constraints:
            try:
                session.run(constraint)
                logger.info(f"Created constraint: {constraint}")
            except Exception as e:
                logger.error(f"Error creating constraint: {str(e)}")


def migrate_compounds(driver: Driver, sqlite_conn: sqlite3.Connection) -> None:
    """Migrate compounds from SQLite to Neo4j."""
    compounds_df = pd.read_sql("SELECT * FROM compounds", sqlite_conn)
    synonyms_df = pd.read_sql("SELECT * FROM compound_synonyms", sqlite_conn)

    with driver.session() as session:
        for _, compound in tqdm(compounds_df.iterrows(), desc="Migrating compounds"):
            # Create compound node
            cypher = f"""
            MERGE (c:{Labels.COMPOUND} {{{Props.ID}: $id}})
            SET 
                c.{Props.NAME} = $name,
                c.{Props.CANONICAL_NAME} = $canonical_name,
                c.{Props.SMILES} = $smiles,
                c.{Props.MOLECULAR_FORMULA} = $molecular_formula,
                c.{Props.MOLECULAR_WEIGHT} = $molecular_weight,
                c.{Props.DESCRIPTION} = $description,
                c.{Props.PUBCHEM_ID} = $pubchem_id,
                c.{Props.CHEMBL_ID} = $chembl_id,
                c.{Props.COCONUT_ID} = $coconut_id,
                c.{Props.CREATED_AT} = datetime($created_at),
                c.{Props.LAST_UPDATED} = datetime($last_updated)
            """

            # Add synonyms as a property array
            compound_synonyms = synonyms_df[
                synonyms_df["compound_id"] == compound["id"]
            ]
            synonyms = [
                {"name": row["name"], "source": row["source"]}
                for _, row in compound_synonyms.iterrows()
            ]

            params = {
                "id": compound["id"],
                "name": compound["name"],
                "canonical_name": compound["canonical_name"],
                "smiles": compound["smiles"],
                "molecular_formula": compound["molecular_formula"],
                "molecular_weight": compound["molecular_weight"],
                "description": compound["description"],
                "pubchem_id": compound["pubchem_id"],
                "chembl_id": compound["chembl_id"],
                "coconut_id": compound["coconut_id"],
                "created_at": compound["created_at"].isoformat(),
                "last_updated": compound["last_updated"].isoformat(),
                "synonyms": synonyms,
            }

            session.run(cypher, params)


def migrate_sources(driver: Driver, sqlite_conn: sqlite3.Connection) -> None:
    """Migrate sources and their relationships from SQLite to Neo4j."""
    sources_df = pd.read_sql("SELECT * FROM sources", sqlite_conn)
    compound_sources_df = pd.read_sql("SELECT * FROM compound_sources", sqlite_conn)

    with driver.session() as session:
        for _, source in tqdm(sources_df.iterrows(), desc="Migrating sources"):
            # Create source node
            cypher = f"""
            MERGE (s:{Labels.SOURCE} {{{Props.ID}: $id}})
            SET 
                s.{Props.NAME} = $name,
                s.{Props.TYPE} = $type,
                s.{Props.DESCRIPTION} = $description,
                s.common_names = $common_names,
                s.native_regions = $native_regions,
                s.traditional_uses = $traditional_uses,
                s.taxonomy = $taxonomy,
                s.{Props.CREATED_AT} = datetime($created_at),
                s.{Props.LAST_UPDATED} = datetime($last_updated)
            """

            params = {
                "id": source["id"],
                "name": source["name"],
                "type": source["type"],
                "description": source["description"],
                "common_names": (
                    json.loads(source["common_names"]) if source["common_names"] else []
                ),
                "native_regions": (
                    json.loads(source["native_regions"])
                    if source["native_regions"]
                    else []
                ),
                "traditional_uses": (
                    json.loads(source["traditional_uses"])
                    if source["traditional_uses"]
                    else []
                ),
                "taxonomy": (
                    json.loads(source["taxonomy"]) if source["taxonomy"] else {}
                ),
                "created_at": source["created_at"].isoformat(),
                "last_updated": source["last_updated"].isoformat(),
            }

            session.run(cypher, params)

        # Create relationships between compounds and sources
        for _, rel in tqdm(
            compound_sources_df.iterrows(),
            desc="Creating compound-source relationships",
        ):
            cypher = f"""
            MATCH (c:{Labels.COMPOUND} {{{Props.ID}: $compound_id}})
            MATCH (s:{Labels.SOURCE} {{{Props.ID}: $source_id}})
            MERGE (c)-[r:{RelTypes.FOUND_IN}]->(s)
            SET r.{Props.CREATED_AT} = datetime($created_at)
            """

            params = {
                "compound_id": rel["compound_id"],
                "source_id": rel["source_id"],
                "created_at": rel["created_at"].isoformat(),
            }

            session.run(cypher, params)


def migrate_targets(driver: Driver, sqlite_conn: sqlite3.Connection) -> None:
    """Migrate targets and their relationships from SQLite to Neo4j."""
    targets_df = pd.read_sql("SELECT * FROM biological_targets", sqlite_conn)
    compound_targets_df = pd.read_sql("SELECT * FROM compound_targets", sqlite_conn)

    with driver.session() as session:
        for _, target in tqdm(targets_df.iterrows(), desc="Migrating targets"):
            # Create target node
            cypher = f"""
            MERGE (t:{Labels.TARGET} {{{Props.ID}: $id}})
            SET 
                t.{Props.NAME} = $name,
                t.standardized_name = $standardized_name,
                t.{Props.TYPE} = $type,
                t.{Props.DESCRIPTION} = $description,
                t.{Props.ORGANISM} = $organism,
                t.{Props.UNIPROT_ID} = $uniprot_id,
                t.{Props.CHEMBL_ID} = $chembl_id,
                t.{Props.GENE_ID} = $gene_id,
                t.gene_name = $gene_name,
                t.{Props.CREATED_AT} = datetime($created_at),
                t.{Props.LAST_UPDATED} = datetime($last_updated)
            """

            params = {
                "id": target["id"],
                "name": target["name"],
                "standardized_name": target["standardized_name"],
                "type": target["type"],
                "description": target["description"],
                "organism": target["organism"],
                "uniprot_id": target["uniprot_id"],
                "chembl_id": target["chembl_id"],
                "gene_id": target["gene_id"],
                "gene_name": target["gene_name"],
                "created_at": target["created_at"].isoformat(),
                "last_updated": target["last_updated"].isoformat(),
            }

            session.run(cypher, params)

        # Create relationships between compounds and targets
        for _, rel in tqdm(
            compound_targets_df.iterrows(),
            desc="Creating compound-target relationships",
        ):
            cypher = f"""
            MATCH (c:{Labels.COMPOUND} {{{Props.ID}: $compound_id}})
            MATCH (t:{Labels.TARGET} {{{Props.ID}: $target_id}})
            MERGE (c)-[r:{RelTypes.BINDS_TO}]->(t)
            SET 
                r.{Props.ACTION} = $action,
                r.{Props.ACTION_TYPE} = $action_type,
                r.{Props.ACTION_VALUE} = $action_value,
                r.{Props.EVIDENCE} = $evidence,
                r.{Props.EVIDENCE_URLS} = $evidence_urls,
                r.{Props.CREATED_AT} = datetime($created_at)
            """

            params = {
                "compound_id": rel["compound_id"],
                "target_id": rel["target_id"],
                "action": rel["action"],
                "action_type": rel["action_type"],
                "action_value": rel["action_value"],
                "evidence": rel["evidence"],
                "evidence_urls": rel["evidence_urls"],
                "created_at": rel["created_at"].isoformat(),
            }

            session.run(cypher, params)


@register_command("migrate_to_neo4j")
async def command_migrate_to_neo4j(args: List[str]) -> None:
    """Migrate data from SQLite to Neo4j."""
    parser = argparse.ArgumentParser(description="Migrate data from SQLite to Neo4j")
    parser.add_argument(
        "--sqlite-db", default="hyperblend.db", help="SQLite database file"
    )

    parsed_args = parser.parse_args(args)

    driver: Optional[Driver] = None
    try:
        # Connect to SQLite
        sqlite_conn = sqlite3.connect(parsed_args.sqlite_db)

        # Get Neo4j driver
        driver = get_driver()

        # Create constraints
        create_constraints(driver)

        # Migrate data
        migrate_compounds(driver, sqlite_conn)
        migrate_sources(driver, sqlite_conn)
        migrate_targets(driver, sqlite_conn)

        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise

    finally:
        if sqlite_conn:
            sqlite_conn.close()
        if driver:
            driver.close()
