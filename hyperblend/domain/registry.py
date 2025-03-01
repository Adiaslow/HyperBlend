"""Registry system for managing compound and species entries in HyperBlend."""

from typing import Dict, List, Optional, TypeVar, Generic

from hyperblend.domain.models.targets import BiologicalTarget

T = TypeVar("T")


class Registry(Generic[T]):
    """Generic registry for managing entries of a specific type."""

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._entries: Dict[str, T] = {}
        self._name_index: Dict[str, str] = {}

    def register(self, entry: T) -> None:
        """Register a new entry."""
        if not hasattr(entry, "id"):
            raise ValueError("Entry must have 'id' attribute")

        entry_id = str(getattr(entry, "id"))

        # Get the name from either 'name' or 'scientific_name' attribute
        # If neither exists, use the ID as the name
        if hasattr(entry, "name"):
            entry_name = str(getattr(entry, "name"))
        elif hasattr(entry, "scientific_name"):
            entry_name = str(getattr(entry, "scientific_name"))
        else:
            entry_name = entry_id

        if entry_id in self._entries:
            raise ValueError(f"Entry with ID {entry_id} already exists")

        # Only enforce name uniqueness for non-BiologicalTarget entries
        if not isinstance(entry, BiologicalTarget):
            if entry_name in self._name_index and entry_name != entry_id:
                raise ValueError(f"Entry with name {entry_name} already exists")

        self._entries[entry_id] = entry
        self._name_index[entry_name] = entry_id

    def get_by_id(self, entry_id: str) -> Optional[T]:
        """Get an entry by its ID."""
        return self._entries.get(entry_id)

    def get_by_name(self, name: str) -> Optional[T]:
        """Get an entry by its name."""
        entry_id = self._name_index.get(name)
        if entry_id:
            return self._entries.get(entry_id)
        return None

    def list_all(self) -> List[T]:
        """Get all entries."""
        return list(self._entries.values())

    def count(self) -> int:
        """Get the number of entries."""
        return len(self._entries)


# Global registries
compound_registry = Registry()
source_registry = Registry()
target_registry = Registry()
