"""Data verification and standardization commands."""

import argparse
import asyncio
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from hyperblend_old.config import settings
from hyperblend_old.infrastructure.repositories.models.base import Base
from hyperblend_old.infrastructure.repositories.models.compounds import Compound
from hyperblend_old.infrastructure.repositories.models.sources import Source
from hyperblend_old.infrastructure.repositories.models.targets import BiologicalTarget
from hyperblend_old.management import register_command

logger = logging.getLogger(__name__)


async def verify_sources():
    """Verify and clean up source data."""
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.begin() as conn:
            # Check for sources without compounds
            orphaned = await conn.execute(
                text(
                    """
                SELECT s.id, s.name 
                FROM sources s 
                LEFT JOIN compound_sources cs ON s.id = cs.source_id 
                WHERE cs.compound_id IS NULL
            """
                )
            )
            orphaned_sources = orphaned.fetchall()

            if orphaned_sources:
                logger.warning("Found orphaned sources:")
                for source in orphaned_sources:
                    logger.warning(f"  - {source.name} (ID: {source.id})")

            # Check for invalid taxonomies
            invalid = await conn.execute(
                text(
                    """
                SELECT id, name, taxonomy 
                FROM sources 
                WHERE taxonomy IS NOT NULL 
                AND taxonomy NOT LIKE '%kingdom%'
            """
                )
            )
            invalid_sources = invalid.fetchall()

            if invalid_sources:
                logger.warning("Found sources with invalid taxonomy:")
                for source in invalid_sources:
                    logger.warning(f"  - {source.name} (ID: {source.id})")

            logger.info("Source verification completed")
    finally:
        await engine.dispose()


async def verify_compounds():
    """Verify compound data integrity."""
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.begin() as conn:
            # Check for compounds without SMILES
            no_smiles = await conn.execute(
                text(
                    """
                SELECT id, name 
                FROM compounds 
                WHERE smiles IS NULL
            """
                )
            )
            compounds_no_smiles = no_smiles.fetchall()

            if compounds_no_smiles:
                logger.warning("Found compounds without SMILES:")
                for compound in compounds_no_smiles:
                    logger.warning(f"  - {compound.name} (ID: {compound.id})")

            # Check for compounds without sources
            orphaned = await conn.execute(
                text(
                    """
                SELECT c.id, c.name 
                FROM compounds c 
                LEFT JOIN compound_sources cs ON c.id = cs.compound_id 
                WHERE cs.source_id IS NULL
            """
                )
            )
            orphaned_compounds = orphaned.fetchall()

            if orphaned_compounds:
                logger.warning("Found compounds without sources:")
                for compound in orphaned_compounds:
                    logger.warning(f"  - {compound.name} (ID: {compound.id})")

            logger.info("Compound verification completed")
    finally:
        await engine.dispose()


async def verify_targets():
    """Verify and standardize target data."""
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.begin() as conn:
            # Check for targets without UniProt IDs
            no_uniprot = await conn.execute(
                text(
                    """
                SELECT id, name 
                FROM biological_targets 
                WHERE uniprot_id IS NULL
            """
                )
            )
            targets_no_uniprot = no_uniprot.fetchall()

            if targets_no_uniprot:
                logger.warning("Found targets without UniProt IDs:")
                for target in targets_no_uniprot:
                    logger.warning(f"  - {target.name} (ID: {target.id})")

            logger.info("Target verification completed")
    finally:
        await engine.dispose()


@register_command("verify")
async def command_verify(args):
    """Data verification command handler."""
    parser = argparse.ArgumentParser(description="Data verification commands")
    parser.add_argument(
        "type",
        choices=["sources", "compounds", "targets", "all"],
        help="Type of data to verify",
    )

    parsed_args = parser.parse_args(args)

    if parsed_args.type == "sources" or parsed_args.type == "all":
        await verify_sources()
    if parsed_args.type == "compounds" or parsed_args.type == "all":
        await verify_compounds()
    if parsed_args.type == "targets" or parsed_args.type == "all":
        await verify_targets()
