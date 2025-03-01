# hyperblend/domain/entry_manager.py

"""Entry manager for HyperBlend."""

from enum import Enum
from typing import Dict, List, Optional, Set, TypeVar, Generic, Any
from uuid import UUID

from hyperblend.domain.models.compounds import Compound
from hyperblend.domain.models.sources import Source
from hyperblend.domain.models.targets import BiologicalTarget


class EntryType(str, Enum):
    """Types of entries in the system."""

    COMPOUND = "COMPOUND"
    SOURCE = "SOURCE"
    BIOLOGICAL_TARGET = "BIOLOGICAL_TARGET"


T = TypeVar("T")


class EntryManager(Generic[T]):
    """Manager for entries in the system."""

    def __init__(self):
        """Initialize the entry manager."""
        self._entries: Dict[UUID, T] = {}
        self._entries_by_type: Dict[EntryType, Set[UUID]] = {
            t: set() for t in EntryType
        }

    def register(self, entry: T) -> None:
        """Register an entry in the system.

        Args:
            entry: Entry to register
        """
        entry_id = getattr(entry, "id")
        entry_type = self._get_entry_type(entry)

        self._entries[entry_id] = entry
        self._entries_by_type[entry_type].add(entry_id)

    def get_by_id(self, entry_id: UUID) -> Optional[T]:
        """Get an entry by its ID.

        Args:
            entry_id: ID of the entry

        Returns:
            Entry if found, None otherwise
        """
        return self._entries.get(entry_id)

    def get_by_type(self, entry_type: EntryType) -> List[T]:
        """Get all entries of a given type.

        Args:
            entry_type: Type of entries to get

        Returns:
            List of entries of the given type
        """
        return [
            self._entries[entry_id] for entry_id in self._entries_by_type[entry_type]
        ]

    def _get_entry_type(self, entry: T) -> EntryType:
        """Get the type of an entry.

        Args:
            entry: Entry to get type for

        Returns:
            Type of the entry

        Raises:
            ValueError: If entry type is not recognized
        """
        if isinstance(entry, Compound):
            return EntryType.COMPOUND
        elif isinstance(entry, Source):
            return EntryType.SOURCE
        elif isinstance(entry, BiologicalTarget):
            return EntryType.BIOLOGICAL_TARGET
        else:
            raise ValueError(f"Unknown entry type: {type(entry)}")


# Global entry manager instance
entry_manager = EntryManager()
