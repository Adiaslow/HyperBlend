"""SQLAlchemy model for biological targets."""

from sqlalchemy import Column, String, JSON
from sqlalchemy.orm import relationship

from hyperblend.infrastructure.repositories.models.base import Base


class BiologicalTarget(Base):
    """SQLAlchemy model for biological targets (receptors, enzymes, etc.)."""

    __tablename__ = "biological_targets"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # e.g., "receptor", "enzyme", "transporter"
    description = Column(String)
    organism = Column(String, nullable=False)

    # External identifiers
    uniprot_id = Column(String, unique=True, index=True)
    chembl_id = Column(String, unique=True, index=True)

    # Relationships
    compounds = relationship(
        "Compound", secondary="compound_targets", back_populates="targets"
    )
