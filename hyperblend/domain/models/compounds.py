"""Domain models for compounds and their properties."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from hyperblend.domain.models.sources import Source
    from hyperblend.domain.models.targets import BiologicalTarget


@dataclass
class Compound:
    """Domain model for chemical compounds."""

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
    last_updated: datetime = field(default_factory=datetime.utcnow)
    sources: List["Source"] = field(default_factory=list)
    targets: List["BiologicalTarget"] = field(default_factory=list)

    @property
    def display_data(self) -> Dict[str, Any]:
        """Get formatted data for display in the web interface."""
        return {
            "id": self.id,
            "name": self.name,
            "smiles": self.smiles,
            "molecular_formula": self.molecular_formula,
            "molecular_weight": self.molecular_weight,
            "description": self.description,
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
            "external_data": {
                "pubchem": self.pubchem_data,
                "chembl": self.chembl_data,
            },
        }
