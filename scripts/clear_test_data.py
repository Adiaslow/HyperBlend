# scripts/clear_test_data.py

"""Script to clear test data from the database."""

import asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from hyperblend.config import settings
from hyperblend.infrastructure.repositories.models.compounds import Compound
from hyperblend.infrastructure.repositories.models.sources import Source
from hyperblend.infrastructure.repositories.models.targets import BiologicalTarget
from hyperblend.infrastructure.repositories.models import (
    compound_sources,
    compound_targets,
)


async def clear_test_data():
    """Clear all test data from the database."""
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL, echo=True)

    # Create async session factory
    async_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        # Delete all relationships first
        await session.execute(delete(compound_sources))
        await session.execute(delete(compound_targets))

        # Delete all entries from each table
        await session.execute(delete(Compound))
        await session.execute(delete(Source))
        await session.execute(delete(BiologicalTarget))

        # Commit the changes
        await session.commit()

    # Close the engine
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(clear_test_data())
