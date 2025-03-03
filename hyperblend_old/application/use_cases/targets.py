"""Use cases for managing biological targets."""

from typing import List, Optional, Dict, Any
from hyperblend_old.domain.models import Target, TargetType
from hyperblend_old.domain.services import TargetService
from hyperblend_old.core.exceptions import DatabaseError


async def create_target(service: TargetService, target_data: Dict[str, Any]) -> Target:
    """Create a new biological target."""
    try:
        return await service.create_from_data(target_data)
    except Exception as e:
        raise DatabaseError(f"Error creating target: {str(e)}")


async def update_target(
    service: TargetService, target_id: str, target_data: Dict[str, Any]
) -> Target:
    """Update an existing biological target."""
    try:
        return await service.update_from_data(target_id, target_data)
    except Exception as e:
        raise DatabaseError(f"Error updating target: {str(e)}")


async def delete_target(service: TargetService, target_id: str) -> bool:
    """Delete a biological target."""
    try:
        return await service.delete(target_id)
    except Exception as e:
        raise DatabaseError(f"Error deleting target: {str(e)}")


async def get_target(service: TargetService, target_id: str) -> Target:
    """Get a biological target by ID."""
    try:
        return await service.get(target_id)
    except Exception as e:
        raise DatabaseError(f"Error getting target: {str(e)}")


async def list_targets(service: TargetService) -> List[Target]:
    """List all biological targets."""
    try:
        return await service._repository.get_all()
    except Exception as e:
        raise DatabaseError(f"Error listing targets: {str(e)}")


async def search_targets(
    service: TargetService,
    name: Optional[str] = None,
    target_type: Optional[TargetType] = None,
    organism: Optional[str] = None,
) -> List[Target]:
    """Search for biological targets by various criteria."""
    try:
        results: List[Target] = []
        if name:
            results.extend(await service.find_by_name(name))
        if target_type:
            results.extend(await service.find_by_type(target_type))
        if organism:
            results.extend(await service.find_by_organism(organism))
        # Remove duplicates while preserving order
        seen = set()
        return [x for x in results if not (x.id in seen or seen.add(x.id))]
    except Exception as e:
        raise DatabaseError(f"Error searching targets: {str(e)}")


async def find_targets_by_gene(service: TargetService, gene_name: str) -> List[Target]:
    """Find targets by gene name."""
    try:
        return await service.find_by_gene(gene_name)
    except Exception as e:
        raise DatabaseError(f"Error finding targets by gene: {str(e)}")


async def get_target_compounds(service: TargetService, target_id: str) -> List[str]:
    """Get compounds that interact with a target."""
    try:
        return await service.get_compounds(target_id)
    except Exception as e:
        raise DatabaseError(f"Error getting target compounds: {str(e)}")


async def add_compound_interaction(
    service: TargetService,
    target_id: str,
    compound_id: str,
    action: str,
    action_type: Optional[str] = None,
    action_value: Optional[float] = None,
) -> bool:
    """Add a compound interaction to a target."""
    try:
        return await service.add_compound_interaction(
            target_id, compound_id, action, action_type, action_value
        )
    except Exception as e:
        raise DatabaseError(f"Error adding compound interaction: {str(e)}")
