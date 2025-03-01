# scripts/add_sceletium_data.py
"""Script to add Sceletium tortuosum data to the database."""

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
        "id": "mesembrine",
        "name": "Mesembrine",
        "molecular_formula": "C17H23NO3",
        "molecular_weight": 289.4,
        "smiles": "CN1CCC2(C1CC(=O)CC2)C3=CC(=C(C=C3)OC)OC",
        "pubchem_id": "394162",
        "chembl_id": "CHEMBL1976871",
    },
    {
        "id": "mesembrenone",
        "name": "Mesembrenone",
        "molecular_formula": "C17H21NO3",
        "molecular_weight": 287.35,
        "smiles": "CN1CCC2(C1CC(=O)C=C2)C3=CC(=C(C=C3)OC)OC",
        "pubchem_id": "216272",
        "chembl_id": "CHEMBL4781238",
    },
    {
        "id": "mesembrenol",
        "name": "Mesembrenol",
        "molecular_formula": "C17H23NO3",
        "molecular_weight": 289.4,
        "smiles": "CN1CCC2(C1CC(C=C2)O)C3=CC(=C(C=C3)OC)OC",
        "pubchem_id": "46898090",
    },
    {
        "id": "mesembranol",
        "name": "Mesembranol",
        "molecular_formula": "C17H25NO3",
        "molecular_weight": 291.39,
        "smiles": "CN1CCC2(C1CC(CC2)O)C3=CC(=C(C=C3)OC)OC",
        "pubchem_id": "625909",
    },
    {
        "id": "delta7_mesembrine",
        "name": "Δ7-Mesembrine",
        "molecular_formula": "C17H21NO3",
        "molecular_weight": 287.35,
    },
    {
        "id": "delta7_mesembrenone",
        "name": "Δ7-Mesembrenone",
        "molecular_formula": "C17H21NO3",
        "molecular_weight": 287.35,
        "smiles": "CN1CCC2(C1=CC(=O)CC2)C3=CC(=C(C=C3)OC)OC",
        "pubchem_id": "11077036",
    },
    {
        "id": "epimesembranol",
        "name": "Epimesembranol",
        "molecular_formula": "C17H25NO3",
        "molecular_weight": 291.39,
    },
    {
        "id": "epimesembrenol",
        "name": "Epimesembrenol",
        "molecular_formula": "C17H23NO3",
        "molecular_weight": 289.37,
    },
    {
        "id": "mesembrane",
        "name": "Mesembrane",
        "molecular_formula": "C17H25NO2",
        "molecular_weight": 275.39,
        "smiles": "CN1CCC2(C1CCCC2)C3=CC(=C(C=C3)OC)OC",
        "pubchem_id": "10989483",
    },
    {
        "id": "tortuosamine",
        "name": "Tortuosamine",
        "molecular_formula": "C20H26N2O2",
        "molecular_weight": 326.4,
        "smiles": "CNCCC1(CCC2=C(C1)C=CC=N2)C3=CC(=C(C=C3)OC)OC",
        "pubchem_id": "101324747",
    },
    {
        "id": "channaine",
        "name": "Channaine",
        "molecular_formula": "C32H38N2O6",
        "molecular_weight": 546.7,
        "smiles": "COC1=C(C=C(C=C1)C23CCNC2CC45C(=C3)C6CC(O4)(CC7C6(CCN57)C8=CC(=C(C=C8)OC)OC)O)OC",
        "pubchem_id": "51136501",
    },
    {"id": "sceletorine_a", "name": "Sceletorine A"},
    {"id": "sceletorine_b", "name": "Sceletorine B"},
]

SOURCES = [
    {
        "id": "sceletium_tortuosum",
        "name": "Kanna",
        "type": "PLANT",
        "description": "Succulent plant endemic to South Africa, traditionally used for medicinal purposes. Contains mesembrine-type alkaloids and other compounds with psychoactive properties.",
    }
]

TARGETS = [
    {
        "id": "sert",
        "name": "Serotonin Transporter",
        "type": "PROTEIN",
        "description": "SERT inhibition",
        "organism": "Homo sapiens",
        "chembl_id": "CHEMBL228",
    },
    {
        "id": "pde4",
        "name": "Phosphodiesterase-4",
        "type": "ENZYME",
        "description": "PDE-4 inhibition",
        "organism": "Homo sapiens",
        "chembl_id": "CHEMBL288",
    },
    {
        "id": "vmat2",
        "name": "Vesicular Monoamine Transporter-2",
        "type": "PROTEIN",
        "description": "Upregulates VMAT-2",
        "organism": "Homo sapiens",
        "chembl_id": "CHEMBL1293224",
    },
    {
        "id": "ache",
        "name": "Acetylcholinesterase",
        "type": "ENZYME",
        "description": "Mild inhibition of AChE",
        "organism": "Homo sapiens",
        "chembl_id": "CHEMBL220",
    },
    {
        "id": "mao_a",
        "name": "Monoamine Oxidase-A",
        "type": "ENZYME",
        "description": "Mild inhibition of MAO-A",
        "organism": "Homo sapiens",
        "chembl_id": "CHEMBL1951",
    },
    {
        "id": "gaba_receptors",
        "name": "GABA Receptors",
        "type": "RECEPTOR",
        "description": "Affected by Sceletium tortuosum compounds at high doses",
        "organism": "Homo sapiens",
    },
    {
        "id": "delta2_opioid",
        "name": "δ2-Opioid Receptor",
        "type": "RECEPTOR",
        "description": "Affected by Sceletium tortuosum compounds at high doses",
        "organism": "Homo sapiens",
    },
    {
        "id": "mu_opioid",
        "name": "μ-Opioid Receptor",
        "type": "RECEPTOR",
        "description": "Affected by Sceletium tortuosum compounds at high doses",
        "organism": "Homo sapiens",
    },
    {
        "id": "cck1",
        "name": "Cholecystokinin-1 Receptor",
        "type": "RECEPTOR",
        "description": "Target of Sceletium tortuosum compounds",
        "organism": "Homo sapiens",
    },
    {
        "id": "mt1",
        "name": "Melatonin-1 Receptor",
        "type": "RECEPTOR",
        "description": "Target of Sceletium tortuosum compounds",
        "organism": "Homo sapiens",
    },
    {
        "id": "ep4",
        "name": "EP4 Prostaglandin Receptor",
        "type": "RECEPTOR",
        "description": "Target of Sceletium tortuosum compounds",
        "organism": "Homo sapiens",
    },
    {
        "id": "ampa",
        "name": "AMPA Receptor",
        "type": "RECEPTOR",
        "description": "α-amino-3-hydroxy-5-methyl-4-isoxazolepropionic acid receptor, target of Sceletium tortuosum compounds",
        "organism": "Homo sapiens",
    },
]

# Relationships - all compounds are from Sceletium tortuosum
COMPOUND_SOURCES = [(compound["id"], "sceletium_tortuosum") for compound in COMPOUNDS]

# Known compound-target relationships based on the literature
COMPOUND_TARGETS = [
    # Mesembrine relationships
    ("mesembrine", "sert"),  # SERT inhibition
    ("mesembrine", "pde4"),  # PDE-4 inhibition
    ("mesembrine", "vmat2"),  # Upregulates VMAT-2
    ("mesembrine", "ache"),  # Mild inhibition of AChE
    ("mesembrine", "mao_a"),  # Mild inhibition of MAO-A
    # Mesembrenone relationships
    ("mesembrenone", "sert"),  # SERT inhibition
    ("mesembrenone", "pde4"),  # PDE-4 inhibition
    # Mesembrenol relationships
    ("mesembrenol", "sert"),  # SERT inhibition
    ("mesembrenol", "pde4"),  # PDE-4 inhibition
]


async def init_db():
    """Initialize the database by dropping all tables and recreating them."""
    async with engine.begin() as conn:
        # Drop all tables
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def add_data():
    """Add the Sceletium tortuosum data to the database."""
    async with SessionLocal() as session:
        # Add sources
        for source_data in SOURCES:
            source = Source(**source_data)
            session.add(source)

        # Add compounds
        for compound_data in COMPOUNDS:
            compound = Compound(**compound_data)
            session.add(compound)

        # Add targets
        for target_data in TARGETS:
            target = BiologicalTarget(**target_data)
            session.add(target)

        await session.commit()

        # Add compound-source relationships
        await session.execute(
            insert(compound_sources),
            [
                {"compound_id": c_id, "source_id": s_id}
                for c_id, s_id in COMPOUND_SOURCES
            ],
        )

        # Add compound-target relationships
        await session.execute(
            insert(compound_targets),
            [
                {"compound_id": c_id, "target_id": t_id}
                for c_id, t_id in COMPOUND_TARGETS
            ],
        )

        await session.commit()


async def main():
    """Main function to run the script."""
    await init_db()
    await add_data()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
