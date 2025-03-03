"""SQLAlchemy models for HyperBlend."""

from sqlalchemy import Table, Column, String, ForeignKey, Float
from hyperblend_old.infrastructure.repositories.models.base import Base
from hyperblend_old.infrastructure.repositories.models.compounds import Compound
from hyperblend_old.infrastructure.repositories.models.sources import Source
from hyperblend_old.infrastructure.repositories.models.targets import BiologicalTarget

# Association tables
compound_sources = Table(
    "compound_sources",
    Base.metadata,
    Column("compound_id", String, ForeignKey("compounds.id"), primary_key=True),
    Column("source_id", String, ForeignKey("sources.id"), primary_key=True),
)

compound_targets = Table(
    "compound_targets",
    Base.metadata,
    Column("compound_id", String, ForeignKey("compounds.id"), primary_key=True),
    Column("target_id", String, ForeignKey("biological_targets.id"), primary_key=True),
    Column("action", String),  # Description of the interaction
    Column("action_type", String),  # Type of measurement (e.g., pEC50)
    Column("action_value", Float),  # Numerical value of the measurement
    Column("evidence", String),  # Evidence references (e.g., PMID)
    Column("evidence_urls", String),  # URLs to evidence sources
)

__all__ = [
    "Base",
    "Compound",
    "Source",
    "BiologicalTarget",
    "compound_sources",
    "compound_targets",
]
