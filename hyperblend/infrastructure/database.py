"""Database configuration and session management."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from hyperblend.infrastructure.repositories.models.base import Base

# Create SQLite database engine with in-memory persistence
engine = create_engine(
    "sqlite:///hyperblend.db",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create all tables
Base.metadata.create_all(bind=engine)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get a database session.

    This function is used as a FastAPI dependency to get a database session
    for each request.

    Returns:
        SQLAlchemy session generator
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
