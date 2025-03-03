"""Domain models for biological targets and their relationships."""

from typing import Optional, Dict, Any
from enum import Enum
from pydantic import Field
from .base import BaseNamedEntity


class TargetType(str, Enum):
    """Enumeration of target types."""

    RECEPTOR = "receptor"
    ENZYME = "enzyme"
    TRANSPORTER = "transporter"
    ION_CHANNEL = "ion_channel"
    PROTEIN = "protein"
    OTHER = "other"


class Target(BaseNamedEntity):
    """Model for biological targets."""

    standardized_name: str = Field(..., description="Standardized target name")
    type: TargetType = Field(TargetType.PROTEIN, description="Target type")
    organism: str = Field("Homo sapiens", description="Target organism")
    uniprot_id: Optional[str] = Field(None, description="UniProt ID")
    chembl_id: Optional[str] = Field(None, description="ChEMBL target ID")
    gene_id: Optional[str] = Field(None, description="Gene ID")
    gene_name: Optional[str] = Field(None, description="Gene name")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the target to a dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "standardized_name": self.standardized_name,
            "type": self.type.value,
            "description": self.description,
            "organism": self.organism,
            "uniprot_id": self.uniprot_id,
            "chembl_id": self.chembl_id,
            "gene_id": self.gene_id,
            "gene_name": self.gene_name,
        }

    def to_neo4j_dict(self) -> Dict[str, Any]:
        """Convert the target to a Neo4j-compatible dictionary format."""
        data = self.model_dump()
        data["type"] = data["type"].value
        return data

    @classmethod
    def from_neo4j_dict(cls, data: Dict[str, Any]) -> "Target":
        """Create a Target instance from Neo4j data."""
        if isinstance(data.get("type"), str):
            data["type"] = TargetType(data["type"])
        return cls(**data)
