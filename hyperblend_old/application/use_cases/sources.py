"""Use cases for managing sources."""

from typing import List, Optional, Dict, Any, cast
from sqlalchemy.orm import Session
from sqlalchemy import inspect

from hyperblend_old.domain.models import Source
from hyperblend_old.infrastructure.repositories.models import Source as SourceModel


def create_source(db: Session, source_data: Dict[str, Any]) -> Source:
    """Create a new source."""
    db_source = SourceModel(**source_data)
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return _to_domain(db_source)


def update_source(
    db: Session, source_id: str, source_data: Dict[str, Any]
) -> Optional[Source]:
    """Update an existing source."""
    db_source = db.query(SourceModel).filter(SourceModel.id == source_id).first()
    if not db_source:
        return None

    for key, value in source_data.items():
        setattr(db_source, key, value)

    db.commit()
    db.refresh(db_source)
    return _to_domain(db_source)


def delete_source(db: Session, source_id: str) -> bool:
    """Delete a source."""
    db_source = db.query(SourceModel).filter(SourceModel.id == source_id).first()
    if not db_source:
        return False

    db.delete(db_source)
    db.commit()
    return True


def get_source(db: Session, source_id: str) -> Optional[Source]:
    """Get a source by ID."""
    db_source = db.query(SourceModel).filter(SourceModel.id == source_id).first()
    if not db_source:
        return None
    return _to_domain(db_source)


def list_sources(db: Session, skip: int = 0, limit: int = 100) -> List[Source]:
    """List all sources."""
    db_sources = db.query(SourceModel).offset(skip).limit(limit).all()
    return [_to_domain(s) for s in db_sources]


def search_sources(
    db: Session,
    name: Optional[str] = None,
    type: Optional[str] = None,
) -> List[Source]:
    """Search for sources by various criteria."""
    query = db.query(SourceModel)
    if name:
        query = query.filter(SourceModel.name.ilike(f"%{name}%"))
    if type:
        query = query.filter(SourceModel.type == type)
    return [_to_domain(s) for s in query.all()]


def _to_domain(db_source: SourceModel) -> Source:
    """Convert a database model to a domain model."""
    # Get the actual values from the SQLAlchemy model
    attrs = inspect(db_source).dict

    return Source(
        id=str(attrs["id"]),
        name=str(attrs["name"]),
        type=str(attrs["type"]),
        common_names=cast(Optional[List[str]], attrs.get("common_names")),
        description=str(attrs["description"]) if attrs.get("description") else None,
        native_regions=cast(Optional[List[str]], attrs.get("native_regions")),
        traditional_uses=cast(Optional[List[str]], attrs.get("traditional_uses")),
        compounds=[c for c in db_source.compounds],
    )
