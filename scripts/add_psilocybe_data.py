# scripts/add_psilocybe_data.py
"""Script to add psilocybin, psilocin, and their fungal sources to the database.

This script populates the database with:
1. Compounds: psilocybin and psilocin
2. Sources: Various psilocybin-containing mushrooms across different families
3. Targets: Serotonin receptors and their binding data
4. Relationships: Compound-source and compound-target associations
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import insert
from hyperblend.config import settings
from hyperblend.infrastructure.repositories.models.base import Base
from hyperblend.infrastructure.repositories.models.compounds import Compound
from hyperblend.infrastructure.repositories.models.sources import Source
from hyperblend.infrastructure.repositories.models.targets import BiologicalTarget
from hyperblend.infrastructure.repositories.models import (
    compound_sources,
    compound_targets,
)

# Database configuration
engine = create_async_engine(settings.DATABASE_URL, echo=True)
SessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

# Data to be added
COMPOUNDS = [
    {
        "id": "psilocin",
        "name": "Psilocin",
        "molecular_formula": "C12H16N2O",
        "molecular_weight": 204.27,
        "smiles": "CN(C)CCc1c[nH]c2cccc(O)c12",
        "pubchem_id": "4980",
        "chembl_id": "CHEMBL1200374",
    },
    {
        "id": "psilocybin",
        "name": "Psilocybin",
        "molecular_formula": "C12H17N2O4P",
        "molecular_weight": 284.25,
        "smiles": "CN(C)CCc1c[nH]c2cccc(OP(=O)(O)O)c12",
        "pubchem_id": "4980",
        "chembl_id": "CHEMBL1200374",
    },
]

# ... existing code ...
