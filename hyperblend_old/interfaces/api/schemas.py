# hyperblend/interfaces/api/schemas.py
"""Pydantic schemas for the HyperBlend API."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class CompoundBase(BaseModel):
    """Base schema for compounds."""

    id: str
    name: str
    smiles: Optional[str] = None
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    description: Optional[str] = None
    pubchem_id: Optional[str] = None
    chembl_id: Optional[str] = None
    pubchem_data: Optional[Dict[str, Any]] = None
    chembl_data: Optional[Dict[str, Any]] = None


class CompoundCreate(CompoundBase):
    """Schema for creating a compound."""

    pass


class CompoundRead(CompoundBase):
    """Schema for reading a compound."""

    sources: List["SourceRead"] = []
    targets: List["BiologicalTargetRead"] = []


class SourceBase(BaseModel):
    """Base schema for sources."""

    id: str
    name: str
    type: str
    common_names: Optional[List[str]] = None
    description: Optional[str] = None
    native_regions: Optional[List[str]] = None
    traditional_uses: Optional[List[str]] = None


class SourceCreate(SourceBase):
    """Schema for creating a source."""

    pass


class SourceRead(SourceBase):
    """Schema for reading a source."""

    compounds: List[CompoundBase] = []


class BiologicalTargetBase(BaseModel):
    """Base schema for biological targets."""

    id: str
    name: str
    type: str
    description: Optional[str] = None
    external_ids: Optional[Dict[str, str]] = None


class BiologicalTargetCreate(BiologicalTargetBase):
    """Schema for creating a biological target."""

    pass


class BiologicalTargetRead(BiologicalTargetBase):
    """Schema for reading a biological target."""

    compounds: List[CompoundBase] = []


# Update forward references
CompoundRead.model_rebuild()
SourceRead.model_rebuild()
BiologicalTargetRead.model_rebuild()
