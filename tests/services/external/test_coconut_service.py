"""Test script for COCONUT service."""

import os
from hyperblend.services.external.coconut_service import CoconutService
from hyperblend.database import get_graph
from typing import Optional


def test_molecule(service: CoconutService, name: str, smiles: Optional[str] = None):
    """Test molecule search functionality."""
    print(f"\nSearching for {name} in COCONUT...")
    molecules = service.search_molecule_by_name(name)

    if not molecules:
        print("No molecules found by name")
    else:
        print(f"\nFound {len(molecules)} molecules")
        for molecule in molecules:
            print("\nMolecule details:")
            print(f"ID: {molecule.id}")
            print(f"Name: {molecule.name}")
            print(f"Formula: {molecule.formula}")
            print(f"Molecular Weight: {molecule.molecular_weight}")
            print(f"SMILES: {molecule.smiles}")
            print(f"InChI: {molecule.inchi}")
            print(f"InChIKey: {molecule.inchikey}")
            print(f"LogP: {molecule.logp}")
            print(f"Polar Surface Area: {molecule.polar_surface_area}")

    if smiles:
        print(f"\nSearching for molecule by SMILES: {smiles}")
        molecules = service.search_molecule_by_smiles(smiles)

        if molecules:
            print(f"\nFound {len(molecules)} molecules by SMILES")
            for molecule in molecules:
                print(f"\nMolecule name: {molecule.name}")
                print(f"SMILES: {molecule.smiles}")


def test_organism(service: CoconutService, name: str):
    """Test organism search functionality."""
    print(f"\nSearching for organism: {name}")
    organisms = service.search_organisms(name=name)

    if organisms:
        print(f"\nFound {len(organisms)} organisms")
        for organism in organisms:
            print("\nOrganism details:")
            print(f"Name: {organism.get('name')}")
            print(f"Rank: {organism.get('rank')}")
            print(f"Molecule Count: {organism.get('molecule_count')}")
            print(f"IRI: {organism.get('iri')}")
    else:
        print("No organisms found")


def main():
    """Test COCONUT service with multiple compounds and organisms."""
    # Get credentials from environment variables or use defaults
    email = os.getenv("COCONUT_EMAIL", "a.murray0413@gmail.com")
    password = os.getenv("COCONUT_PASSWORD", "mHBR!KoG!Yrq7e5U")

    try:
        # Get Neo4j graph connection
        graph = get_graph()

        # Initialize service with graph connection
        service = CoconutService(email=email, password=password, db_session=graph)
        print("Successfully authenticated with COCONUT API")

        # Test Mescaline
        test_molecule(
            service, "Mescaline", smiles="COC1=CC(=CC(=C1OC)OC)CCN"  # Mescaline SMILES
        )

        # Test Sceletium tortuosum
        test_organism(service, "Sceletium tortuosum")

        print("\nTest completed")

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
