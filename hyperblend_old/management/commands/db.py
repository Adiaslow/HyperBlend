"""Database management commands."""

import argparse
import asyncio
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from hyperblend_old.config import settings
from hyperblend_old.infrastructure.repositories.models.base import Base
from hyperblend_old.management import register_command

logger = logging.getLogger(__name__)


async def init_database():
    """Initialize the database schema."""
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database schema initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise
    finally:
        await engine.dispose()


async def clear_test_data():
    """Clear test data from the database."""
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.begin() as conn:
            # Delete test data from junction tables first
            await conn.execute(text("DELETE FROM compound_targets"))
            await conn.execute(text("DELETE FROM compound_sources"))

            # Delete test data from main tables
            await conn.execute(
                text(
                    """
                DELETE FROM biological_targets 
                WHERE name LIKE 'TEST_%'
            """
                )
            )
            await conn.execute(
                text(
                    """
                DELETE FROM sources 
                WHERE name LIKE 'TEST_%'
            """
                )
            )
            await conn.execute(
                text(
                    """
                DELETE FROM compounds 
                WHERE name LIKE 'TEST_%'
            """
                )
            )

            logger.info("Test data cleared successfully")
    except Exception as e:
        logger.error(f"Error clearing test data: {str(e)}")
        raise
    finally:
        await engine.dispose()


async def cleanup_non_human_targets():
    """Remove non-human targets from the database."""
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.begin() as conn:
            # Delete compound associations first
            await conn.execute(
                text(
                    """
                DELETE FROM compound_targets 
                WHERE target_id IN (
                    SELECT id FROM biological_targets 
                    WHERE organism != 'Homo sapiens'
                )
            """
                )
            )

            # Then delete the targets
            await conn.execute(
                text(
                    """
                DELETE FROM biological_targets 
                WHERE organism != 'Homo sapiens'
            """
                )
            )

            logger.info("Non-human targets cleaned up successfully")
    except Exception as e:
        logger.error(f"Error cleaning up non-human targets: {str(e)}")
        raise
    finally:
        await engine.dispose()


@register_command("db")
async def command_db(args):
    """Database management command handler."""
    parser = argparse.ArgumentParser(description="Database management commands")
    parser.add_argument(
        "action",
        choices=["init", "clear-test", "cleanup-targets"],
        help="Action to perform",
    )

    parsed_args = parser.parse_args(args)

    if parsed_args.action == "init":
        await init_database()
    elif parsed_args.action == "clear-test":
        await clear_test_data()
    elif parsed_args.action == "cleanup-targets":
        await cleanup_non_human_targets()
