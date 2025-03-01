"""SQLAlchemy models for HyperBlend."""

from sqlalchemy import Table, Column, String, ForeignKey
from hyperblend.infrastructure.repositories.models.base import Base
from hyperblend.infrastructure.repositories.models.compounds import Compound
from hyperblend.infrastructure.repositories.models.sources import Source
from hyperblend.infrastructure.repositories.models.targets import BiologicalTarget

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
)

__all__ = [
    "Base",
    "Compound",
    "Source",
    "BiologicalTarget",
    "compound_sources",
    "compound_targets",
]
