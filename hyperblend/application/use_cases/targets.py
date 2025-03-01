"""Use cases for managing biological targets."""

from typing import List, Optional, Dict, Any, cast
from sqlalchemy.orm import Session
from sqlalchemy import inspect

from hyperblend.domain.models import BiologicalTarget
from hyperblend.infrastructure.repositories.models import (
    BiologicalTarget as TargetModel,
)


def create_target(db: Session, target_data: Dict[str, Any]) -> BiologicalTarget:
    """Create a new biological target."""
    db_target = TargetModel(**target_data)
    db.add(db_target)
    db.commit()
    db.refresh(db_target)
    return _to_domain(db_target)


def update_target(
    db: Session, target_id: str, target_data: Dict[str, Any]
) -> Optional[BiologicalTarget]:
    """Update an existing biological target."""
    db_target = db.query(TargetModel).filter(TargetModel.id == target_id).first()
    if not db_target:
        return None

    for key, value in target_data.items():
        setattr(db_target, key, value)

    db.commit()
    db.refresh(db_target)
    return _to_domain(db_target)


def delete_target(db: Session, target_id: str) -> bool:
    """Delete a biological target."""
    db_target = db.query(TargetModel).filter(TargetModel.id == target_id).first()
    if not db_target:
        return False

    db.delete(db_target)
    db.commit()
    return True


def get_target(db: Session, target_id: str) -> Optional[BiologicalTarget]:
    """Get a biological target by ID."""
    db_target = db.query(TargetModel).filter(TargetModel.id == target_id).first()
    if not db_target:
        return None
    return _to_domain(db_target)


def list_targets(
    db: Session, skip: int = 0, limit: int = 100
) -> List[BiologicalTarget]:
    """List all biological targets."""
    db_targets = db.query(TargetModel).offset(skip).limit(limit).all()
    return [_to_domain(t) for t in db_targets]


def search_targets(
    db: Session,
    name: Optional[str] = None,
    type: Optional[str] = None,
    organism: Optional[str] = None,
) -> List[BiologicalTarget]:
    """Search for biological targets by various criteria."""
    query = db.query(TargetModel)
    if name:
        query = query.filter(TargetModel.name.ilike(f"%{name}%"))
    if type:
        query = query.filter(TargetModel.type == type)
    if organism:
        query = query.filter(TargetModel.organism == organism)
    return [_to_domain(t) for t in query.all()]


def _to_domain(db_target: TargetModel) -> BiologicalTarget:
    """Convert a database model to a domain model."""
    # Get the actual values from the SQLAlchemy model
    attrs = inspect(db_target).dict

    return BiologicalTarget(
        id=str(attrs["id"]),
        name=str(attrs["name"]),
        type=str(attrs["type"]),
        organism=str(attrs["organism"]),
        description=str(attrs["description"]) if attrs.get("description") else None,
        uniprot_id=str(attrs["uniprot_id"]) if attrs.get("uniprot_id") else None,
        chembl_id=str(attrs["chembl_id"]) if attrs.get("chembl_id") else None,
        compounds=[c for c in db_target.compounds],
    )
