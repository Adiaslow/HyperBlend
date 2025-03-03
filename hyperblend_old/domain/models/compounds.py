"""Domain models for compounds and their properties."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from hyperblend_old.domain.models.sources import Source
    from hyperblend_old.domain.models.targets import BiologicalTarget


@dataclass
class Compound:
    """Domain model for chemical compounds."""

    id: str
    name: str
    canonical_name: str
    description: Optional[str] = None
    smiles: Optional[str] = None
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    pubchem_id: Optional[str] = None
    chembl_id: Optional[str] = None
    napralert_id: Optional[str] = None
    sources: List["Source"] = field(default_factory=list)
    targets: List["BiologicalTarget"] = field(default_factory=list)

    @property
    def display_data(self) -> Dict[str, Any]:
        """Get formatted data for display in the web interface."""
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
            "sources": [
                {
                    "id": source.id,
                    "name": source.name,
                    "type": source.type,
                }
                for source in self.sources
            ],
            "targets": [
                {
                    "id": target.id,
                    "name": target.name,
                    "type": target.type,
                }
                for target in self.targets
            ],
        }
