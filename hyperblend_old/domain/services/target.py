# hyperblend/domain/services/target.py

"""Target service class."""

from typing import List, Optional, Dict, Any
from .base import BaseService
from ..models.target import Target, TargetType
from ..repositories.target import TargetRepository


class TargetService(BaseService[Target]):
    """Service for managing biological targets."""

    def __init__(self, repository: TargetRepository):
        """Initialize the service with a target repository."""
        super().__init__(repository)
        self._target_repository = repository

    async def find_by_name(self, name: str) -> List[Target]:
        """Find targets by name."""
        return await self._target_repository.find_by_name(name)

    async def find_by_type(self, target_type: TargetType) -> List[Target]:
        """Find targets by type."""
        return await self._target_repository.find_by_type(target_type)

    async def find_by_external_id(
        self, id_type: str, id_value: str
    ) -> Optional[Target]:
        """Find a target by external ID."""
        return await self._target_repository.find_by_external_id(id_type, id_value)

    async def find_by_gene(self, gene_name: str) -> List[Target]:
        """Find targets by gene name."""
        return await self._target_repository.find_by_gene(gene_name)

    async def find_by_organism(self, organism: str) -> List[Target]:
        """Find targets by organism."""
        return await self._target_repository.find_by_organism(organism)

    async def get_compounds(self, target_id: str) -> List[str]:
        """Get IDs of compounds that interact with this target."""
        return await self._target_repository.get_compounds(target_id)

    async def add_compound_interaction(
        self,
        target_id: str,
        compound_id: str,
        action: str,
        action_type: Optional[str] = None,
        action_value: Optional[float] = None,
    ) -> bool:
        """Add a compound interaction to a target."""
        return await self._target_repository.add_compound_interaction(
            target_id, compound_id, action, action_type, action_value
        )

    async def create_from_data(self, data: Dict[str, Any]) -> Target:
        """Create a target from dictionary data."""
        target = Target(**data)
        return await self.create(target)

    async def update_from_data(self, target_id: str, data: Dict[str, Any]) -> Target:
        """Update a target from dictionary data."""
        target = await self.get(target_id)
        for key, value in data.items():
            setattr(target, key, value)
        return await self.update(target)
