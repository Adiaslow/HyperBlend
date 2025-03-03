"""FastAPI application for the HyperBlend API."""

from typing import List, Optional, AsyncGenerator, Union, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from ...config import Settings, get_settings
from ...domain.models.compounds import Compound
from ...domain.models.sources import Source
from ...domain.models.targets import BiologicalTarget
from ...infrastructure.repositories.models.base import Base
from ...infrastructure.repositories.models.compounds import Compound as CompoundModel
from ...infrastructure.repositories.models.sources import Source as SourceModel
from ...infrastructure.repositories.sqlalchemy_repositories import (
    SQLAlchemyCompoundRepository,
    SQLAlchemySourceRepository,
)
from .schemas import (
    CompoundCreate,
    CompoundRead,
    SourceCreate,
    SourceRead,
    BiologicalTargetRead,
)

# Database configuration
settings = get_settings()
engine = create_async_engine(
    settings.DATABASE_URL,
    **settings.DATABASE_ARGS,
)
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the FastAPI application."""
    # Initialize database on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Clean up on shutdown
    await engine.dispose()


# Initialize FastAPI app
app = FastAPI(
    title="HyperBlend API",
    description="A chemical compound analysis and visualization platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@app.get("/compounds", response_model=List[CompoundRead])
async def list_compounds(db: AsyncSession = Depends(get_db)) -> List[Compound]:
    """List all compounds."""
    repo = SQLAlchemyCompoundRepository(db)
    return await repo.list()


@app.post("/compounds", response_model=CompoundRead, status_code=201)
async def create_compound(
    compound: CompoundCreate, db: AsyncSession = Depends(get_db)
) -> Compound:
    """Create a new compound."""
    repo = SQLAlchemyCompoundRepository(db)
    domain_compound = Compound(**compound.model_dump())
    compound_id = await repo.add(domain_compound)
    result = await repo.get(compound_id)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create compound")
    return result


@app.get("/compounds/{compound_id}", response_model=CompoundRead)
async def get_compound(
    compound_id: str, db: AsyncSession = Depends(get_db)
) -> Compound:
    """Get a compound by ID."""
    repo = SQLAlchemyCompoundRepository(db)
    compound = await repo.get(compound_id)
    if not compound:
        raise HTTPException(status_code=404, detail="Compound not found")
    return compound


@app.get("/sources", response_model=List[SourceRead])
async def list_sources(db: AsyncSession = Depends(get_db)) -> List[Source]:
    """List all sources."""
    repo = SQLAlchemySourceRepository(db)
    return await repo.list()


@app.post("/sources", response_model=SourceRead, status_code=201)
async def create_source(
    source: SourceCreate, db: AsyncSession = Depends(get_db)
) -> Source:
    """Create a new source."""
    repo = SQLAlchemySourceRepository(db)
    domain_source = Source(**source.model_dump())
    source_id = await repo.add(domain_source)
    result = await repo.get(source_id)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create source")
    return result


@app.get("/sources/{source_id}", response_model=SourceRead)
async def get_source(source_id: str, db: AsyncSession = Depends(get_db)) -> Source:
    """Get a source by ID."""
    repo = SQLAlchemySourceRepository(db)
    source = await repo.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@app.get("/sources/{source_id}/compounds", response_model=List[CompoundRead])
async def get_source_compounds(
    source_id: str, db: AsyncSession = Depends(get_db)
) -> List[Compound]:
    """Get compounds associated with a source."""
    source_repo = SQLAlchemySourceRepository(db)
    source = await source_repo.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source.compounds


@app.post("/sources/{source_id}/compounds/{compound_id}", status_code=200)
async def associate_compound_with_source(
    source_id: str, compound_id: str, db: AsyncSession = Depends(get_db)
) -> None:
    """Associate a compound with a source."""
    # Get the SQLAlchemy models directly with eager loading
    stmt = (
        select(SourceModel)
        .options(selectinload(SourceModel.compounds))
        .where(SourceModel.id == source_id)
    )
    result = await db.execute(stmt)
    db_source = result.scalar_one_or_none()
    if not db_source:
        raise HTTPException(status_code=404, detail="Source not found")

    stmt = select(CompoundModel).where(CompoundModel.id == compound_id)
    result = await db.execute(stmt)
    db_compound = result.scalar_one_or_none()
    if not db_compound:
        raise HTTPException(status_code=404, detail="Compound not found")

    # Add the compound to the source's compounds list
    db_source.compounds.append(db_compound)
    await db.commit()


@app.get("/")
async def root() -> Dict[str, Any]:
    """Get API information and available endpoints."""
    return {
        "name": "HyperBlend API",
        "version": app.version,
        "description": app.description,
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
        },
        "endpoints": {
            "compounds": {
                "list": "/compounds",
                "create": "/compounds",
                "get": "/compounds/{compound_id}",
            },
            "sources": {
                "list": "/sources",
                "create": "/sources",
                "get": "/sources/{source_id}",
                "get_compounds": "/sources/{source_id}/compounds",
                "associate_compound": "/sources/{source_id}/compounds/{compound_id}",
            },
        },
    }
