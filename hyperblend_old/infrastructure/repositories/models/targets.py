"""SQLAlchemy model for biological targets."""

from sqlalchemy import Column, String, JSON, CheckConstraint
from sqlalchemy.orm import relationship

from hyperblend_old.infrastructure.repositories.models.base import Base


class BiologicalTarget(Base):
    """SQLAlchemy model for biological targets (receptors, enzymes, etc.)."""

    __tablename__ = "biological_targets"

    # Class variable for organism value
    HUMAN_ORGANISM = "Homo sapiens"

    id = Column(String, primary_key=True, unique=True)
    name = Column(String, nullable=False)
    standardized_name = Column(String)
    type = Column(String, nullable=False)  # e.g., "receptor", "enzyme", "transporter"
    description = Column(String)
    organism = Column(String, nullable=False)

    # External identifiers
    uniprot_id = Column(String, unique=True, index=True)
    chembl_id = Column(String, unique=True, index=True)
    gene_id = Column(String, index=True)  # NCBI Gene ID
    gene_name = Column(String, index=True)  # Gene symbol/name

    # Relationships
    compounds = relationship(
        "Compound", secondary="compound_targets", back_populates="targets"
    )

    # Add check constraint to ensure only human targets
    __table_args__ = (
        CheckConstraint(f"organism = '{HUMAN_ORGANISM}'", name="check_human_organism"),
    )
