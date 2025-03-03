# hyperblend/domain/repositories/base.py

"""Base repository interface."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Any

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Base repository interface for all domain entities."""

    @abstractmethod
    async def get(self, id: str) -> Optional[T]:
        """Retrieve an entity by ID."""
        pass

    @abstractmethod
    async def get_all(self) -> List[T]:
        """Retrieve all entities."""
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity."""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete an entity by ID."""
        pass

    @abstractmethod
    async def find_by(self, **kwargs: Any) -> List[T]:
        """Find entities by attributes."""
        pass
