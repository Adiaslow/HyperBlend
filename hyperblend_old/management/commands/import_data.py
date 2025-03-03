"""Data import and update commands."""

import argparse
import asyncio
import logging
import uuid
from typing import Optional
import aiohttp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from hyperblend_old.config import settings
from hyperblend_old.infrastructure.repositories.models.base import Base
from hyperblend_old.infrastructure.repositories.models.compounds import Compound
from hyperblend_old.infrastructure.repositories.models.sources import Source
from hyperblend_old.infrastructure.repositories.models.targets import BiologicalTarget
from hyperblend_old.management import register_command

logger = logging.getLogger(__name__)


def generate_id(prefix: str) -> str:
    """Generate a unique ID with a prefix."""
    return f"{prefix}_{str(uuid.uuid4())}"


async def import_plant_data(plant_name: str, source_type: str):
    """Import data for a specific plant."""
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.begin() as conn:
            # Create or get source
            result = await conn.execute(
                text("SELECT * FROM sources WHERE name = :name"), {"name": plant_name}
            )
            source = result.fetchone()

            if not source:
                source_id = generate_id("SRC")
                await conn.execute(
                    text(
                        """
                        INSERT INTO sources (id, name, type) 
                        VALUES (:id, :name, :type)
                    """
                    ),
                    {"id": source_id, "name": plant_name, "type": source_type},
                )
                logger.info(f"Created new source: {plant_name} (ID: {source_id})")
            else:
                logger.info(f"Found existing source: {plant_name}")

            # TODO: Add specific plant data import logic
            logger.info(f"Imported data for {plant_name}")
    finally:
        await engine.dispose()


async def update_compound_targets(compound_id: Optional[int] = None):
    """Update compound-target associations."""
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.begin() as conn:
            if compound_id:
                # Update specific compound
                result = await conn.execute(
                    text("SELECT * FROM compounds WHERE id = :id"), {"id": compound_id}
                )
                compound = result.fetchone()
                if not compound:
                    logger.error(f"Compound not found: {compound_id}")
                    return

                # TODO: Add target update logic for specific compound
                logger.info(f"Updated targets for compound {compound.name}")
            else:
                # Update all compounds
                result = await conn.execute(text("SELECT * FROM compounds"))
                compounds = result.fetchall()

                for compound in compounds:
                    # TODO: Add target update logic for each compound
                    logger.info(f"Updated targets for compound {compound.name}")
    finally:
        await engine.dispose()


async def fetch_pubchem_data(compound_id: Optional[int] = None):
    """Fetch compound data from PubChem."""
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.begin() as conn:
            if compound_id:
                # Fetch data for specific compound
                result = await conn.execute(
                    text("SELECT * FROM compounds WHERE id = :id"), {"id": compound_id}
                )
                compound = result.fetchone()
                if not compound:
                    logger.error(f"Compound not found: {compound_id}")
                    return

                # TODO: Add PubChem data fetch logic for specific compound
                logger.info(f"Fetched PubChem data for compound {compound.name}")
            else:
                # Fetch data for all compounds
                result = await conn.execute(text("SELECT * FROM compounds"))
                compounds = result.fetchall()

                for compound in compounds:
                    # TODO: Add PubChem data fetch logic for each compound
                    logger.info(f"Fetched PubChem data for compound {compound.name}")
    finally:
        await engine.dispose()


@register_command("import")
async def command_import(args):
    """Data import command handler."""
    parser = argparse.ArgumentParser(description="Data import commands")
    subparsers = parser.add_subparsers(dest="action", help="Action to perform")

    # Plant data import
    plant_parser = subparsers.add_parser("plant", help="Import plant data")
    plant_parser.add_argument("name", help="Plant name")
    plant_parser.add_argument("--type", default="plant", help="Source type")

    # Target update
    target_parser = subparsers.add_parser("targets", help="Update compound targets")
    target_parser.add_argument("--compound-id", type=int, help="Specific compound ID")

    # PubChem data
    pubchem_parser = subparsers.add_parser("pubchem", help="Fetch PubChem data")
    pubchem_parser.add_argument("--compound-id", type=int, help="Specific compound ID")

    parsed_args = parser.parse_args(args)

    if parsed_args.action == "plant":
        await import_plant_data(parsed_args.name, parsed_args.type)
    elif parsed_args.action == "targets":
        await update_compound_targets(parsed_args.compound_id)
    elif parsed_args.action == "pubchem":
        await fetch_pubchem_data(parsed_args.compound_id)
