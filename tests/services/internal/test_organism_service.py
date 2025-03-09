"""Tests for the OrganismService."""

import os
import logging
from typing import Dict, Any
from py2neo import Graph

from hyperblend.services.internal.organism_service import OrganismService


def main():
    """Run tests for the OrganismService."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Connect to Neo4j
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    try:
        graph = Graph(neo4j_uri, auth=(neo4j_user, neo4j_password))
        service = OrganismService(graph)
        logger.info("Connected to Neo4j database")

        # Test find_by_name with exact match
        logger.info("\nTesting find_by_name with exact match for 'Sceletium tortuosum'")
        organisms = service.find_by_name("Sceletium tortuosum", exact=True)
        for organism in organisms:
            print_organism(organism)

        # Test find_by_name with pattern match
        logger.info("\nTesting find_by_name with pattern match for 'Sceletium'")
        organisms = service.find_by_name("Sceletium", exact=False)
        for organism in organisms:
            print_organism(organism)

        # Test find_by_rank
        logger.info("\nTesting find_by_rank for 'species'")
        organisms = service.find_by_rank("species")
        logger.info(f"Found {len(organisms)} species")
        for organism in organisms[:5]:  # Show first 5 results
            print_organism(organism)

        # Test find_by_source
        logger.info("\nTesting find_by_source for 'COCONUT'")
        organisms = service.find_by_source("COCONUT")
        logger.info(f"Found {len(organisms)} organisms from COCONUT")
        for organism in organisms[:5]:  # Show first 5 results
            print_organism(organism)

        # Test get_organism_molecules
        logger.info("\nTesting get_organism_molecules for 'Sceletium tortuosum'")
        molecules = service.get_organism_molecules("Sceletium tortuosum")
        logger.info(f"Found {len(molecules)} molecules")
        for molecule in molecules:
            print_molecule(molecule)

        # Test linking molecules to organism
        logger.info("\nTesting molecule linking")

        # Example molecules with properties
        test_molecules = {
            "MOL_COCONUT_CNP0580400.0": {  # Mescaline hydrochloride
                "name": "Mescaline hydrochloride",
                "formula": "C11H17NO3.HCl",
                "molecular_weight": 247.72,
                "smiles": "COC1=CC(CCN)=CC(OC)=C1OC.Cl",
                "inchi": "InChI=1S/C11H17NO3.ClH/c1-13-9-6-8(4-5-12)7-10(14-2)11(9)15-3;/h6-7H,4-5,12H2,1-3H3;1H",
                "inchikey": "FVZVSNDNKMOYKF-UHFFFAOYSA-N",
                "logp": 0.78,
                "polar_surface_area": 35.94,
            },
            "MOL_COCONUT_CNP0580401.0": {  # Example molecule
                "name": "Example Molecule 1",
                "formula": "C10H15NO2",
                "molecular_weight": 181.23,
                "smiles": "CC1=CC(=CC(=C1OC)OC)CCN",
                "inchi": "InChI=1S/C10H15NO2/c1-8-5-9(4-3-11)6-10(13-2)7-8/h5-7,11H,3-4H2,1-2H3",
                "inchikey": "EXAMPLE1NKMOYKF",
                "logp": 1.2,
                "polar_surface_area": 32.7,
            },
            "MOL_COCONUT_CNP0580402.0": {  # Example molecule
                "name": "Example Molecule 2",
                "formula": "C12H19NO3",
                "molecular_weight": 225.28,
                "smiles": "COC1=CC(=CC(=C1OC)OC)CCNC",
                "inchi": "InChI=1S/C12H19NO3/c1-13-7-6-9-3-10(14-2)12(16-4)8-11(9)15-5/h3,8,13H,6-7H2,1-5H3",
                "inchikey": "EXAMPLE2NKMOYKF",
                "logp": 1.5,
                "polar_surface_area": 38.3,
            },
        }

        # Link molecules to Sceletium tortuosum
        linked_count = service.link_molecules_to_organism(
            "Sceletium tortuosum",
            list(test_molecules.keys()),
            "COCONUT",
            test_molecules,
        )
        logger.info(f"Successfully linked {linked_count} molecules")

        # Verify the links by retrieving molecules
        logger.info("\nVerifying molecule links for 'Sceletium tortuosum'")
        molecules = service.get_organism_molecules("Sceletium tortuosum")
        logger.info(f"Found {len(molecules)} linked molecules")
        for molecule in molecules:
            print_molecule(molecule)

    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        raise


def print_organism(organism: Dict[str, Any]):
    """Print organism details in a readable format."""
    print("\nOrganism Details:")
    print(f"  Name: {organism['name']}")
    print(f"  Rank: {organism['rank']}")
    print(f"  IRI: {organism['iri']}")
    print(f"  Molecule Count: {organism['molecule_count']}")
    print(f"  Sources: {', '.join(organism['sources'])}")


def print_molecule(molecule: Dict[str, Any]):
    """Print molecule details in a readable format."""
    print("\nMolecule Details:")
    print(f"  ID: {molecule['id']}")
    print(f"  Name: {molecule['name']}")
    print(f"  Formula: {molecule['formula']}")
    print(f"  Molecular Weight: {molecule['molecular_weight']}")
    print(f"  SMILES: {molecule['smiles']}")
    print(f"  InChI: {molecule['inchi']}")
    print(f"  InChIKey: {molecule['inchikey']}")
    if molecule["pubchem_cid"]:
        print(f"  PubChem CID: {molecule['pubchem_cid']}")
    if molecule["chembl_id"]:
        print(f"  ChEMBL ID: {molecule['chembl_id']}")
    print(f"  LogP: {molecule['logp']}")
    print(f"  Polar Surface Area: {molecule['polar_surface_area']}")
    if molecule["synonyms"]:
        print(f"  Synonyms: {', '.join(molecule['synonyms'])}")
    print(f"  Sources: {', '.join(molecule['sources'])}")


if __name__ == "__main__":
    main()
