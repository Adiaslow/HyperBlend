from typing import List, Optional, Dict, Any
from pydantic import Field, EmailStr, HttpUrl, BaseModel
from .base import BaseEntity


class Compound(BaseModel):
    """Model representing a chemical compound."""

    id: Optional[str] = Field(None, description="Unique identifier for the compound")
    name: str = Field(..., description="Name of the compound")
    iupac_name: Optional[str] = Field(None, description="IUPAC name of the compound")
    molecular_formula: Optional[str] = Field(None, description="Molecular formula")
    molecular_weight: Optional[float] = Field(
        None, description="Molecular weight in g/mol"
    )
    smiles: str = Field(
        ..., description="SMILES representation of the compound structure"
    )
    inchi: Optional[str] = Field(None, description="InChI representation")
    inchi_key: Optional[str] = Field(None, description="InChI key")
    cas_number: Optional[str] = Field(None, description="CAS registry number")
    drugbank_id: Optional[str] = Field(None, description="DrugBank ID")
    chembl_id: Optional[str] = Field(None, description="ChEMBL ID")
    pubchem_cid: Optional[int] = Field(None, description="PubChem CID")
    chebi_id: Optional[str] = Field(None, description="ChEBI ID")
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Additional chemical properties"
    )
    description: Optional[str] = Field(None, description="Description of the compound")

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


class Source(BaseModel):
    """Model representing a natural source."""

    id: Optional[str] = Field(None, description="Unique identifier for the source")
    name: str = Field(..., description="Name of the source")
    type: str = Field(
        ..., description="Type of the source (e.g., database, publication)"
    )
    region: Optional[str] = Field(None, description="Region of the source")
    description: Optional[str] = Field(None, description="Description of the source")
    compound_count: Optional[int] = Field(
        0, description="Number of compounds associated with the source"
    )

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


class Target(BaseModel):
    """Model representing a biological target."""

    id: Optional[str] = Field(None, description="Unique identifier for the target")
    name: str = Field(..., description="Name of the target")
    type: str = Field(..., description="Type of the target (e.g., protein, gene)")
    family: Optional[str] = Field(None, description="Family of the target")
    organism: Optional[str] = Field(None, description="Organism the target belongs to")
    description: Optional[str] = Field(None, description="Description of the target")
    compound_count: Optional[int] = Field(
        0, description="Number of compounds associated with the target"
    )

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


class Relationship(BaseModel):
    """Model representing a relationship between nodes."""

    source_id: str = Field(..., description="ID of the source node")
    target_id: str = Field(..., description="ID of the target node")
    type: str = Field(..., description="Type of the relationship")
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Additional properties of the relationship"
    )

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


class GraphData(BaseModel):
    """Model representing graph visualization data."""

    nodes: List[Dict[str, Any]] = Field(..., description="List of nodes in the graph")
    links: List[Dict[str, Any]] = Field(
        ..., description="List of relationships between nodes"
    )

    class Config:
        """Pydantic model configuration."""

        from_attributes = True
