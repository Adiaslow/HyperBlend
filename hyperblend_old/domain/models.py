"""Domain models for the HyperBlend system."""

from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime


class SourceType(str, Enum):
    """Type of source."""

    PLANT = "PLANT"
    FUNGUS = "FUNGUS"
    BACTERIA = "BACTERIA"
    ANIMAL = "ANIMAL"
    SYNTHETIC = "SYNTHETIC"


class TargetType(Enum):
    """Type of target."""

    UNKNOWN = "UNKNOWN"
    PROTEIN = "PROTEIN"
    ENZYME = "ENZYME"
    RECEPTOR = "RECEPTOR"
    ION_CHANNEL = "ION_CHANNEL"
    TRANSPORTER = "TRANSPORTER"
    TRANSCRIPTION_FACTOR = "TRANSCRIPTION_FACTOR"
    CELL_LINE = "CELL_LINE"
    TISSUE = "TISSUE"
    ORGANISM = "ORGANISM"
    PATHWAY = "PATHWAY"


class Source:
    """A source of compounds."""

    def __init__(
        self,
        id: str,
        name: str,
        type: SourceType,
        common_names: List[str],
        description: str = "",
        native_regions: Optional[List[str]] = None,
        traditional_uses: Optional[List[str]] = None,
        taxonomy: Optional[Dict[str, str]] = None,
        created_at: Optional[datetime] = None,
        last_updated: Optional[datetime] = None,
    ):
        """Initialize a source."""
        self.id = id
        self.name = name
        self.type = type
        self.common_names = common_names
        self.description = description
        self.native_regions = native_regions if native_regions is not None else []
        self.traditional_uses = traditional_uses if traditional_uses is not None else []
        self.taxonomy = taxonomy if taxonomy is not None else {}
        self.created_at = created_at if created_at is not None else datetime.now()
        self.last_updated = last_updated if last_updated is not None else datetime.now()


class Compound:
    """A chemical compound."""

    def __init__(
        self,
        id: str,
        name: str,
        canonical_name: str,
        description: str = "",
        smiles: str = "",
        molecular_formula: str = "",
        molecular_weight: Optional[float] = None,
        pubchem_id: str = "",
        chembl_id: str = "",
        coconut_id: str = "",
        created_at: Optional[datetime] = None,
        last_updated: Optional[datetime] = None,
    ):
        """Initialize a compound."""
        self.id = id
        self.name = name
        self.canonical_name = canonical_name
        self.description = description
        self.smiles = smiles
        self.molecular_formula = molecular_formula
        self.molecular_weight = molecular_weight
        self.pubchem_id = pubchem_id
        self.chembl_id = chembl_id
        self.coconut_id = coconut_id
        self.created_at = created_at if created_at is not None else datetime.now()
        self.last_updated = last_updated if last_updated is not None else datetime.now()


class Target:
    """A biological target."""

    def __init__(
        self,
        id: str,
        name: str,
        standardized_name: str,
        type: TargetType,
        organism: str,
        description: str = "",
        uniprot_id: str = "",
        chembl_id: str = "",
        gene_id: str = "",
        gene_name: str = "",
        created_at: Optional[datetime] = None,
        last_updated: Optional[datetime] = None,
    ):
        """Initialize a target."""
        self.id = id
        self.name = name
        self.standardized_name = standardized_name
        self.type = type
        self.organism = organism
        self.description = description
        self.uniprot_id = uniprot_id
        self.chembl_id = chembl_id
        self.gene_id = gene_id
        self.gene_name = gene_name
        self.created_at = created_at if created_at is not None else datetime.now()
        self.last_updated = last_updated if last_updated is not None else datetime.now()
