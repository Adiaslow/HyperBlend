"""Use cases for managing compounds."""

from typing import List, Optional, Dict, Any, cast
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import inspect

from hyperblend_old.domain.models import Compound
from hyperblend_old.infrastructure.repositories.models import Compound as CompoundModel


def create_compound(db: Session, compound_data: Dict[str, Any]) -> Compound:
    """Create a new compound."""
    db_compound = CompoundModel(**compound_data)
    db.add(db_compound)
    db.commit()
    db.refresh(db_compound)
    return _to_domain(db_compound)


def update_compound(
    db: Session, compound_id: str, compound_data: Dict[str, Any]
) -> Optional[Compound]:
    """Update an existing compound."""
    db_compound = (
        db.query(CompoundModel).filter(CompoundModel.id == compound_id).first()
    )
    if not db_compound:
        return None

    for key, value in compound_data.items():
        setattr(db_compound, key, value)

    db.commit()
    db.refresh(db_compound)
    return _to_domain(db_compound)


def delete_compound(db: Session, compound_id: str) -> bool:
    """Delete a compound."""
    db_compound = (
        db.query(CompoundModel).filter(CompoundModel.id == compound_id).first()
    )
    if not db_compound:
        return False

    db.delete(db_compound)
    db.commit()
    return True


def get_compound(db: Session, compound_id: str) -> Optional[Compound]:
    """Get a compound by ID."""
    db_compound = (
        db.query(CompoundModel).filter(CompoundModel.id == compound_id).first()
    )
    if not db_compound:
        return None
    return _to_domain(db_compound)


def list_compounds(db: Session, skip: int = 0, limit: int = 100) -> List[Compound]:
    """List all compounds."""
    db_compounds = db.query(CompoundModel).offset(skip).limit(limit).all()
    return [_to_domain(c) for c in db_compounds]


def search_compounds(
    db: Session,
    name: Optional[str] = None,
    smiles: Optional[str] = None,
    pubchem_id: Optional[str] = None,
    chembl_id: Optional[str] = None,
) -> List[Compound]:
    """Search for compounds by various criteria."""
    query = db.query(CompoundModel)
    if name:
        query = query.filter(CompoundModel.name.ilike(f"%{name}%"))
    if smiles:
        query = query.filter(CompoundModel.smiles == smiles)
    if pubchem_id:
        query = query.filter(CompoundModel.pubchem_id == pubchem_id)
    if chembl_id:
        query = query.filter(CompoundModel.chembl_id == chembl_id)
    return [_to_domain(c) for c in query.all()]


def _to_domain(db_compound: CompoundModel) -> Compound:
    """Convert a database model to a domain model."""
    # Get the actual values from the SQLAlchemy model
    attrs = inspect(db_compound).dict

    return Compound(
        id=str(attrs["id"]),
        name=str(attrs["name"]),
        smiles=str(attrs["smiles"]) if attrs.get("smiles") else None,
        molecular_formula=(
            str(attrs["molecular_formula"]) if attrs.get("molecular_formula") else None
        ),
        molecular_weight=(
            float(attrs["molecular_weight"]) if attrs.get("molecular_weight") else None
        ),
        description=str(attrs["description"]) if attrs.get("description") else None,
        pubchem_id=str(attrs["pubchem_id"]) if attrs.get("pubchem_id") else None,
        chembl_id=str(attrs["chembl_id"]) if attrs.get("chembl_id") else None,
        pubchem_data=cast(Optional[Dict[str, Any]], attrs.get("pubchem_data")),
        chembl_data=cast(Optional[Dict[str, Any]], attrs.get("chembl_data")),
        last_updated=cast(datetime, attrs["last_updated"]),
        sources=[s for s in db_compound.sources],
        targets=[t for t in db_compound.targets],
    )
