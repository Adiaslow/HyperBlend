# hyperblend/web/api.py
"""FastAPI service for the HyperBlend system."""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from neo4j import AsyncDriver, AsyncGraphDatabase

from ..core.config import settings
from ..domain.models import Compound, Source, Target, TargetType
from ..domain.services import CompoundService, SourceService, TargetService
from ..infrastructure.neo4j import (
    Neo4jCompoundRepository,
    Neo4jSourceRepository,
    Neo4jTargetRepository,
)
from ..infrastructure.enriched_data_provider import EnrichedDataProvider


# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format=settings.LOG_FORMAT,
)
logger = logging.getLogger(__name__)


# Pydantic models for API responses
class CompoundResponse(BaseModel):
    """Pydantic model for compound responses."""

    id: str
    name: str
    canonical_name: str
    smiles: Optional[str] = None
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    description: Optional[str] = None
    pubchem_id: Optional[str] = None
    chembl_id: Optional[str] = None
    coconut_id: Optional[str] = None

    model_config = {"from_attributes": True}


class SourceResponse(BaseModel):
    """Pydantic model for source responses."""

    id: str
    name: str
    type: str
    common_names: List[str]
    description: Optional[str] = None
    native_regions: List[str]
    traditional_uses: List[str]
    kingdom: Optional[str] = None
    division: Optional[str] = None
    class_name: Optional[str] = None
    order: Optional[str] = None
    family: Optional[str] = None
    genus: Optional[str] = None
    species: Optional[str] = None

    model_config = {"from_attributes": True}


class TargetResponse(BaseModel):
    """Pydantic model for target responses."""

    id: str
    name: str
    standardized_name: str
    type: str
    organism: str
    description: Optional[str] = None
    uniprot_id: Optional[str] = None
    chembl_id: Optional[str] = None
    gene_id: Optional[str] = None
    gene_name: Optional[str] = None

    model_config = {"from_attributes": True}


# Set up templates and static files
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Neo4j driver and data provider
driver: Optional[AsyncDriver] = None
data_provider = EnrichedDataProvider()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the FastAPI application."""
    global driver
    logger.info("Initializing Neo4j driver...")
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )
    yield
    if driver:
        logger.info("Closing Neo4j driver...")
        await driver.close()


# Create FastAPI app
app = FastAPI(title="HyperBlend API", lifespan=lifespan)

# Configure CORS with specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to responses."""
    response = await call_next(request)
    headers = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob: "
            "https://cdnjs.cloudflare.com https://unpkg.com "
            "https://fonts.googleapis.com https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' http://localhost:* http://127.0.0.1:* "
            "https://*.ncbi.nlm.nih.gov https://*.ebi.ac.uk "
            "https://*.naturalproducts.net https://*.uniprot.org "
            "https://unpkg.com; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdnjs.cloudflare.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com;"
        ),
        # Remove COEP headers as they're causing issues with unpkg.com
        # "Cross-Origin-Embedder-Policy": "require-corp",
        # "Cross-Origin-Opener-Policy": "same-origin",
        # "Cross-Origin-Resource-Policy": "same-site",
    }
    for key, value in headers.items():
        response.headers[key] = value
    return response


# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


async def get_compound_service() -> CompoundService:
    """Get compound service instance."""
    if not driver:
        raise HTTPException(status_code=503, detail="Database connection not available")
    return CompoundService(Neo4jCompoundRepository(driver))


async def get_source_service() -> SourceService:
    """Get source service instance."""
    if not driver:
        raise HTTPException(status_code=503, detail="Database connection not available")
    return SourceService(Neo4jSourceRepository(driver))


async def get_target_service() -> TargetService:
    """Get target service instance."""
    if not driver:
        raise HTTPException(status_code=503, detail="Database connection not available")
    return TargetService(Neo4jTargetRepository(driver))


@app.get("/")
async def root(request: Request):
    """Serve the main application page."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "base_url": str(request.base_url).rstrip("/"),
        },
    )


@app.get("/compounds", response_model=List[CompoundResponse])
async def list_compounds(
    service: CompoundService = Depends(get_compound_service),
) -> List[Compound]:
    """List all compounds."""
    logger.info("Retrieving compounds from Neo4j...")
    compounds = await service._repository.get_all()
    logger.info(f"Retrieved {len(compounds)} compounds")
    return compounds


@app.get("/sources", response_model=List[SourceResponse])
async def list_sources(
    service: SourceService = Depends(get_source_service),
) -> List[Source]:
    """List all sources."""
    logger.info("Retrieving sources from Neo4j...")
    sources = await service._repository.get_all()
    logger.info(f"Retrieved {len(sources)} sources")
    return sources


@app.get("/targets", response_model=List[TargetResponse])
async def list_targets(
    service: TargetService = Depends(get_target_service),
) -> List[Target]:
    """List all targets."""
    logger.info("Retrieving targets from Neo4j...")
    targets = await service._repository.get_all()
    logger.info(f"Retrieved {len(targets)} targets")
    return targets


@app.get("/sources/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: str,
    service: SourceService = Depends(get_source_service),
) -> Source:
    """Get source by ID."""
    source = await service.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@app.get("/compounds/{compound_id}", response_model=CompoundResponse)
async def get_compound(
    compound_id: str,
    service: CompoundService = Depends(get_compound_service),
) -> Compound:
    """Get compound by ID."""
    compound = await service.get(compound_id)
    if not compound:
        raise HTTPException(status_code=404, detail="Compound not found")
    return compound


@app.get("/targets/{target_id}", response_model=TargetResponse)
async def get_target(
    target_id: str,
    service: TargetService = Depends(get_target_service),
) -> Target:
    """Get target by ID."""
    target = await service.get(target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return target


@app.get("/compounds/{compound_id}/targets", response_model=List[str])
async def get_compound_targets(
    compound_id: str,
    service: CompoundService = Depends(get_compound_service),
) -> List[str]:
    """Get IDs of targets that interact with a compound."""
    return await service.get_targets(compound_id)


@app.get("/compounds/{compound_id}/sources", response_model=List[str])
async def get_compound_sources(
    compound_id: str,
    service: CompoundService = Depends(get_compound_service),
) -> List[str]:
    """Get IDs of sources that contain a compound."""
    return await service.get_sources(compound_id)


@app.get("/targets/{target_id}/compounds", response_model=List[str])
async def get_target_compounds(
    target_id: str,
    service: TargetService = Depends(get_target_service),
) -> List[str]:
    """Get IDs of compounds that interact with a target."""
    return await service.get_compounds(target_id)


@app.get("/sources/{source_id}/compounds", response_model=List[str])
async def get_source_compounds(
    source_id: str,
    service: SourceService = Depends(get_source_service),
) -> List[str]:
    """Get IDs of compounds found in a source."""
    return await service.get_compounds(source_id)


@app.post("/admin/enrich")
async def enrich_data(
    service: CompoundService = Depends(get_compound_service),
) -> Dict[str, Any]:
    """Enrich data from external sources and store in database."""
    try:
        logger.info("Starting data enrichment process...")

        # Load and enrich data
        enriched_compounds, sources, targets = await data_provider.load_enriched_data()
        logger.info(
            f"Loaded and enriched {len(enriched_compounds)} compounds, "
            f"found {len(targets)} targets"
        )

        # Store in database
        async with service._repository._driver.session() as session:
            # Clear existing data
            await session.run("MATCH (n) DETACH DELETE n")

            # Store compounds
            for compound in enriched_compounds:
                await service.create(compound)

            # Store sources
            source_service = SourceService(
                Neo4jSourceRepository(service._repository._driver)
            )
            for source in sources:
                await source_service.create(source)

            # Store targets
            target_service = TargetService(
                Neo4jTargetRepository(service._repository._driver)
            )
            for target in targets:
                await target_service.create(target)

            # Create relationships
            for compound_id, target_ids in data_provider._compound_targets.items():
                for target_id in target_ids:
                    await session.run(
                        """
                        MATCH (c:Compound {id: $compound_id})
                        MATCH (t:Target {id: $target_id})
                        MERGE (c)-[:INTERACTS_WITH]->(t)
                        """,
                        compound_id=compound_id,
                        target_id=target_id,
                    )

            # Create source-compound relationships
            source_compound_count = 0
            for (
                source_id,
                compound_ids,
            ) in data_provider.base_provider._source_compounds.items():
                for compound_id in compound_ids:
                    await session.run(
                        """
                        MATCH (s:Source {id: $source_id})
                        MATCH (c:Compound {id: $compound_id})
                        MERGE (s)-[:CONTAINS]->(c)
                        """,
                        source_id=source_id,
                        compound_id=compound_id,
                    )
                    source_compound_count += 1

        return {
            "status": "success",
            "compounds_enriched": len(enriched_compounds),
            "sources_stored": len(sources),
            "targets_found": len(targets),
            "compound_target_relationships": sum(
                len(targets) for targets in data_provider._compound_targets.values()
            ),
            "source_compound_relationships": source_compound_count,
        }

    except Exception as e:
        logger.error(f"Error during data enrichment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error during data enrichment: {str(e)}",
        )


@app.post("/admin/load")
async def load_data(
    service: CompoundService = Depends(get_compound_service),
) -> Dict[str, Any]:
    """Load initial data into the database."""
    try:
        logger.info("Starting initial data loading process...")

        # Load data from the base provider
        compounds, sources = await data_provider.base_provider.load_plant_compounds()
        logger.info(f"Loaded {len(compounds)} compounds and {len(sources)} sources")

        # Store in database
        async with service._repository._driver.session() as session:
            # Clear existing data
            await session.run("MATCH (n) DETACH DELETE n")

            # Store compounds
            for compound in compounds:
                await service.create(compound)

            # Store sources
            source_service = SourceService(
                Neo4jSourceRepository(service._repository._driver)
            )
            for source in sources:
                await source_service.create(source)

            # Create source-compound relationships
            source_compound_count = 0
            for (
                source_id,
                compound_ids,
            ) in data_provider.base_provider._source_compounds.items():
                for compound_id in compound_ids:
                    await session.run(
                        """
                        MATCH (s:Source {id: $source_id})
                        MATCH (c:Compound {id: $compound_id})
                        MERGE (s)-[:CONTAINS]->(c)
                        """,
                        source_id=source_id,
                        compound_id=compound_id,
                    )
                    source_compound_count += 1

        return {
            "status": "success",
            "compounds_loaded": len(compounds),
            "sources_loaded": len(sources),
            "source_compound_relationships": source_compound_count,
        }

    except Exception as e:
        logger.error(f"Error during data loading: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error during data loading: {str(e)}",
        )
