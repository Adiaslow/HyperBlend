# hyperblend/domain/services/source.py

"""Source service class."""

from typing import List, Dict, Any
from .base import BaseService
from ..models.source import Source, SourceType
from ..repositories.source import SourceRepository


class SourceService(BaseService[Source]):
    """Service for managing natural product sources."""

    def __init__(self, repository: SourceRepository):
        """Initialize the service with a source repository."""
        super().__init__(repository)
        self._source_repository = repository

    async def find_by_name(self, name: str) -> List[Source]:
        """Find sources by name or common name."""
        return await self._source_repository.find_by_name(name)

    async def find_by_type(self, source_type: SourceType) -> List[Source]:
        """Find sources by type."""
        return await self._source_repository.find_by_type(source_type)

    async def find_by_region(self, region: str) -> List[Source]:
        """Find sources by native region."""
        return await self._source_repository.find_by_region(region)

    async def find_by_traditional_use(self, use: str) -> List[Source]:
        """Find sources by traditional use."""
        return await self._source_repository.find_by_traditional_use(use)

    async def find_by_taxonomy(self, rank: str, value: str) -> List[Source]:
        """Find sources by taxonomic classification."""
        return await self._source_repository.find_by_taxonomy(rank, value)

    async def get_compounds(self, source_id: str) -> List[str]:
        """Get IDs of compounds found in this source."""
        return await self._source_repository.get_compounds(source_id)

    async def add_compound(self, source_id: str, compound_id: str) -> bool:
        """Add a compound to a source."""
        return await self._source_repository.add_compound(source_id, compound_id)

    async def update_taxonomy(self, source_id: str, taxonomy: Dict[str, str]) -> bool:
        """Update the taxonomic classification of a source."""
        return await self._source_repository.update_taxonomy(source_id, taxonomy)

    async def create_from_data(self, data: Dict[str, Any]) -> Source:
        """Create a source from dictionary data."""
        source = Source(**data)
        return await self.create(source)

    async def update_from_data(self, source_id: str, data: Dict[str, Any]) -> Source:
        """Update a source from dictionary data."""
        source = await self.get(source_id)
        for key, value in data.items():
            setattr(source, key, value)
        return await self.update(source)
