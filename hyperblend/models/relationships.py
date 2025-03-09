"""Models representing relationships between entities in the system."""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class MoleculeOrganismRelationship(BaseModel):
    """Relationship between a molecule and an organism."""

    molecule_id: str = Field(..., description="ID of the molecule")
    organism_id: str = Field(..., description="ID of the organism")
    relationship_type: str = Field(
        ..., description="Type of relationship (e.g., 'FOUND_IN', 'PRODUCED_BY')"
    )
    concentration: Optional[float] = Field(
        None, description="Concentration in organism (if known)"
    )
    concentration_unit: Optional[str] = Field(
        None, description="Unit of concentration measurement"
    )
    source: Optional[str] = Field(
        None, description="Source of this relationship information"
    )
    confidence_score: Optional[float] = Field(
        None, description="Confidence score (0-1) of the relationship"
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )


class MoleculeTargetRelationship(BaseModel):
    """Relationship between a molecule and a target."""

    molecule_id: str = Field(..., description="ID of the molecule")
    target_id: str = Field(..., description="ID of the target")
    relationship_type: str = Field(
        ..., description="Type of interaction (e.g., 'INHIBITS', 'ACTIVATES')"
    )
    activity_value: Optional[float] = Field(
        None, description="Activity value (e.g., IC50, EC50)"
    )
    activity_unit: Optional[str] = Field(
        None, description="Unit of activity measurement"
    )
    activity_type: Optional[str] = Field(
        None, description="Type of activity measurement"
    )
    source: Optional[str] = Field(
        None, description="Source of this relationship information"
    )
    confidence_score: Optional[float] = Field(
        None, description="Confidence score (0-1) of the relationship"
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )


class OrganismTargetRelationship(BaseModel):
    """Relationship between an organism and a target."""

    organism_id: str = Field(..., description="ID of the organism")
    target_id: str = Field(..., description="ID of the target")
    relationship_type: str = Field(
        ..., description="Type of relationship (e.g., 'EXPRESSES', 'REGULATES')"
    )
    expression_level: Optional[float] = Field(
        None, description="Expression level if applicable"
    )
    source: Optional[str] = Field(
        None, description="Source of this relationship information"
    )
    confidence_score: Optional[float] = Field(
        None, description="Confidence score (0-1) of the relationship"
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )


class Config:
    """Pydantic model configuration."""

    json_schema_extra = {
        "examples": {
            "molecule_organism": {
                "molecule_id": "MOL123",
                "organism_id": "ORG123",
                "relationship_type": "FOUND_IN",
                "concentration": 0.5,
                "concentration_unit": "mg/g",
                "source": "Scientific literature",
                "confidence_score": 0.85,
                "last_updated": "2024-03-03T12:00:00Z",
            },
            "molecule_target": {
                "molecule_id": "MOL123",
                "target_id": "TAR123",
                "relationship_type": "INHIBITS",
                "activity_value": 1.2,
                "activity_unit": "nM",
                "activity_type": "IC50",
                "source": "ChEMBL",
                "confidence_score": 0.95,
                "last_updated": "2024-03-03T12:00:00Z",
            },
            "organism_target": {
                "organism_id": "ORG123",
                "target_id": "TAR123",
                "relationship_type": "EXPRESSES",
                "expression_level": 2.5,
                "source": "UniProt",
                "confidence_score": 0.75,
                "last_updated": "2024-03-03T12:00:00Z",
            },
        }
    }
