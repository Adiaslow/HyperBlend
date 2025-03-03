# hyperblend/domain/services/compound.py

"""Compound service class."""

from typing import List, Optional, Dict, Any
from .base import BaseService
from ..models.compound import Compound
from ..repositories.compound import CompoundRepository


class CompoundService(BaseService[Compound]):
    """Service for managing compounds."""

    def __init__(self, repository: CompoundRepository):
        """Initialize the service with a compound repository."""
        super().__init__(repository)
        self._compound_repository = repository

    async def find_by_name(self, name: str) -> List[Compound]:
        """Find compounds by name or synonym."""
        return await self._compound_repository.find_by_name(name)

    async def find_by_smiles(self, smiles: str) -> Optional[Compound]:
        """Find a compound by SMILES string."""
        return await self._compound_repository.find_by_smiles(smiles)

    async def find_by_external_id(
        self, id_type: str, id_value: str
    ) -> Optional[Compound]:
        """Find a compound by external ID."""
        return await self._compound_repository.find_by_external_id(id_type, id_value)

    async def find_similar(self, smiles: str, threshold: float = 0.8) -> List[Compound]:
        """Find compounds similar to the given SMILES string."""
        return await self._compound_repository.find_similar(smiles, threshold)

    async def add_synonym(self, compound_id: str, name: str, source: str) -> bool:
        """Add a synonym to a compound."""
        return await self._compound_repository.add_synonym(compound_id, name, source)

    async def get_synonyms(self, compound_id: str) -> List[str]:
        """Get all synonyms for a compound."""
        return await self._compound_repository.get_synonyms(compound_id)

    async def create_from_data(self, data: Dict[str, Any]) -> Compound:
        """Create a compound from dictionary data."""
        compound = Compound(**data)
        return await self.create(compound)

    async def update_from_data(
        self, compound_id: str, data: Dict[str, Any]
    ) -> Compound:
        """Update a compound from dictionary data."""
        compound = await self.get(compound_id)
        for key, value in data.items():
            setattr(compound, key, value)
        return await self.update(compound)

    async def get_targets(self, compound_id: str) -> List[str]:
        """Get IDs of targets that interact with a compound."""
        return await self._compound_repository.get_targets(compound_id)

    async def get_sources(self, compound_id: str) -> List[str]:
        """Get IDs of sources that contain a compound."""
        return await self._compound_repository.get_sources(compound_id)
