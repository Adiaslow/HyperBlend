import json
from typing import List, Optional, Dict, Any
from neo4j import AsyncDriver, AsyncSession

from ..domain.models import Compound, Source, Target, SourceType, TargetType
from ..domain.repositories import (
    CompoundRepository,
    SourceRepository,
    TargetRepository,
)
from ..core.exceptions import DatabaseError


class Neo4jSourceRepository(SourceRepository):
    """Neo4j implementation of the source repository."""

    def __init__(self, driver: AsyncDriver):
        """Initialize the repository."""
        self._driver = driver

    async def create(self, entity: Source) -> Source:
        """Create a new source."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                CREATE (s:Source)
                SET s = $props
                RETURN s
                """,
                props=entity.to_neo4j_dict(),
            )
            record = await result.single()
            if record and record.get("s"):
                return Source.from_neo4j_dict(dict(record["s"]))
            raise DatabaseError("Failed to create Source")

    async def get(self, id: str) -> Optional[Source]:
        """Get a source by ID."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Source {id: $id})
                RETURN s
                """,
                id=id,
            )
            record = await result.single()
            if not record:
                return None
            return Source.from_neo4j_dict(dict(record["s"]))

    async def get_all(self) -> List[Source]:
        """Get all sources."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Source)
                RETURN s
                """
            )
            sources = []
            async for record in result:
                sources.append(Source.from_neo4j_dict(dict(record["s"])))
            return sources

    async def find_by_name(self, name: str) -> List[Source]:
        """Find sources by name or common name."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Source)
                WHERE s.name =~ $name_pattern
                OR any(common_name in s.common_names WHERE common_name =~ $name_pattern)
                RETURN s
                """,
                name_pattern=f"(?i).*{name}.*",
            )
            return [
                Source.from_neo4j_dict(dict(record["s"])) async for record in result
            ]

    async def find_by_type(self, source_type: SourceType) -> List[Source]:
        """Find sources by type."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Source {type: $type})
                RETURN s
                """,
                type=source_type.value,
            )
            return [
                Source.from_neo4j_dict(dict(record["s"])) async for record in result
            ]

    async def find_by_region(self, region: str) -> List[Source]:
        """Find sources by native region."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Source)
                WHERE any(r in s.native_regions WHERE r =~ $region_pattern)
                RETURN s
                """,
                region_pattern=f"(?i).*{region}.*",
            )
            return [
                Source.from_neo4j_dict(dict(record["s"])) async for record in result
            ]

    async def find_by_traditional_use(self, use: str) -> List[Source]:
        """Find sources by traditional use."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Source)
                WHERE any(u in s.traditional_uses WHERE u =~ $use_pattern)
                RETURN s
                """,
                use_pattern=f"(?i).*{use}.*",
            )
            return [
                Source.from_neo4j_dict(dict(record["s"])) async for record in result
            ]

    async def find_by_taxonomy(self, rank: str, value: str) -> List[Source]:
        """Find sources by taxonomic classification."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Source)
                WHERE s[$rank] =~ $value_pattern
                RETURN s
                """,
                rank=rank.lower(),
                value_pattern=f"(?i).*{value}.*",
            )
            return [
                Source.from_neo4j_dict(dict(record["s"])) async for record in result
            ]

    async def get_compounds(self, source_id: str) -> List[str]:
        """Get IDs of compounds found in this source."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Compound)-[r:FOUND_IN]->(s:Source {id: $source_id})
                RETURN c.id as compound_id
                """,
                source_id=source_id,
            )
            return [str(record["compound_id"]) async for record in result]

    async def add_compound(self, source_id: str, compound_id: str) -> bool:
        """Add a compound to a source."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Compound {id: $compound_id})
                MATCH (s:Source {id: $source_id})
                MERGE (c)-[r:FOUND_IN]->(s)
                RETURN count(r) as count
                """,
                compound_id=compound_id,
                source_id=source_id,
            )
            record = await result.single()
            return bool(record and record.get("count", 0) > 0)

    async def update_taxonomy(self, source_id: str, taxonomy: Dict[str, str]) -> bool:
        """Update the taxonomic classification of a source."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Source {id: $source_id})
                SET s += $taxonomy
                RETURN s
                """,
                source_id=source_id,
                taxonomy=taxonomy,
            )
            record = await result.single()
            return bool(record and record.get("s"))
