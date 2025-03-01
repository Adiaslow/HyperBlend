"""SQLAlchemy models for compound-related entities."""

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    JSON,
    ForeignKey,
    Table,
    DateTime,
    Boolean,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from hyperblend.infrastructure.repositories.models.base import Base


class Compound(Base):
    """SQLAlchemy model for compounds."""

    __tablename__ = "compounds"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    smiles = Column(String)
    molecular_formula = Column(String)
    molecular_weight = Column(Float)
    description = Column(String)

    # External data
    pubchem_id = Column(String, unique=True, index=True)
    chembl_id = Column(String, unique=True, index=True)
    pubchem_data = Column(JSON)
    chembl_data = Column(JSON)
    last_updated = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sources = relationship(
        "Source", secondary="compound_sources", back_populates="compounds"
    )
    targets = relationship(
        "BiologicalTarget", secondary="compound_targets", back_populates="compounds"
    )
