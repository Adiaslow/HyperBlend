# hyperblend/infrastructure/neo4j/source.py

"""Neo4j source repository implementation."""

from typing import List, Optional, Dict, Any, cast
from neo4j import AsyncDriver, Query, Record, AsyncResult
from hyperblend_old.domain.models.source import Source, SourceType
from hyperblend_old.domain.repositories.source import SourceRepository
from hyperblend_old.core.exceptions import DatabaseError
from .base import BaseNeo4jRepository


class Neo4jSourceRepository(BaseNeo4jRepository[Source], SourceRepository):
    """Neo4j implementation of the source repository."""

    def __init__(self, driver: AsyncDriver):
        """Initialize the repository."""
        super().__init__(driver, "Source", Source)

    async def find_by_name(self, name: str) -> List[Source]:
        """Find sources by name or common name."""
        query = Query(
            """
            MATCH (s:Source)
            WHERE s.name =~ $name_pattern
            OR any(common_name in s.common_names WHERE common_name =~ $name_pattern)
            RETURN s
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query, {"name_pattern": f"(?i).*{name}.*"}
                )
                records = await result.values()
                return [
                    Source(**record[0])
                    for record in records
                    if record and isinstance(record[0], dict)
                ]
        except Exception as e:
            raise DatabaseError(f"Error finding sources by name: {str(e)}")

    async def find_by_type(self, source_type: SourceType) -> List[Source]:
        """Find sources by type."""
        query = Query(
            """
            MATCH (s:Source {type: $type})
            RETURN s
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query, {"type": source_type.value}
                )
                records = await result.values()
                return [
                    Source(**record[0])
                    for record in records
                    if record and isinstance(record[0], dict)
                ]
        except Exception as e:
            raise DatabaseError(f"Error finding sources by type: {str(e)}")

    async def find_by_region(self, region: str) -> List[Source]:
        """Find sources by native region."""
        query = Query(
            """
            MATCH (s:Source)
            WHERE any(r in s.native_regions WHERE r =~ $region_pattern)
            RETURN s
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query, {"region_pattern": f"(?i).*{region}.*"}
                )
                records = await result.values()
                return [
                    Source(**record[0])
                    for record in records
                    if record and isinstance(record[0], dict)
                ]
        except Exception as e:
            raise DatabaseError(f"Error finding sources by region: {str(e)}")

    async def find_by_traditional_use(self, use: str) -> List[Source]:
        """Find sources by traditional use."""
        query = Query(
            """
            MATCH (s:Source)
            WHERE any(u in s.traditional_uses WHERE u =~ $use_pattern)
            RETURN s
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query, {"use_pattern": f"(?i).*{use}.*"}
                )
                records = await result.values()
                return [
                    Source(**record[0])
                    for record in records
                    if record and isinstance(record[0], dict)
                ]
        except Exception as e:
            raise DatabaseError(f"Error finding sources by traditional use: {str(e)}")

    async def find_by_taxonomy(self, rank: str, value: str) -> List[Source]:
        """Find sources by taxonomic classification."""
        query = Query(
            """
            MATCH (s:Source)
            WHERE s[$rank] =~ $value_pattern
            RETURN s
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query,
                    {"rank": rank.lower(), "value_pattern": f"(?i).*{value}.*"},
                )
                records = await result.values()
                return [
                    Source(**record[0])
                    for record in records
                    if record and isinstance(record[0], dict)
                ]
        except Exception as e:
            raise DatabaseError(f"Error finding sources by taxonomy: {str(e)}")

    async def get_compounds(self, source_id: str) -> List[str]:
        """Get IDs of compounds found in this source."""
        query = Query(
            """
            MATCH (c:Compound)-[r:FOUND_IN]->(s:Source {id: $source_id})
            RETURN c.id as compound_id
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(query, {"source_id": source_id})
                records = await result.values()
                return [
                    str(record[0])
                    for record in records
                    if record and isinstance(record[0], str)
                ]
        except Exception as e:
            raise DatabaseError(f"Error getting compounds for source: {str(e)}")

    async def add_compound(self, source_id: str, compound_id: str) -> bool:
        """Add a compound to a source."""
        query = Query(
            """
            MATCH (c:Compound {id: $compound_id})
            MATCH (s:Source {id: $source_id})
            MERGE (c)-[r:FOUND_IN]->(s)
            RETURN count(r) as count
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query,
                    {"compound_id": compound_id, "source_id": source_id},
                )
                record = await result.single()
                return bool(record and record.get("count", 0) > 0)
        except Exception as e:
            raise DatabaseError(f"Error adding compound to source: {str(e)}")

    async def update_taxonomy(self, source_id: str, taxonomy: Dict[str, str]) -> bool:
        """Update the taxonomic classification of a source."""
        query = Query(
            """
            MATCH (s:Source {id: $source_id})
            SET s += $taxonomy
            RETURN s
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query,
                    {"source_id": source_id, "taxonomy": taxonomy},
                )
                record = await result.single()
                return bool(record and record.get("s"))
        except Exception as e:
            raise DatabaseError(f"Error updating taxonomy: {str(e)}")
