"""Domain models for compounds and related entities."""

from typing import List, Optional, Dict, Any
from pydantic import Field, validator
from .base import BaseNamedEntity


class Synonym(BaseNamedEntity):
    """Model for compound synonyms."""

    source: str = Field(
        ..., description="Source of the synonym (e.g., PubChem, ChEMBL)"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the synonym to a dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "description": self.description,
        }


class Compound(BaseNamedEntity):
    """Model for chemical compounds."""

    canonical_name: str = Field(..., description="Standardized compound name")
    smiles: Optional[str] = Field(None, description="SMILES representation")
    molecular_formula: Optional[str] = Field(None, description="Molecular formula")
    molecular_weight: Optional[float] = Field(
        None, description="Molecular weight in g/mol"
    )
    pubchem_id: Optional[str] = Field(None, description="PubChem compound ID")
    chembl_id: Optional[str] = Field(None, description="ChEMBL compound ID")
    napralert_id: Optional[str] = Field(None, description="NAPRALERT compound ID")
    coconut_id: Optional[str] = Field(None, description="COCONUT compound ID")
    synonyms: List[Synonym] = Field(
        default_factory=list, description="List of compound synonyms"
    )

    @validator("molecular_weight")
    def validate_molecular_weight(cls, v: Optional[float]) -> Optional[float]:
        """Validate that molecular weight is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("Molecular weight must be positive")
        return v

    def add_synonym(self, name: str, source: str) -> None:
        """Add a new synonym if it doesn't exist."""
        if not any(s.name == name and s.source == source for s in self.synonyms):
            self.synonyms.append(
                Synonym(id=f"SYN_{len(self.synonyms)}", name=name, source=source)
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the compound to a dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "canonical_name": self.canonical_name,
            "smiles": self.smiles,
            "molecular_formula": self.molecular_formula,
            "molecular_weight": self.molecular_weight,
            "description": self.description,
            "pubchem_id": self.pubchem_id,
            "chembl_id": self.chembl_id,
            "napralert_id": self.napralert_id,
            "coconut_id": self.coconut_id,
            "synonyms": [s.to_dict() for s in self.synonyms],
        }

    def to_neo4j_dict(self) -> Dict[str, Any]:
        """Convert the compound to a Neo4j-compatible dictionary format."""
        data = self.model_dump()
        # Remove empty fields
        for field in [
            "smiles",
            "molecular_formula",
            "molecular_weight",
            "pubchem_id",
            "chembl_id",
            "napralert_id",
            "coconut_id",
            "description",
        ]:
            if not data.get(field):
                data.pop(field, None)
        # Remove synonyms as they are stored as separate nodes
        data.pop("synonyms", None)
        return data

    @classmethod
    def from_neo4j_dict(cls, data: Dict[str, Any]) -> "Compound":
        """Create a Compound instance from Neo4j data."""
        # Convert numeric strings to appropriate types
        if "molecular_weight" in data and isinstance(data["molecular_weight"], str):
            try:
                data["molecular_weight"] = float(data["molecular_weight"])
            except (ValueError, TypeError):
                data.pop("molecular_weight", None)
        return cls(**data)
