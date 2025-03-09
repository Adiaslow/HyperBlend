"""Tests for the UniProtService."""

import logging
from typing import Dict, Any
from py2neo import Graph

from hyperblend.services.external.uniprot_service import UniProtService, ProteinResult
from hyperblend.database.entry_manager import DatabaseEntryManager


def main():
    """Run tests for UniProt service."""
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    try:
        # Initialize Neo4j connection
        graph = Graph("bolt://localhost:7687", auth=("neo4j", "password"))
        db_manager = DatabaseEntryManager(graph)

        # Initialize UniProt service
        service = UniProtService(db_manager)
        logger.info("Initialized UniProt service")

        # Test protein search
        logger.info("\nTesting protein search for '5-HT2A receptor'")
        proteins = service.search_protein(
            query="5-HT2A receptor", organism="Homo sapiens"
        )
        logger.info(f"Found {len(proteins)} proteins")

        # Test get_protein for P28223 (5-HT2A)
        logger.info("\nTesting get_protein for P28223 (5-HT2A) from API")
        protein = service.get_protein("P28223")
        if protein:
            logger.info("\nProtein Details:")
            logger.info(f"  UniProt ID: {protein.get('primaryAccession')}")
            logger.info(f"  Entry Name: {protein.get('uniProtkbId')}")
            logger.info(
                f"  Protein Name: {protein.get('proteinDescription', {}).get('recommendedName', {}).get('fullName', {}).get('value')}"
            )
            logger.info(
                f"  Gene Names: {protein.get('genes', [{}])[0].get('geneName', {}).get('value')}"
            )
            logger.info(
                f"  Organism: {protein.get('organism', {}).get('scientificName')}"
            )
            logger.info(f"  Length: {protein.get('sequence', {}).get('length')}")
            logger.info(
                f"  Function: {protein.get('comments', [{}])[0].get('text', [{}])[0].get('value')}"
            )

            # Get ChEMBL and PDB IDs
            chembl_ids = []
            pdb_ids = []
            for xref in protein.get("uniProtKBCrossReferences", []):
                if xref.get("database") == "ChEMBL":
                    chembl_ids.append(xref.get("id"))
                elif xref.get("database") == "PDB":
                    pdb_ids.append(xref.get("id"))

            logger.info(f"  ChEMBL IDs: {', '.join(chembl_ids)}")
            logger.info(f"  PDB IDs: {', '.join(pdb_ids)}")

        # Test get_protein from cache
        logger.info("\nTesting get_protein for P28223 (5-HT2A) from cache")
        cached_protein = service.get_protein("P28223")
        if cached_protein:
            logger.info("Successfully retrieved protein from cache")

        # Test get_protein_sequence
        logger.info("\nTesting get_protein_sequence for P28223")
        sequence = service.get_protein_sequence("P28223")
        if sequence:
            logger.info(f"Sequence length: {len(sequence)}")
            logger.info(f"Sequence start: {sequence[:60]}...")

        # Test get_protein_features
        logger.info("\nTesting get_protein_features for P28223")
        features = service.get_protein_features("P28223")
        if features:
            logger.info(f"Found {len(features)} features\n")
            for feature in features:
                logger.info("Feature:")
                logger.info(f"  Type: {feature.get('type')}")
                logger.info(f"  Category: {feature.get('category', '')}")
                logger.info(f"  Description: {feature.get('description', '')}")
                logger.info(
                    f"  Location: {feature.get('location', {}).get('start', {}).get('value', '')}-{feature.get('location', {}).get('end', {}).get('value', '')}\n"
                )

        # Test error handling
        logger.info("\nTesting error handling with invalid ID")
        invalid_protein = service.get_protein("INVALID_ID")
        if not invalid_protein:
            logger.info("Successfully handled invalid protein ID")

        # Verify database entries
        logger.info("\nVerifying database entries")
        protein_node = db_manager.get_node("Protein", {"uniprot_id": "P28223"})
        if protein_node:
            logger.info("  Found protein node in database")

            # Check gene relationships
            genes = db_manager.get_related_nodes(protein_node, "ENCODED_BY", "Gene")
            logger.info(f"  Found {len(genes)} gene relationships")

            # Check pathway relationships
            pathways = db_manager.get_related_nodes(
                protein_node, "INVOLVED_IN", "Pathway"
            )
            logger.info(f"  Found {len(pathways)} pathway relationships")

            # Check disease relationships
            diseases = db_manager.get_related_nodes(
                protein_node, "ASSOCIATED_WITH", "Disease"
            )
            logger.info(f"  Found {len(diseases)} disease relationships")

            # Check structure relationships
            structures = db_manager.get_related_nodes(
                protein_node, "HAS_STRUCTURE", "Structure"
            )
            logger.info(f"  Found {len(structures)} structure relationships")

            # Check ChEMBL references
            chembl_refs = db_manager.get_related_nodes(
                protein_node, "HAS_CHEMBL", "Molecule"
            )
            logger.info(f"  Found {len(chembl_refs)} ChEMBL references")

    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        raise


def verify_database_entries(db_manager: DatabaseEntryManager, uniprot_id: str):
    """Verify that protein data was correctly stored in the database."""
    # Check protein node
    protein = db_manager.get_node("Protein", {"uniprot_id": uniprot_id})
    if protein:
        print("\nDatabase Verification:")
        print("  Found protein node in database")

        # Check relationships
        genes = db_manager.get_related_nodes(
            "Protein", {"uniprot_id": uniprot_id}, "ENCODED_BY", "Gene"
        )
        print(f"  Found {len(genes)} gene relationships")

        pathways = db_manager.get_related_nodes(
            "Protein", {"uniprot_id": uniprot_id}, "INVOLVED_IN", "Pathway"
        )
        print(f"  Found {len(pathways)} pathway relationships")

        diseases = db_manager.get_related_nodes(
            "Protein", {"uniprot_id": uniprot_id}, "ASSOCIATED_WITH", "Disease"
        )
        print(f"  Found {len(diseases)} disease relationships")

        structures = db_manager.get_related_nodes(
            "Protein", {"uniprot_id": uniprot_id}, "HAS_STRUCTURE", "Structure"
        )
        print(f"  Found {len(structures)} structure relationships")

        chembl_refs = db_manager.get_related_nodes(
            "Protein", {"uniprot_id": uniprot_id}, "HAS_CHEMBL", "Molecule"
        )
        print(f"  Found {len(chembl_refs)} ChEMBL references")
    else:
        print("\nWarning: Protein node not found in database")


def print_protein(protein: ProteinResult):
    """Print protein details in a readable format."""
    print("\nProtein Details:")
    print(f"  UniProt ID: {protein['uniprot_id']}")
    print(f"  Entry Name: {protein['entry_name']}")
    print(f"  Protein Name: {protein['protein_name']}")
    if protein["gene_names"]:
        print(f"  Gene Names: {', '.join(protein['gene_names'])}")
    print(f"  Organism: {protein['organism']}")
    print(f"  Length: {protein['length']}")
    if protein["ec_numbers"]:
        print(f"  EC Numbers: {', '.join(protein['ec_numbers'])}")
    if protein["function"]:
        print(f"  Function: {protein['function']}")
    if protein["catalytic_activity"]:
        print("  Catalytic Activity:")
        for activity in protein["catalytic_activity"]:
            print(f"    - {activity}")
    if protein["pathways"]:
        print("  Pathways:")
        for path in protein["pathways"]:
            print(f"    - {path}")
    if protein["diseases"]:
        print("  Diseases:")
        for disease in protein["diseases"]:
            print(f"    - {disease}")
    if protein["chembl_ids"]:
        print(f"  ChEMBL IDs: {', '.join(protein['chembl_ids'])}")
    if protein["pdb_ids"]:
        print(f"  PDB IDs: {', '.join(protein['pdb_ids'])}")


def print_feature(feature: Dict[str, Any]):
    """Print protein feature in a readable format."""
    print("\nFeature:")
    print(f"  Type: {feature.get('type', '')}")
    print(f"  Category: {feature.get('category', '')}")
    if description := feature.get("description"):
        print(f"  Description: {description}")
    begin = feature.get("location", {}).get("start", {}).get("value")
    end = feature.get("location", {}).get("end", {}).get("value")
    if begin and end:
        print(f"  Location: {begin}-{end}")
    if length := feature.get("location", {}).get("length"):
        print(f"  Length: {length}")


if __name__ == "__main__":
    main()
