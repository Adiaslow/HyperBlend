"""Test script for all chemical database services."""

import os
from hyperblend.database import get_graph
from hyperblend.services.external.chembl_service import ChEMBLService
from hyperblend.services.external.pubchem_service import PubChemService
from hyperblend.services.external.coconut_service import CoconutService


def test_chembl_service(service: ChEMBLService, name: str):
    """Test ChEMBL service functionality."""
    print("\n=== Testing ChEMBL Service ===")

    print(f"\nSearching for {name} in ChEMBL...")
    molecules = service.search_molecule_by_name(name)

    if molecules:
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
            print(f"ChEMBL ID: {molecule.chembl_id}")
            print(f"LogP: {molecule.logp}")
            print(f"Polar Surface Area: {molecule.polar_surface_area}")

            if molecule.chembl_id:
                print("\nGetting targets...")
                targets = service.get_molecule_targets(molecule.chembl_id)
                if targets:
                    print(f"\nFound {len(targets)} targets")
                    for target in targets[:3]:  # Show first 3 targets
                        print(f"\nTarget: {target['name']}")
                        print(f"Organism: {target['organism']}")
                        print(f"Activities: {len(target['activities'])} recorded")
    else:
        print("No molecules found")


def test_pubchem_service(service: PubChemService, name: str):
    """Test PubChem service functionality."""
    print("\n=== Testing PubChem Service ===")

    print(f"\nSearching for {name} in PubChem...")
    molecules = service.search_molecule_by_name(name)

    if molecules:
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
            print(f"PubChem CID: {molecule.pubchem_cid}")
            print(f"LogP: {molecule.logp}")
            print(f"Polar Surface Area: {molecule.polar_surface_area}")
    else:
        print("No molecules found")


def test_coconut_service(service: CoconutService, name: str, organism_name: str):
    """Test COCONUT service functionality."""
    print("\n=== Testing COCONUT Service ===")

    print(f"\nSearching for {name} in COCONUT...")
    molecules = service.search_molecule_by_name(name)

    if molecules:
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
    else:
        print("No molecules found")

    print(f"\nSearching for organism: {organism_name}")
    organisms = service.search_organisms(name=organism_name)
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
    """Test all chemical database services."""
    try:
        # Get Neo4j graph connection
        graph = get_graph()
        print("Successfully connected to Neo4j database")

        # Initialize services
        chembl_service = ChEMBLService(graph)
        pubchem_service = PubChemService(graph)
        coconut_service = CoconutService(
            email=os.getenv("COCONUT_EMAIL", "a.murray0413@gmail.com"),
            password=os.getenv("COCONUT_PASSWORD", "mHBR!KoG!Yrq7e5U"),
            graph=graph,
        )

        # Test molecule to search for
        molecule_name = "Mescaline"
        organism_name = "Sceletium tortuosum"

        # Test each service
        test_chembl_service(chembl_service, molecule_name)
        test_pubchem_service(pubchem_service, molecule_name)
        test_coconut_service(coconut_service, molecule_name, organism_name)

        print("\nAll tests completed")

    except Exception as e:
        print(f"Error during testing: {str(e)}")


if __name__ == "__main__":
    main()
