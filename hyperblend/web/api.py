# hyperblend/web/api.py
"""FastAPI service for the HyperBlend system."""

from typing import List, Optional, AsyncGenerator
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from ..config import settings
from ..domain.models.compounds import Compound
from ..domain.models.sources import Source
from ..domain.models.targets import BiologicalTarget
from ..application.services.graph_service import GraphService, GraphAnalysisResult
from ..infrastructure.repositories.models.base import Base
from ..infrastructure.repositories.sqlalchemy_repositories import (
    SQLAlchemyCompoundRepository,
    SQLAlchemySourceRepository,
    SQLAlchemyTargetRepository,
)
from ..infrastructure.repositories.models.compounds import Compound as CompoundModel


# Pydantic models for API responses
class CompoundResponse(BaseModel):
    """Pydantic model for compound responses."""

    id: str
    name: str
    smiles: Optional[str] = None
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    description: Optional[str] = None
    pubchem_id: Optional[str] = None
    chembl_id: Optional[str] = None
    last_updated: datetime

    model_config = {"from_attributes": True}


class SourceResponse(BaseModel):
    """Pydantic model for source responses."""

    id: str
    name: str
    type: str
    common_names: Optional[List[str]] = None
    description: Optional[str] = None
    native_regions: Optional[List[str]] = None
    traditional_uses: Optional[List[str]] = None

    model_config = {"from_attributes": True}


class BiologicalTargetResponse(BaseModel):
    """Pydantic model for biological target responses."""

    id: str
    name: str
    type: str
    organism: str
    description: Optional[str] = None
    uniprot_id: Optional[str] = None
    chembl_id: Optional[str] = None

    model_config = {"from_attributes": True}


# Set up templates and static files
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Create FastAPI app
app = FastAPI(
    title="HyperBlend",
    description="Advanced botanical medicine analysis using hypergraph networks",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and set up templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Database configuration
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True,
)

# Create async session factory
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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    async with SessionLocal() as session:
        yield session


@app.get("/")
async def root(request: Request):
    """Render the main page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/compounds", response_model=List[CompoundResponse])
async def list_compounds(session: AsyncSession = Depends(get_db)) -> List[Compound]:
    """List all compounds."""
    repo = SQLAlchemyCompoundRepository(session)
    return await repo.list()


@app.get("/sources", response_model=List[SourceResponse])
async def list_sources(session: AsyncSession = Depends(get_db)) -> List[Source]:
    """List all sources."""
    repo = SQLAlchemySourceRepository(session)
    return await repo.list()


@app.get("/targets", response_model=List[BiologicalTargetResponse])
async def list_targets(
    session: AsyncSession = Depends(get_db),
) -> List[BiologicalTarget]:
    """List all biological targets."""
    repo = SQLAlchemyTargetRepository(session)
    return await repo.list()


@app.get("/sources/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: str,
    session: AsyncSession = Depends(get_db),
) -> Source:
    """Get source by ID."""
    repo = SQLAlchemySourceRepository(session)
    source = await repo.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@app.get("/compounds/{compound_id}", response_model=CompoundResponse)
async def get_compound(
    compound_id: str,
    session: AsyncSession = Depends(get_db),
) -> Compound:
    """Get compound by ID."""
    repo = SQLAlchemyCompoundRepository(session)
    compound = await repo.get(compound_id)
    if not compound:
        raise HTTPException(status_code=404, detail="Compound not found")
    return compound


@app.get("/targets/{target_id}", response_model=BiologicalTargetResponse)
async def get_target(
    target_id: str,
    session: AsyncSession = Depends(get_db),
) -> BiologicalTarget:
    """Get target by ID."""
    repo = SQLAlchemyTargetRepository(session)
    target = await repo.get(target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return target


@app.get(
    "/compounds/{compound_id}/targets", response_model=List[BiologicalTargetResponse]
)
async def get_compound_targets(
    compound_id: str, session: AsyncSession = Depends(get_db)
) -> List[BiologicalTarget]:
    """Get all targets for a specific compound."""
    stmt = (
        select(CompoundModel)
        .options(selectinload(CompoundModel.targets))
        .where(CompoundModel.id == compound_id)
    )
    result = await session.execute(stmt)
    db_compound = result.scalar_one_or_none()

    if not db_compound:
        raise HTTPException(status_code=404, detail="Compound not found")

    return db_compound.targets


@app.get("/compounds/{compound_id}/sources", response_model=List[SourceResponse])
async def get_compound_sources(
    compound_id: str, session: AsyncSession = Depends(get_db)
) -> List[Source]:
    """Get all sources for a specific compound."""
    stmt = (
        select(CompoundModel)
        .options(selectinload(CompoundModel.sources))
        .where(CompoundModel.id == compound_id)
    )
    result = await session.execute(stmt)
    db_compound = result.scalar_one_or_none()

    if not db_compound:
        raise HTTPException(status_code=404, detail="Compound not found")

    return db_compound.sources
