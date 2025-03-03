# hyperblend/app/db/repository.py

from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from pydantic import BaseModel
from .neo4j import db

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    """Base repository class for database operations."""

    def __init__(self, model: Type[T]):
        """Initialize the repository with a model class."""
        self.model = model
        self._collection_name = model.__name__.lower()

    def create(self, entity: T) -> T:
        """Create a new entity in the database."""
        with db.session() as session:
            query = f"""
            CREATE (n:{self._collection_name} $properties)
            RETURN n
            """
            result = session.run(query, properties=entity.model_dump())
            return self.model(**dict(result.single()["n"]))

    def get_by_id(self, id: str) -> Optional[T]:
        """Retrieve an entity by its ID."""
        with db.session() as session:
            query = f"""
            MATCH (n:{self._collection_name} {{id: $id}})
            RETURN n
            """
            result = session.run(query, id=id)
            record = result.single()
            return self.model(**dict(record["n"])) if record else None

    def update(self, id: str, entity: T) -> Optional[T]:
        """Update an existing entity."""
        with db.session() as session:
            query = f"""
            MATCH (n:{self._collection_name} {{id: $id}})
            SET n += $properties
            RETURN n
            """
            result = session.run(query, id=id, properties=entity.model_dump())
            record = result.single()
            return self.model(**dict(record["n"])) if record else None

    def delete(self, id: str) -> bool:
        """Delete an entity by its ID."""
        with db.session() as session:
            query = f"""
            MATCH (n:{self._collection_name} {{id: $id}})
            DELETE n
            """
            result = session.run(query, id=id)
            return result.consume().counters.nodes_deleted > 0

    def find_all(self) -> List[T]:
        """Retrieve all entities of this type."""
        with db.session() as session:
            query = f"""
            MATCH (n:{self._collection_name})
            RETURN n
            """
            result = session.run(query)
            return [self.model(**dict(record["n"])) for record in result]

    def find_by_property(self, property_name: str, value: Any) -> List[T]:
        """Find entities by a specific property value."""
        with db.session() as session:
            query = f"""
            MATCH (n:{self._collection_name} {{{property_name}: $value}})
            RETURN n
            """
            result = session.run(query, value=value)
            return [self.model(**dict(record["n"])) for record in result]

    def create_relationship(
        self,
        from_id: str,
        to_id: str,
        relationship_type: str,
        properties: Dict[str, Any] = None,
    ) -> bool:
        """Create a relationship between two nodes."""
        with db.session() as session:
            query = f"""
            MATCH (a:{self._collection_name} {{id: $from_id}})
            MATCH (b:{self._collection_name} {{id: $to_id}})
            CREATE (a)-[r:{relationship_type} $properties]->(b)
            RETURN r
            """
            result = session.run(
                query, from_id=from_id, to_id=to_id, properties=properties or {}
            )
            return result.single() is not None
