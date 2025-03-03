"""Source repository interface."""

from abc import abstractmethod
from typing import List, Optional, Dict
from .base import BaseRepository
from ..models.source import Source, SourceType


class SourceRepository(BaseRepository[Source]):
    """Repository interface for natural product sources."""

    @abstractmethod
    async def find_by_name(self, name: str) -> List[Source]:
        """Find sources by name or common name."""
        pass

    @abstractmethod
    async def find_by_type(self, source_type: SourceType) -> List[Source]:
        """Find sources by type."""
        pass

    @abstractmethod
    async def find_by_region(self, region: str) -> List[Source]:
        """Find sources by native region."""
        pass

    @abstractmethod
    async def find_by_traditional_use(self, use: str) -> List[Source]:
        """Find sources by traditional use."""
        pass

    @abstractmethod
    async def find_by_taxonomy(self, rank: str, value: str) -> List[Source]:
        """Find sources by taxonomic classification."""
        pass

    @abstractmethod
    async def get_compounds(self, source_id: str) -> List[str]:
        """Get IDs of compounds found in this source."""
        pass

    @abstractmethod
    async def add_compound(self, source_id: str, compound_id: str) -> bool:
        """Add a compound to a source."""
        pass

    @abstractmethod
    async def update_taxonomy(self, source_id: str, taxonomy: Dict[str, str]) -> bool:
        """Update the taxonomic classification of a source."""
        pass
