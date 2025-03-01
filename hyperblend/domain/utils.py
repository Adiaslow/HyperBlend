"""Utility functions for the domain layer."""

from typing import Dict, Any
from hyperblend.domain.models.compounds import Compound
from hyperblend.domain.models.sources import Source
from hyperblend.domain.models.targets import BiologicalTarget


def format_display_data(entity: Compound | Source | BiologicalTarget) -> Dict[str, Any]:
    """Format entity data for display in the web interface.

    Args:
        entity: The entity to format (Compound, Source, or BiologicalTarget)

    Returns:
        A dictionary containing formatted data for display
    """
    if hasattr(entity, "display_data"):
        return entity.display_data
    return {
        "id": entity.id,
        "name": entity.name,
        "type": getattr(entity, "type", None),
        "description": getattr(entity, "description", None),
    }
