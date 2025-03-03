"""Domain models for biological targets."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from hyperblend_old.domain.models.compounds import Compound


@dataclass
class BiologicalTarget:
    """Domain model for biological targets (receptors, enzymes, etc.)."""

    id: str
    name: str
    type: str  # e.g., "receptor", "enzyme", "transporter"
    organism: str
    description: Optional[str] = None
    uniprot_id: Optional[str] = None
    chembl_id: Optional[str] = None
    standardized_name: Optional[str] = None
    compounds: List["Compound"] = field(default_factory=list)

    @property
    def display_data(self) -> Dict[str, Any]:
        """Get formatted data for display in the web interface."""
        return {
            "id": self.id,
            "name": self.name,
            "standardized_name": self.standardized_name,
            "type": self.type,
            "description": self.description,
            "organism": self.organism,
            "identifiers": {
                "uniprot": self.uniprot_id,
                "chembl": self.chembl_id,
            },
            "compounds": [
                {
                    "id": compound.id,
                    "name": compound.name,
                }
                for compound in self.compounds
            ],
        }
