"""Neo4j database configuration and connection management."""

import os
from typing import Dict, Any
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver, AsyncGraphDatabase, AsyncDriver

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


def get_driver() -> Driver:
    """Get a synchronous Neo4j driver instance."""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


async def get_async_driver() -> AsyncDriver:
    """Get an asynchronous Neo4j driver instance."""
    return AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


# Node labels
class Labels:
    COMPOUND = "Compound"
    SOURCE = "Source"
    TARGET = "Target"
    CHEMICAL_CLASS = "ChemicalClass"
    EFFECT = "Effect"


# Relationship types
class RelTypes:
    FOUND_IN = "FOUND_IN"
    BINDS_TO = "BINDS_TO"
    BELONGS_TO = "BELONGS_TO"
    SIMILAR_TO = "SIMILAR_TO"
    METABOLIZES_TO = "METABOLIZES_TO"
    INTERACTS_WITH = "INTERACTS_WITH"


# Property keys
class Props:
    ID = "id"
    NAME = "name"
    CANONICAL_NAME = "canonical_name"
    SMILES = "smiles"
    MOLECULAR_FORMULA = "molecular_formula"
    MOLECULAR_WEIGHT = "molecular_weight"
    DESCRIPTION = "description"
    TYPE = "type"
    ORGANISM = "organism"
    CREATED_AT = "created_at"
    LAST_UPDATED = "last_updated"

    # External IDs
    PUBCHEM_ID = "pubchem_id"
    CHEMBL_ID = "chembl_id"
    COCONUT_ID = "coconut_id"
    UNIPROT_ID = "uniprot_id"
    GENE_ID = "gene_id"

    # Relationship properties
    ACTION = "action"
    ACTION_TYPE = "action_type"
    ACTION_VALUE = "action_value"
    EVIDENCE = "evidence"
    EVIDENCE_URLS = "evidence_urls"
    SIMILARITY_SCORE = "similarity_score"
