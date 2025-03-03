from sqlalchemy import Column, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime

from hyperblend_old.models.base import Base

compound_sources = Table(
    "compound_sources",
    Base.metadata,
    Column("compound_id", String, ForeignKey("compounds.id"), nullable=False),
    Column("source_id", String, ForeignKey("sources.id"), nullable=False),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("last_updated", DateTime, nullable=False, default=datetime.utcnow),
    __table_args__=(
        {"sqlite_on_conflict": "IGNORE"},
        {"extend_existing": True},
        {"primary_key": ("compound_id", "source_id")},
    ),
)


class Source(Base):
    """Model representing a data source."""

    __tablename__ = "sources"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    url = Column(String)
    description = Column(String)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)

    compounds = relationship(
        "Compound", secondary=compound_sources, back_populates="sources"
    )
