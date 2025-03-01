# scripts/verify_sources.py
"""Script to verify compound-source relationships in the database."""

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from hyperblend.config import settings
from hyperblend.infrastructure.repositories.models.compounds import Compound
from hyperblend.infrastructure.repositories.models.sources import Source
from hyperblend.infrastructure.repositories.models import compound_sources

# Database configuration
engine = create_async_engine(settings.DATABASE_URL, echo=True)
SessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def verify_relationships():
    """Verify all compound-source relationships in the database."""
    async with SessionLocal() as session:
        # Query to get all compound-source relationships
        query = (
            select(
                Compound.name.label("compound_name"), Source.name.label("source_name")
            )
            .join(compound_sources, Compound.id == compound_sources.c.compound_id)
            .join(Source, Source.id == compound_sources.c.source_id)
        )

        result = await session.execute(query)
        relationships = result.all()

        print("\nCompound-Source Relationships:")
        print("-----------------------------")
        for rel in relationships:
            print(f"Compound: {rel.compound_name} -> Source: {rel.source_name}")

        print(f"\nTotal relationships found: {len(relationships)}")


async def main():
    """Main function to run the verification."""
    await verify_relationships()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
