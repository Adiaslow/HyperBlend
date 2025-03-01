# tests/conftest.py

"""Test configuration and fixtures for the HyperBlend test suite."""

import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
)

from hyperblend.interfaces.api.main import app, get_db
from hyperblend.infrastructure.repositories.models import (
    Base,
    Compound,
    Source,
    BiologicalTarget,
    compound_sources,
    compound_targets,
)

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create async engine for testing
engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=True,
    future=True,
    poolclass=None,  # Disable connection pooling for tests
)

# Create async session factory
TestingSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def pytest_configure(config):
    """Configure pytest-asyncio default settings."""
    config.option.asyncio_mode = "strict"
    config.option.asyncio_default_fixture_loop_scope = "function"


# Mark all tests in this module as requiring asyncio
pytestmark = pytest.mark.asyncio(loop_scope="function")


@pytest_asyncio.fixture(scope="function")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Yield the SQLAlchemy engine, recreating tables for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Get a TestingSessionLocal instance that rolls back after each test."""
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.rollback()
        finally:
            await session.close()


@pytest.fixture
def client(db_engine) -> Generator[TestClient, None, None]:
    """Get a TestClient instance."""

    async def override_get_db():
        async with TestingSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
