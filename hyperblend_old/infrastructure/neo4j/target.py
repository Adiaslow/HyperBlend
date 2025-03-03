# hyperblend/infrastructure/neo4j/target.py

"""Neo4j target repository implementation."""

from typing import List, Optional, Dict, Any, cast
from neo4j import AsyncDriver, Query, Record, AsyncResult
from hyperblend_old.domain.models.target import Target, TargetType
from hyperblend_old.domain.repositories.target import TargetRepository
from hyperblend_old.core.exceptions import DatabaseError
from .base import BaseNeo4jRepository


class Neo4jTargetRepository(BaseNeo4jRepository[Target], TargetRepository):
    """Neo4j implementation of the target repository."""

    def __init__(self, driver: AsyncDriver):
        """Initialize the repository."""
        super().__init__(driver, "Target", Target)

    async def find_by_name(self, name: str) -> List[Target]:
        """Find targets by name."""
        query = Query(
            """
            MATCH (t:Target)
            WHERE t.name =~ $name_pattern OR t.gene_name =~ $name_pattern
            RETURN t
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query, {"name_pattern": f"(?i).*{name}.*"}
                )
                records = await result.values()
                return [
                    Target(**record[0])
                    for record in records
                    if record and isinstance(record[0], dict)
                ]
        except Exception as e:
            raise DatabaseError(f"Error finding targets by name: {str(e)}")

    async def find_by_type(self, target_type: TargetType) -> List[Target]:
        """Find targets by type."""
        query = Query(
            """
            MATCH (t:Target {type: $type})
            RETURN t
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query, {"type": target_type.value}
                )
                records = await result.values()
                return [
                    Target(**record[0])
                    for record in records
                    if record and isinstance(record[0], dict)
                ]
        except Exception as e:
            raise DatabaseError(f"Error finding targets by type: {str(e)}")

    async def find_by_external_id(
        self, id_type: str, id_value: str
    ) -> Optional[Target]:
        """Find a target by external ID."""
        query = Query(
            """
            MATCH (t:Target)
            WHERE t[$id_type] = $id_value
            RETURN t
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query,
                    {"id_type": id_type.lower() + "_id", "id_value": id_value},
                )
                record = await result.single()
                if record and record.get("t"):
                    return Target(**cast(Dict[str, Any], record.get("t")))
                return None
        except Exception as e:
            raise DatabaseError(f"Error finding target by external ID: {str(e)}")

    async def find_by_gene(self, gene_name: str) -> List[Target]:
        """Find targets by gene name."""
        query = Query(
            """
            MATCH (t:Target)
            WHERE t.gene_name =~ $gene_pattern
            RETURN t
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query, {"gene_pattern": f"(?i).*{gene_name}.*"}
                )
                records = await result.values()
                return [
                    Target(**record[0])
                    for record in records
                    if record and isinstance(record[0], dict)
                ]
        except Exception as e:
            raise DatabaseError(f"Error finding targets by gene name: {str(e)}")

    async def find_by_organism(self, organism: str) -> List[Target]:
        """Find targets by organism."""
        query = Query(
            """
            MATCH (t:Target {organism: $organism})
            RETURN t
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(query, {"organism": organism})
                records = await result.values()
                return [
                    Target(**record[0])
                    for record in records
                    if record and isinstance(record[0], dict)
                ]
        except Exception as e:
            raise DatabaseError(f"Error finding targets by organism: {str(e)}")

    async def get_compounds(self, target_id: str) -> List[str]:
        """Get IDs of compounds that interact with this target."""
        query = Query(
            """
            MATCH (t:Target {id: $target_id})<-[r:INTERACTS_WITH]-(c:Compound)
            RETURN c.id as compound_id
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(query, {"target_id": target_id})
                records = await result.values()
                return [
                    str(record[0])
                    for record in records
                    if record and isinstance(record[0], str)
                ]
        except Exception as e:
            raise DatabaseError(f"Error getting compounds for target: {str(e)}")

    async def add_compound_interaction(
        self,
        target_id: str,
        compound_id: str,
        action: str,
        action_type: Optional[str] = None,
        action_value: Optional[float] = None,
    ) -> bool:
        """Add a compound interaction to a target."""
        query = Query(
            """
            MATCH (t:Target {id: $target_id})
            MATCH (c:Compound {id: $compound_id})
            MERGE (c)-[r:INTERACTS_WITH {
                action: $action,
                action_type: $action_type,
                action_value: $action_value
            }]->(t)
            RETURN count(r) as count
            """
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query,
                    {
                        "target_id": target_id,
                        "compound_id": compound_id,
                        "action": action,
                        "action_type": action_type,
                        "action_value": action_value,
                    },
                )
                record = await result.single()
                return bool(record and record.get("count", 0) > 0)
        except Exception as e:
            raise DatabaseError(f"Error adding compound interaction: {str(e)}")
