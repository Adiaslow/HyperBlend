"""Tests for the TargetService."""

import os
import logging
from typing import Dict, Any
from py2neo import Graph

from hyperblend.services.internal.target_service import TargetService


def main():
    """Run tests for the TargetService."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Connect to Neo4j
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    try:
        graph = Graph(neo4j_uri, auth=(neo4j_user, neo4j_password))
        service = TargetService(graph)
        logger.info("Connected to Neo4j database")

        # Create test target
        logger.info("\nCreating test target")
        target_properties = {
            "name": "5-HT2A",
            "type": "receptor",
            "organism": "Homo sapiens",
            "uniprot_id": "P28223",
            "chembl_id": "CHEMBL224",
            "description": "5-hydroxytryptamine receptor 2A",
            "sequence": "MDILCEENTSLSSTTNSLMQLNDDTRLYSNDFNSGEANTSDAFNWTVDSENRTNLSCEGCLSPSCLSLLHLQEKNWSALLTAVVIILTIAGNILVIMAVSLEKKLQNATNYFLMSLAIADMLLGFLVMPVSMLTILYGYRWPLPSKLCAVWIYLDVLFSTASIMHLCAISLDRYVAIQNPIHHSRFNSRTKAFLKIIAVWTISVGISMPIPVFGLQDDSKVFKQGSCLLADDNFVLIGSFVSFFIPLTIMVITYFLTIKSLQKEATLCVSDLGTRAKLASFSFLPQSSLSSEKLFQRSIHREPGSYTGRRTMQSISNEQKACKVLGIVFFLFVVMWCPFFITNIMAVICKESCNEDVIGALLNVFVWIGYLSSAVNPLVYTLFNKTYRSAFSRYIQCQYKENKKPLQLILVNTIPALAYKSSQLQMGQKKNSKQDAKTTDNDCSMVALGKQHSEEASKDNSDGVNEKVSCV",
        }
        success = service._ensure_target_exists(
            target_properties["name"],
            target_properties["type"],
            "ChEMBL",
            target_properties,
        )
        logger.info(f"Target creation {'successful' if success else 'failed'}")

        # Test find_by_name with exact match
        logger.info("\nTesting find_by_name with exact match for '5-HT2A'")
        targets = service.find_by_name("5-HT2A", exact=True)
        for target in targets:
            print_target(target)

        # Test find_by_name with pattern match
        logger.info("\nTesting find_by_name with pattern match for '5-HT'")
        targets = service.find_by_name("5-HT", exact=False)
        for target in targets:
            print_target(target)

        # Test find_by_type
        logger.info("\nTesting find_by_type for 'receptor'")
        targets = service.find_by_type("receptor")
        logger.info(f"Found {len(targets)} receptors")
        for target in targets:
            print_target(target)

        # Test find_by_source
        logger.info("\nTesting find_by_source for 'ChEMBL'")
        targets = service.find_by_source("ChEMBL")
        logger.info(f"Found {len(targets)} targets from ChEMBL")
        for target in targets:
            print_target(target)

        # Test linking molecules with activity data
        logger.info("\nTesting molecule activity linking")
        test_molecules = [
            {
                "id": "MOL_COCONUT_CNP0580400.0",
                "activity_type": "Ki",
                "activity_value": 1.5,
                "activity_unit": "nM",
            },
            {
                "id": "MOL_COCONUT_CNP0580401.0",
                "activity_type": "IC50",
                "activity_value": 25.3,
                "activity_unit": "nM",
            },
        ]

        for mol in test_molecules:
            success = service.link_molecule_to_target(
                "5-HT2A",
                mol["id"],
                mol["activity_type"],
                mol["activity_value"],
                mol["activity_unit"],
                "ChEMBL",
            )
            logger.info(
                f"Linking molecule {mol['id']} {'successful' if success else 'failed'}"
            )

        # Test getting target molecules
        logger.info("\nTesting get_target_molecules for '5-HT2A'")
        molecules = service.get_target_molecules("5-HT2A")
        logger.info(f"Found {len(molecules)} molecules")
        for molecule in molecules:
            print_molecule(molecule)

        # Test getting target molecules with activity type filter
        logger.info("\nTesting get_target_molecules for '5-HT2A' with Ki activity")
        molecules = service.get_target_molecules("5-HT2A", activity_type="Ki")
        logger.info(f"Found {len(molecules)} Ki molecules")
        for molecule in molecules:
            print_molecule(molecule)

    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        raise


def print_target(target: Dict[str, Any]):
    """Print target details in a readable format."""
    print("\nTarget Details:")
    print(f"  Name: {target['name']}")
    print(f"  Type: {target['type']}")
    print(f"  Organism: {target['organism']}")
    if target["uniprot_id"]:
        print(f"  UniProt ID: {target['uniprot_id']}")
    if target["chembl_id"]:
        print(f"  ChEMBL ID: {target['chembl_id']}")
    print(f"  Description: {target['description']}")
    print(f"  Sequence Length: {len(target['sequence']) if target['sequence'] else 0}")
    print(f"  Molecule Count: {target['molecule_count']}")
    if target["synonyms"]:
        print(f"  Synonyms: {', '.join(target['synonyms'])}")
    print(f"  Sources: {', '.join(target['sources'])}")


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
    if molecule.get("activity_type"):
        print(
            f"  Activity: {molecule['activity_value']} {molecule['activity_unit']} ({molecule['activity_type']})"
        )
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
