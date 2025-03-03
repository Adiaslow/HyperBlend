"""Domain models for natural product sources."""

from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import Field
from .base import BaseNamedEntity


class SourceType(str, Enum):
    """Enumeration of source types."""

    PLANT = "plant"
    FUNGUS = "fungus"
    BACTERIA = "bacteria"
    ANIMAL = "animal"
    MARINE = "marine"
    OTHER = "other"


class Source(BaseNamedEntity):
    """Model for natural product sources."""

    type: SourceType = Field(SourceType.PLANT, description="Source type")
    common_names: List[str] = Field(default_factory=list, description="Common names")
    native_regions: List[str] = Field(
        default_factory=list, description="Native regions"
    )
    traditional_uses: List[str] = Field(
        default_factory=list, description="Traditional uses"
    )
    kingdom: str = Field(default="", description="Taxonomic kingdom")
    division: str = Field(default="", description="Taxonomic division/phylum")
    class_name: str = Field(default="", description="Taxonomic class")
    order: str = Field(default="", description="Taxonomic order")
    family: str = Field(default="", description="Taxonomic family")
    genus: str = Field(default="", description="Taxonomic genus")
    species: str = Field(default="", description="Taxonomic species")

    def add_common_name(self, name: str) -> None:
        """Add a common name if it doesn't exist."""
        if name not in self.common_names:
            self.common_names.append(name)

    def add_traditional_use(self, use: str) -> None:
        """Add a traditional use if it doesn't exist."""
        if use not in self.traditional_uses:
            self.traditional_uses.append(use)

    def add_native_region(self, region: str) -> None:
        """Add a native region if it doesn't exist."""
        if region not in self.native_regions:
            self.native_regions.append(region)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the source to a dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "common_names": self.common_names,
            "native_regions": self.native_regions,
            "traditional_uses": self.traditional_uses,
            "kingdom": self.kingdom,
            "division": self.division,
            "class_name": self.class_name,
            "order": self.order,
            "family": self.family,
            "genus": self.genus,
            "species": self.species,
        }

    def to_neo4j_dict(self) -> Dict[str, Any]:
        """Convert the source to a Neo4j-compatible dictionary format."""
        data = self.model_dump()
        data["type"] = data["type"].value
        # Remove empty taxonomic fields
        for field in [
            "kingdom",
            "division",
            "class_name",
            "order",
            "family",
            "genus",
            "species",
        ]:
            if not data.get(field):
                data.pop(field, None)
        return data

    @classmethod
    def from_neo4j_dict(cls, data: Dict[str, Any]) -> "Source":
        """Create a Source instance from Neo4j data."""
        # Convert type string to enum
        if isinstance(data.get("type"), str):
            data["type"] = SourceType(data["type"])
        return cls(**data)
