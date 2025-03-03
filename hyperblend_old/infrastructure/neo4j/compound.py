"""Neo4j compound repository implementation."""

from typing import List, Optional, Dict, Any, cast
from neo4j import AsyncDriver, Query, Record, AsyncResult
from hyperblend_old.domain.models.compound import Compound
from hyperblend_old.domain.repositories.compound import CompoundRepository
from hyperblend_old.core.exceptions import DatabaseError
from .base import BaseNeo4jRepository


class Neo4jCompoundRepository(BaseNeo4jRepository[Compound], CompoundRepository):
    """Neo4j implementation of the compound repository."""

    def __init__(self, driver: AsyncDriver):
        """Initialize the repository."""
        super().__init__(driver, "Compound", Compound)

    async def get_all(self) -> List[Compound]:
        """Get all compounds."""
        query = Query(
            """
            MATCH (c:Compound)
            RETURN c
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(query)
                records = await result.values()
                return [
                    Compound(**record[0])
                    for record in records
                    if record and isinstance(record[0], dict)
                ]
        except Exception as e:
            raise DatabaseError(f"Error getting all compounds: {str(e)}")

    async def find_by_name(self, name: str) -> List[Compound]:
        """Find compounds by name or synonym."""
        query = Query(
            """
            MATCH (c:Compound)
            WHERE c.name =~ $name_pattern OR c.canonical_name =~ $name_pattern
            OR EXISTS {
                MATCH (c)-[:HAS_SYNONYM]->(s:Synonym)
                WHERE s.name =~ $name_pattern
            }
            RETURN c
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query, {"name_pattern": f"(?i).*{name}.*"}
                )
                records = await result.values()
                return [
                    Compound(**record[0])
                    for record in records
                    if record and isinstance(record[0], dict)
                ]
        except Exception as e:
            raise DatabaseError(f"Error finding compounds by name: {str(e)}")

    async def find_by_smiles(self, smiles: str) -> Optional[Compound]:
        """Find a compound by SMILES string."""
        query = Query(
            """
            MATCH (c:Compound {smiles: $smiles})
            RETURN c
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(query, {"smiles": smiles})
                record = await result.single()
                if record and record.get("c"):
                    return Compound(**cast(Dict[str, Any], record.get("c")))
                return None
        except Exception as e:
            raise DatabaseError(f"Error finding compound by SMILES: {str(e)}")

    async def find_by_external_id(
        self, id_type: str, id_value: str
    ) -> Optional[Compound]:
        """Find a compound by external ID."""
        query = Query(
            """
            MATCH (c:Compound)
            WHERE c[$id_type] = $id_value
            RETURN c
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query,
                    {"id_type": id_type.lower() + "_id", "id_value": id_value},
                )
                record = await result.single()
                if record and record.get("c"):
                    return Compound(**cast(Dict[str, Any], record.get("c")))
                return None
        except Exception as e:
            raise DatabaseError(f"Error finding compound by external ID: {str(e)}")

    async def find_similar(self, smiles: str, threshold: float = 0.8) -> List[Compound]:
        """Find compounds similar to the given SMILES string."""
        query = Query(
            """
            CALL db.index.fulltext.queryNodes("compound_smiles", $smiles)
            YIELD node, score
            WHERE score >= $threshold
            RETURN node as c
            ORDER BY score DESC
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query, {"smiles": smiles, "threshold": threshold}
                )
                records = await result.values()
                return [
                    Compound(**record[0])
                    for record in records
                    if record and isinstance(record[0], dict)
                ]
        except Exception as e:
            raise DatabaseError(f"Error finding similar compounds: {str(e)}")

    async def add_synonym(self, compound_id: str, name: str, source: str) -> bool:
        """Add a synonym to a compound."""
        query = Query(
            """
            MATCH (c:Compound {id: $compound_id})
            MERGE (s:Synonym {name: $name, source: $source})
            MERGE (c)-[r:HAS_SYNONYM]->(s)
            RETURN count(r) as count
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query,
                    {"compound_id": compound_id, "name": name, "source": source},
                )
                record = await result.single()
                return bool(record and record.get("count", 0) > 0)
        except Exception as e:
            raise DatabaseError(f"Error adding synonym: {str(e)}")

    async def get_synonyms(self, compound_id: str) -> List[str]:
        """Get all synonyms for a compound."""
        query = Query(
            """
            MATCH (c:Compound {id: $compound_id})-[:HAS_SYNONYM]->(s:Synonym)
            RETURN s.name as name
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query, {"compound_id": compound_id}
                )
                records = await result.values()
                return [
                    str(record[0])
                    for record in records
                    if record and isinstance(record[0], str)
                ]
        except Exception as e:
            raise DatabaseError(f"Error getting synonyms: {str(e)}")

    async def get_targets(self, compound_id: str) -> List[str]:
        """Get IDs of targets that interact with a compound."""
        query = Query(
            """
            MATCH (c:Compound {id: $compound_id})-[:INTERACTS_WITH]->(t:Target)
            RETURN t.id as id
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query, {"compound_id": compound_id}
                )
                records = await result.values()
                return [
                    str(record[0])
                    for record in records
                    if record and isinstance(record[0], str)
                ]
        except Exception as e:
            raise DatabaseError(f"Error getting target IDs: {str(e)}")

    async def get_sources(self, compound_id: str) -> List[str]:
        """Get IDs of sources that contain a compound."""
        query = Query(
            """
            MATCH (c:Compound {id: $compound_id})-[:FOUND_IN]->(s:Source)
            RETURN s.id as id
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query, {"compound_id": compound_id}
                )
                records = await result.values()
                return [
                    str(record[0])
                    for record in records
                    if record and isinstance(record[0], str)
                ]
        except Exception as e:
            raise DatabaseError(f"Error getting source IDs: {str(e)}")
