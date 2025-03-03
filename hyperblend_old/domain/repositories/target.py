# hyperblend/domain/repositories/target.py

"""Target repository interface."""

from abc import abstractmethod
from typing import List, Optional
from .base import BaseRepository
from ..models.target import Target, TargetType


class TargetRepository(BaseRepository[Target]):
    """Repository interface for biological targets."""

    @abstractmethod
    async def find_by_name(self, name: str) -> List[Target]:
        """Find targets by name."""
        pass

    @abstractmethod
    async def find_by_type(self, target_type: TargetType) -> List[Target]:
        """Find targets by type."""
        pass

    @abstractmethod
    async def find_by_external_id(
        self, id_type: str, id_value: str
    ) -> Optional[Target]:
        """Find a target by external ID (UniProt, ChEMBL, etc.)."""
        pass

    @abstractmethod
    async def find_by_gene(self, gene_name: str) -> List[Target]:
        """Find targets by gene name."""
        pass

    @abstractmethod
    async def find_by_organism(self, organism: str) -> List[Target]:
        """Find targets by organism."""
        pass

    @abstractmethod
    async def get_compounds(self, target_id: str) -> List[str]:
        """Get IDs of compounds that interact with this target."""
        pass

    @abstractmethod
    async def add_compound_interaction(
        self,
        target_id: str,
        compound_id: str,
        action: str,
        action_type: Optional[str] = None,
        action_value: Optional[float] = None,
    ) -> bool:
        """Add a compound interaction to a target."""
        pass
