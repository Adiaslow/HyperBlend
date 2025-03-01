"""Domain models for compound sources."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from hyperblend.domain.models.compounds import Compound


@dataclass
class Source:
    """Domain model for compound sources (plants, fungi, etc.)."""

    id: str
    name: str
    type: str  # e.g., "plant", "fungus"
    common_names: Optional[List[str]] = None
    description: Optional[str] = None
    native_regions: Optional[List[str]] = None
    traditional_uses: Optional[List[str]] = None
    compounds: List["Compound"] = field(default_factory=list)

    @property
    def display_data(self) -> Dict:
        """Get formatted data for display in the web interface."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "common_names": self.common_names,
            "description": self.description,
            "native_regions": self.native_regions,
            "traditional_uses": self.traditional_uses,
            "compounds": [
                {
                    "name": compound.name,
                    "id": compound.id,
                }
                for compound in self.compounds
            ],
        }
