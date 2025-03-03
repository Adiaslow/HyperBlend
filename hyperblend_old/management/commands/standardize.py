"""Data standardization commands."""

import argparse
import asyncio
import logging
import re
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from hyperblend_old.config import settings
from hyperblend_old.infrastructure.repositories.models.base import Base
from hyperblend_old.infrastructure.repositories.models.compounds import Compound
from hyperblend_old.infrastructure.repositories.models.sources import Source
from hyperblend_old.infrastructure.repositories.models.targets import BiologicalTarget
from hyperblend_old.management import register_command

logger = logging.getLogger(__name__)

# Regex patterns for standardization
COMPOUND_NAME_PATTERN = r"[^a-zA-Z0-9-]+"
WHITESPACE_PATTERN = r"\s+"


async def standardize_compound_names():
    """Standardize compound names."""
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.begin() as conn:
            # Standardize chemical names
            await conn.execute(
                text(
                    """
                UPDATE compounds 
                SET name = LOWER(TRIM(name))
                WHERE name != LOWER(TRIM(name))
            """
                )
            )

            logger.info("Compound names standardized")
    finally:
        await engine.dispose()


async def standardize_target_names():
    """Standardize target names and data."""
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.begin() as conn:
            # Basic target name standardization
            await conn.execute(
                text(
                    """
                    UPDATE biological_targets 
                    SET standardized_name = LOWER(TRIM(name))
                    WHERE standardized_name IS NULL
                    OR standardized_name != LOWER(TRIM(name))
                """
                )
            )

            # Standardize gene names to uppercase
            await conn.execute(
                text(
                    """
                UPDATE biological_targets 
                SET gene_name = UPPER(TRIM(gene_name))
                WHERE gene_name IS NOT NULL 
                AND gene_name != UPPER(TRIM(gene_name))
            """
                )
            )

            logger.info("Target names standardized")
    finally:
        await engine.dispose()


async def standardize_source_names():
    """Standardize source names and taxonomies."""
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.begin() as conn:
            # Standardize source names (capitalize first letter of each word)
            await conn.execute(
                text(
                    """
                UPDATE sources 
                SET name = TRIM(name)
                WHERE name != TRIM(name)
            """
                )
            )

            # Standardize taxonomy format (if it's JSON, we don't need to modify it)
            logger.info("Source names standardized")
    finally:
        await engine.dispose()


async def standardize_smiles():
    """Standardize SMILES strings."""
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.begin() as conn:
            # Remove whitespace from SMILES strings
            await conn.execute(
                text(
                    """
                UPDATE compounds 
                SET smiles = TRIM(smiles)
                WHERE smiles IS NOT NULL 
                AND smiles != TRIM(smiles)
            """
                )
            )

            logger.info("SMILES strings standardized")
    finally:
        await engine.dispose()


@register_command("standardize")
async def command_standardize(args):
    """Data standardization command handler."""
    parser = argparse.ArgumentParser(description="Data standardization commands")
    parser.add_argument(
        "type",
        choices=["compounds", "targets", "sources", "smiles", "all"],
        help="Type of data to standardize",
    )

    parsed_args = parser.parse_args(args)

    if parsed_args.type == "compounds" or parsed_args.type == "all":
        await standardize_compound_names()
    if parsed_args.type == "targets" or parsed_args.type == "all":
        await standardize_target_names()
    if parsed_args.type == "sources" or parsed_args.type == "all":
        await standardize_source_names()
    if parsed_args.type == "smiles" or parsed_args.type == "all":
        await standardize_smiles()
