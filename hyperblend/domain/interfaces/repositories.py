"""Repository interfaces for the HyperBlend system."""

from abc import ABC, abstractmethod
from typing import List, Optional, Protocol, TypeVar, Dict, Any
from ..models.compounds import Compound
from ..models.sources import Source
from ..models.targets import BiologicalTarget

T = TypeVar("T")


class Repository(Protocol[T]):
    """Base repository protocol defining common operations."""

    @abstractmethod
    async def get(self, id: str) -> Optional[T]:
        """Retrieve an entity by ID."""
        pass

    @abstractmethod
    async def list(self, filters: Optional[Dict[str, Any]] = None) -> List[T]:
        """List all entities, optionally filtered."""
        pass

    @abstractmethod
    async def add(self, entity: T) -> str:
        """Add a new entity."""
        pass

    @abstractmethod
    async def update(self, id: str, entity: T) -> bool:
        """Update an existing entity."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete an entity by ID."""
        pass


class CompoundRepository(Repository[Compound]):
    """Repository interface for managing Compound entities."""

    @abstractmethod
    async def get_by_pubchem_id(self, pubchem_id: str) -> Optional[Compound]:
        """Retrieve a compound by PubChem ID."""
        pass

    @abstractmethod
    async def get_by_chembl_id(self, chembl_id: str) -> Optional[Compound]:
        """Retrieve a compound by ChEMBL ID."""
        pass


class SourceRepository(Repository[Source]):
    """Repository interface for managing Source entities."""

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Source]:
        """Retrieve a source by scientific name."""
        pass

    @abstractmethod
    async def find_by_compound(self, compound_id: str) -> List[Source]:
        """Find all sources containing a specific compound."""
        pass


class TargetRepository(Repository[BiologicalTarget]):
    """Repository interface for managing BiologicalTarget entities."""

    @abstractmethod
    async def get_by_uniprot_id(self, uniprot_id: str) -> Optional[BiologicalTarget]:
        """Retrieve a target by UniProt ID."""
        pass

    @abstractmethod
    async def get_by_chembl_id(self, chembl_id: str) -> Optional[BiologicalTarget]:
        """Retrieve a target by ChEMBL ID."""
        pass
