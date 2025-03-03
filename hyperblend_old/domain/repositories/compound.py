"""Compound repository interface."""

from abc import abstractmethod
from typing import List, Optional
from .base import BaseRepository
from ..models.compound import Compound


class CompoundRepository(BaseRepository[Compound]):
    """Repository interface for compounds."""

    @abstractmethod
    async def find_by_name(self, name: str) -> List[Compound]:
        """Find compounds by name or synonym."""
        pass

    @abstractmethod
    async def find_by_smiles(self, smiles: str) -> Optional[Compound]:
        """Find a compound by SMILES string."""
        pass

    @abstractmethod
    async def find_by_external_id(
        self, id_type: str, id_value: str
    ) -> Optional[Compound]:
        """Find a compound by external ID (PubChem, ChEMBL, etc.)."""
        pass

    @abstractmethod
    async def find_similar(self, smiles: str, threshold: float = 0.8) -> List[Compound]:
        """Find compounds similar to the given SMILES string."""
        pass

    @abstractmethod
    async def add_synonym(self, compound_id: str, name: str, source: str) -> bool:
        """Add a synonym to a compound."""
        pass

    @abstractmethod
    async def get_synonyms(self, compound_id: str) -> List[str]:
        """Get all synonyms for a compound."""
        pass

    @abstractmethod
    async def get_targets(self, compound_id: str) -> List[str]:
        """Get IDs of targets that interact with a compound."""
        pass

    @abstractmethod
    async def get_sources(self, compound_id: str) -> List[str]:
        """Get IDs of sources that contain a compound."""
        pass
