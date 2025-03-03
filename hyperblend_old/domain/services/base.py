"""Base service class."""

from typing import Generic, TypeVar
from ..repositories.base import BaseRepository

T = TypeVar("T")


class BaseService(Generic[T]):
    """Base service class for all domain entities."""

    def __init__(self, repository: BaseRepository[T]):
        """Initialize the service with a repository."""
        self._repository = repository

    async def get(self, id: str) -> T:
        """Get an entity by ID."""
        entity = await self._repository.get(id)
        if entity is None:
            raise ValueError(f"Entity with ID {id} not found")
        return entity

    async def create(self, entity: T) -> T:
        """Create a new entity."""
        return await self._repository.create(entity)

    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        return await self._repository.update(entity)

    async def delete(self, id: str) -> bool:
        """Delete an entity by ID."""
        return await self._repository.delete(id)
