# tests/test_api.py

"""Test suite for the HyperBlend API endpoints."""

import pytest
from typing import Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from hyperblend.infrastructure.repositories.models.compounds import Compound
from hyperblend.infrastructure.repositories.models.sources import Source
from hyperblend.infrastructure.repositories.models.targets import BiologicalTarget


# Mark all tests in this module as requiring asyncio
pytestmark = pytest.mark.asyncio(loop_scope="function")


async def test_list_compounds_empty(
    client: TestClient, db_session: AsyncSession
) -> None:
    """Test listing compounds when database is empty."""
    response = client.get("/compounds")
    assert response.status_code == 200
    assert response.json() == []


async def test_create_and_get_compound(
    client: TestClient, db_session: AsyncSession
) -> None:
    """Test creating and retrieving a compound."""
    # Create test data
    compound_data = {
        "id": "COMPOUND1",
        "name": "Test Compound",
        "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        "molecular_weight": 180.159,
        "molecular_formula": "C9H8O4",
        "pubchem_cid": "2244",
        "chembl_id": "CHEMBL25",
    }

    # Create compound
    response = client.post("/compounds", json=compound_data)
    assert response.status_code == 201
    created_compound = response.json()
    assert created_compound["id"] == compound_data["id"]
    assert created_compound["name"] == compound_data["name"]

    # Get compound
    response = client.get(f"/compounds/{compound_data['id']}")
    assert response.status_code == 200
    retrieved_compound = response.json()
    assert retrieved_compound == created_compound


async def test_get_nonexistent_compound(
    client: TestClient, db_session: AsyncSession
) -> None:
    """Test getting a compound that doesn't exist."""
    response = client.get("/compounds/NONEXISTENT")
    assert response.status_code == 404


async def test_list_compounds(client: TestClient, db_session: AsyncSession) -> None:
    """Test listing multiple compounds."""
    # Create test compounds
    compounds = [
        {
            "id": "COMPOUND2",
            "name": "Test Compound 2",
            "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "molecular_weight": 180.159,
            "molecular_formula": "C9H8O4",
            "pubchem_cid": "2244",
            "chembl_id": "CHEMBL26",
        },
        {
            "id": "COMPOUND3",
            "name": "Test Compound 3",
            "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
            "molecular_weight": 194.194,
            "molecular_formula": "C8H10N4O2",
            "pubchem_cid": "2519",
            "chembl_id": "CHEMBL113",
        },
    ]

    # Create compounds
    for compound_data in compounds:
        response = client.post("/compounds", json=compound_data)
        assert response.status_code == 201

    # List compounds
    response = client.get("/compounds")
    assert response.status_code == 200
    listed_compounds = response.json()
    assert len(listed_compounds) >= len(
        compounds
    )  # Use >= since there might be compounds from other tests
    assert all(c["id"] in [lc["id"] for lc in listed_compounds] for c in compounds)


async def test_list_sources(client: TestClient, db_session: AsyncSession) -> None:
    """Test listing sources."""
    # Create test source
    source_data = {
        "id": "SOURCE1",
        "name": "Test Source",
        "type": "plant",
        "common_names": ["Common Name 1", "Common Name 2"],
        "description": "Test description",
        "native_regions": ["Region 1", "Region 2"],
        "traditional_uses": ["Use 1", "Use 2"],
    }

    response = client.post("/sources", json=source_data)
    assert response.status_code == 201

    # List sources
    response = client.get("/sources")
    assert response.status_code == 200
    sources = response.json()
    assert len(sources) == 1
    assert sources[0]["id"] == source_data["id"]


async def test_get_source_compounds(
    client: TestClient, db_session: AsyncSession
) -> None:
    """Test getting compounds associated with a source."""
    # Create test source and compound
    source_data = {
        "id": "SOURCE2",
        "name": "Test Source 2",
        "type": "plant",
        "common_names": ["Common Name 1"],
        "description": "Test description",
        "native_regions": ["Region 1"],
        "traditional_uses": ["Use 1"],
    }

    compound_data = {
        "id": "COMPOUND4",
        "name": "Test Compound 4",
        "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        "molecular_weight": 180.159,
        "molecular_formula": "C9H8O4",
        "pubchem_cid": "2244",
        "chembl_id": "CHEMBL27",
    }

    # Create source and compound
    response = client.post("/sources", json=source_data)
    assert response.status_code == 201

    response = client.post("/compounds", json=compound_data)
    assert response.status_code == 201

    # Associate compound with source
    response = client.post(
        f"/sources/{source_data['id']}/compounds/{compound_data['id']}"
    )
    assert response.status_code == 200

    # Get source compounds
    response = client.get(f"/sources/{source_data['id']}/compounds")
    assert response.status_code == 200
    compounds = response.json()
    assert len(compounds) == 1
    assert compounds[0]["id"] == compound_data["id"]
