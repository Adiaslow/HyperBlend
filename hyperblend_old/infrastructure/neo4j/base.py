# hyperblend/infrastructure/neo4j/base.py

"""Base Neo4j repository implementation."""

from typing import TypeVar, Generic, List, Optional, Dict, Any, cast, Type, Protocol
from typing_extensions import LiteralString
from neo4j import AsyncDriver, Query, Record, AsyncResult
from pydantic import BaseModel
from hyperblend_old.domain.repositories.base import BaseRepository
from hyperblend_old.core.exceptions import DatabaseError

T = TypeVar("T", bound=BaseModel)


class BaseNeo4jRepository(BaseRepository[T], Generic[T]):
    """Base Neo4j repository implementation."""

    def __init__(self, driver: AsyncDriver, label: str, model_class: Type[T]):
        """Initialize the repository.

        Args:
            driver: Neo4j driver instance
            label: Node label in Neo4j
            model_class: Model class to instantiate from records
        """
        self._driver = driver
        self._label = label
        self._model_class = model_class

    def _build_query(self, query: LiteralString) -> Query:
        """Build a Neo4j query with the label."""
        return Query(cast(LiteralString, query.replace("$LABEL", self._label)))

    async def get(self, id: str) -> Optional[T]:
        """Retrieve an entity by ID."""
        query = self._build_query(
            cast(
                LiteralString,
                """
                MATCH (n:$LABEL {id: $id})
                RETURN properties(n) as props
                """,
            )
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(query, {"id": id})
                record = await result.single()
                if record and record.get("props"):
                    return self._model_class.from_neo4j_dict(
                        cast(Dict[str, Any], record.get("props"))
                    )
                return None
        except Exception as e:
            raise DatabaseError(f"Error retrieving {self._label}: {str(e)}")

    async def get_all(self) -> List[T]:
        """Retrieve all entities."""
        query = self._build_query(
            cast(
                LiteralString,
                """
                MATCH (n:$LABEL)
                RETURN properties(n) as props
                """,
            )
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(query)
                records = await result.values()
                return [
                    self._model_class.from_neo4j_dict(record[0])
                    for record in records
                    if record and isinstance(record[0], dict)
                ]
        except Exception as e:
            raise DatabaseError(f"Error retrieving all {self._label}s: {str(e)}")

    async def create(self, entity: T) -> T:
        """Create a new entity."""
        query = self._build_query(
            cast(
                LiteralString,
                """
                CREATE (n:$LABEL)
                SET n = $props
                RETURN properties(n) as props
                """,
            )
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(
                    query,
                    {
                        "props": entity.to_neo4j_dict(),
                    },
                )
                record = await result.single()
                if record and record.get("props"):
                    return self._model_class.from_neo4j_dict(
                        cast(Dict[str, Any], record.get("props"))
                    )
                raise DatabaseError(f"Failed to create {self._label}")
        except Exception as e:
            raise DatabaseError(f"Error creating {self._label}: {str(e)}")

    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        query = self._build_query(
            cast(
                LiteralString,
                """
                MATCH (n:$LABEL {id: $id})
                SET n = $props
                RETURN properties(n) as props
                """,
            )
        )
        try:
            async with self._driver.session() as session:
                neo4j_data = entity.to_neo4j_dict()
                result: AsyncResult = await session.run(
                    query,
                    {
                        "id": neo4j_data.get("id"),
                        "props": neo4j_data,
                    },
                )
                record = await result.single()
                if record and record.get("props"):
                    return self._model_class.from_neo4j_dict(
                        cast(Dict[str, Any], record.get("props"))
                    )
                raise DatabaseError(f"Failed to update {self._label}")
        except Exception as e:
            raise DatabaseError(f"Error updating {self._label}: {str(e)}")

    async def delete(self, id: str) -> bool:
        """Delete an entity by ID."""
        query = self._build_query(
            cast(
                LiteralString,
                """
                MATCH (n:$LABEL {id: $id})
                DELETE n
                RETURN count(n) as count
                """,
            )
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(query, {"id": id})
                record = await result.single()
                return bool(record and record.get("count", 0) > 0)
        except Exception as e:
            raise DatabaseError(f"Error deleting {self._label}: {str(e)}")

    async def find_by(self, **kwargs: Any) -> List[T]:
        """Find entities by attributes."""
        conditions = []
        for key in kwargs:
            conditions.append(f"n.{key} = ${key}")
        query = self._build_query(
            cast(
                LiteralString,
                f"""
                MATCH (n:$LABEL)
                WHERE {" AND ".join(conditions)}
                RETURN properties(n) as props
                """,
            )
        )
        try:
            async with self._driver.session() as session:
                result: AsyncResult = await session.run(query, kwargs)
                records = await result.values()
                return [
                    self._model_class.from_neo4j_dict(record[0])
                    for record in records
                    if record and isinstance(record[0], dict)
                ]
        except Exception as e:
            raise DatabaseError(f"Error finding {self._label}s: {str(e)}")

    @staticmethod
    def _format_properties(props: Dict[str, Any]) -> Dict[str, Any]:
        """Format properties for Neo4j query."""
        return {k: v for k, v in props.items() if v is not None}
