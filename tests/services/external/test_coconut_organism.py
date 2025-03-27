# test_coconut_organism.py
"""Test script for COCONUT organism queries."""

import os
from dotenv import load_dotenv
from py2neo import Graph
from hyperblend.services.external.coconut_service import CoconutService

# Load environment variables
load_dotenv()


def test_organism_search():
    """Test searching for Lophophora williamsii in COCONUT."""
    # Get credentials from environment
    email = os.getenv("COCONUT_EMAIL")
    password = os.getenv("COCONUT_PASSWORD")

    if not email or not password:
        print("Error: COCONUT_EMAIL and COCONUT_PASSWORD must be set in .env file")
        return

    # Initialize Neo4j connection
    graph = Graph("bolt://localhost:7687", auth=("neo4j", "password"))

    # Initialize COCONUT service
    coconut_service = CoconutService(email, password, graph)

    # Search for Lophophora williamsii
    print("\nSearching for Lophophora williamsii...")
    organisms = coconut_service.search_organisms(name="Lophophora williamsii")

    if organisms:
        print("\nFound organisms:")
        for org in organisms:
            print("\nOrganism details:")
            print(f"Name: {org.get('name', 'N/A')}")
            print(f"Rank: {org.get('rank', 'N/A')}")
            print(f"IRI: {org.get('iri', 'N/A')}")
            print(f"Molecule count: {org.get('molecule_count', 0)}")
    else:
        print("No organisms found")


if __name__ == "__main__":
    test_organism_search()
