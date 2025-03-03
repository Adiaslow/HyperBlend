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

from hyperblend_old.infrastructure.repositories.models.base import Base


class CompoundSynonym(Base):
    """SQLAlchemy model for compound synonyms."""

    __tablename__ = "compound_synonyms"

    id = Column(String, primary_key=True)
    compound_id = Column(String, ForeignKey("compounds.id"), nullable=False)
    name = Column(String, nullable=False, index=True)
    source = Column(String)  # e.g., 'PubChem', 'ChEMBL', 'IUPAC'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship back to compound
    compound = relationship("Compound", back_populates="synonyms")

    __table_args__ = ({"extend_existing": True},)


class Compound(Base):
    """SQLAlchemy model for compounds."""

    __tablename__ = "compounds"

    id = Column(String, primary_key=True, unique=True)
    name = Column(String, nullable=False)
    canonical_name = Column(String, index=True)
    smiles = Column(String)
    molecular_formula = Column(String)
    molecular_weight = Column(Float)
    description = Column(String)

    # External data
    pubchem_id = Column(String, unique=True)
    chembl_id = Column(String, unique=True)
    napralert_id = Column(String, unique=True)  # NAPRALERT database ID
    pubchem_data = Column(JSON)
    chembl_data = Column(JSON)
    napralert_data = Column(JSON)  # Additional data from NAPRALERT
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sources = relationship(
        "Source", secondary="compound_sources", back_populates="compounds"
    )
    targets = relationship(
        "BiologicalTarget", secondary="compound_targets", back_populates="compounds"
    )
    synonyms = relationship(
        "CompoundSynonym", back_populates="compound", cascade="all, delete-orphan"
    )

    __table_args__ = ({"extend_existing": True},)
