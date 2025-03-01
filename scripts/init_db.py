# scripts/init_db.py

"""Script to initialize the database."""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from hyperblend.config import get_settings
from hyperblend.infrastructure.repositories.sqlalchemy_models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Initialize the database."""
    settings = get_settings()

    # Create engine
    engine = create_async_engine(settings.DATABASE_URL, **settings.DATABASE_ARGS)

    async with engine.begin() as conn:
        # Drop all tables if they exist
        await conn.run_sync(Base.metadata.drop_all)

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        logger.info("Database tables created successfully")

    await engine.dispose()


def main() -> None:
    """Run the database initialization."""
    try:
        asyncio.run(init_db())
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


if __name__ == "__main__":
    main()
