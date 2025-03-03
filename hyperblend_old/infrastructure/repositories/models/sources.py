"""SQLAlchemy model for sources."""

from sqlalchemy import Column, String, JSON
from sqlalchemy.orm import relationship

from hyperblend_old.infrastructure.repositories.models.base import Base


class Source(Base):
    """SQLAlchemy model for sources (plants, fungi, etc.)."""

    __tablename__ = "sources"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # e.g., "plant", "fungus"
    common_names = Column(JSON)  # List of common names
    description = Column(String)
    native_regions = Column(JSON)  # List of regions
    traditional_uses = Column(JSON)  # List of traditional uses
    taxonomy = Column(JSON)  # Taxonomic classification

    # Relationships
    compounds = relationship(
        "Compound", secondary="compound_sources", back_populates="sources"
    )
