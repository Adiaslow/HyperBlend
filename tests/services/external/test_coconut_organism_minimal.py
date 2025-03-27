# test_coconut_organism_minimal.py
"""
Minimal test script for COCONUT database queries.

This script demonstrates how to search for organisms and molecules in the COCONUT database,
addressing the filtering issues with the API by implementing client-side filtering.

NOTE: The COCONUT API appears to have issues with its filtering mechanism. It returns all molecules
regardless of the filter criteria provided. This script implements client-side filtering as a workaround.
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_search():
    """
    Test searching for organisms and molecules in COCONUT with proper client-side filtering.

    This function demonstrates how to:
    1. Authenticate with the COCONUT API
    2. Search for organisms by name
    3. Search for molecules by name, structural elements, and organism association
    4. Apply client-side filtering to get accurate results
    """
    # Authentication
    print("\nAuthenticating with COCONUT...")
    auth_payload = {"email": "a.murray0413@gmail.com", "password": "mHBR!KoG!Yrq7e5U"}
    auth_response = requests.post(
        "https://coconut.naturalproducts.net/api/auth/login", json=auth_payload
    )

    if auth_response.status_code == 200:
        print("\nAuthenticated with COCONUT...")
        token = auth_response.json().get("access_token")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Step 1: Organism Search with manual filtering
        target_organism = "Lophophora williamsii"
        print(f"\nSearching for organism: {target_organism}")

        # Send request to organism search endpoint
        print(
            "NOTE: Server-side filtering appears to be non-functional; manual filtering will be applied."
        )

        organism_payload = {
            "page": 1,
            "limit": 100,
            "filters": [
                {
                    "field": "name",
                    "operator": "like",
                    "value": "Lophophora",  # Use broader term to improve chance of finding
                }
            ],
            "selects": ["name", "rank", "iri", "molecule_count", "taxonomy"],
        }

        organism_response = requests.post(
            "https://coconut.naturalproducts.net/api/organisms/search",
            json=organism_payload,
            headers=headers,
        )

        if organism_response.status_code == 200:
            organism_data = organism_response.json()
            total_organisms = organism_data.get("total", 0)
            organisms = organism_data.get("data", [])

            print(
                f"\nAPI returned {total_organisms} total organisms (likely all organisms in database)"
            )
            print(f"Retrieved {len(organisms)} organisms in the first page")

            # Manual filter to find exact or close matches
            exact_matches = []
            partial_matches = []

            for organism in organisms:
                name = organism.get("name", "")
                if name:
                    if name.lower() == target_organism.lower():
                        exact_matches.append(organism)
                    elif "lophophora" in name.lower():
                        partial_matches.append(organism)

            print(f"\nAfter manual filtering:")
            print(f"- Exact matches for '{target_organism}': {len(exact_matches)}")
            print(f"- Partial matches for 'Lophophora': {len(partial_matches)}")

            # Display matching organisms
            if exact_matches or partial_matches:
                matches_to_display = exact_matches if exact_matches else partial_matches

                print("\n=== MATCHING ORGANISMS ===")
                for i, organism in enumerate(matches_to_display[:5]):  # Show up to 5
                    print(f"\nOrganism {i+1}:")
                    print(f"Name: {organism.get('name', 'N/A')}")
                    print(f"Rank: {organism.get('rank', 'N/A')}")
                    print(f"IRI: {organism.get('iri', 'N/A')}")
                    print(f"Molecule count: {organism.get('molecule_count', 'N/A')}")

                    taxonomy = organism.get("taxonomy", {})
                    if taxonomy:
                        print("\nTaxonomy:")
                        for level, value in taxonomy.items():
                            print(f"  {level}: {value}")

            # Step 2: Molecule Search by organism association with manual filtering
            print(f"\nSearching for molecules associated with {target_organism}...")

            molecule_payload = {
                "page": 1,
                "limit": 100,
                "filters": [
                    {
                        "field": "organisms.name",
                        "operator": "like",
                        "value": "Lophophora",
                    }
                ],
                "selects": [
                    "coconut_id",
                    "name",
                    "molecular_formula",
                    "molecular_weight",
                    "smiles",
                    "organisms.name",
                    "organisms.taxonomy",
                    "traditional_uses",
                ],
            }

            molecule_response = requests.post(
                "https://coconut.naturalproducts.net/api/molecules/search",
                json=molecule_payload,
                headers=headers,
            )

            if molecule_response.status_code == 200:
                molecule_data = molecule_response.json()
                total_molecules = molecule_data.get("total", 0)
                molecules = molecule_data.get("data", [])

                print(
                    f"\nAPI returned {total_molecules} total molecules (likely all molecules in database)"
                )
                print(f"Retrieved {len(molecules)} molecules in the first page")

                # Manual filtering to find molecules from target organism
                target_molecules = []

                for molecule in molecules:
                    orgs = molecule.get("organisms", [])
                    for org in orgs:
                        org_name = org.get("name", "")
                        if org_name and target_organism.lower() in org_name.lower():
                            target_molecules.append(molecule)
                            break

                print(
                    f"\nAfter manual filtering: Found {len(target_molecules)} molecules from {target_organism}"
                )

                # Display target molecules
                if target_molecules:
                    print(f"\n=== MOLECULES FROM {target_organism.upper()} ===")
                    for i, molecule in enumerate(target_molecules[:5]):  # Show up to 5
                        print(f"\nMolecule {i+1}:")
                        print(f"COCONUT ID: {molecule.get('coconut_id', 'N/A')}")
                        print(f"Name: {molecule.get('name', 'N/A')}")
                        print(f"Formula: {molecule.get('molecular_formula', 'N/A')}")
                        print(
                            f"Molecular Weight: {molecule.get('molecular_weight', 'N/A')}"
                        )
                        print(f"SMILES: {molecule.get('smiles', 'N/A')}")

                        # Print traditional uses if available
                        trad_uses = molecule.get("traditional_uses", [])
                        if trad_uses:
                            print("\nTraditional Uses:")
                            for use in trad_uses:
                                print(f"  - {use}")

                # Step 3: Try searching for known compounds from Lophophora williamsii
                known_compounds = [
                    "mescaline",
                    "pellotine",
                    "anhalonidine",
                    "lophophorine",
                ]
                compound_counts = {}

                for compound in known_compounds:
                    print(f"\nSearching for {compound} (found in {target_organism})...")

                    compound_payload = {
                        "page": 1,
                        "limit": 50,
                        "filters": [
                            {"field": "name", "operator": "like", "value": compound}
                        ],
                        "selects": ["coconut_id", "name"],
                    }

                    compound_response = requests.post(
                        "https://coconut.naturalproducts.net/api/molecules/search",
                        json=compound_payload,
                        headers=headers,
                    )

                    if compound_response.status_code == 200:
                        compound_data = compound_response.json()
                        compound_molecules = compound_data.get("data", [])

                        # Manual filtering
                        matching_compounds = []
                        for molecule in compound_molecules:
                            name = molecule.get("name", "")
                            if name and compound.lower() in name.lower():
                                matching_compounds.append(molecule)

                        compound_counts[compound] = len(matching_compounds)
                        print(
                            f"Found {len(matching_compounds)} molecules containing '{compound}' in name"
                        )

                        if matching_compounds:
                            print(
                                f"First match: {matching_compounds[0].get('name', 'N/A')}"
                            )

                # Summary of findings
                print("\n\n=== SUMMARY OF FINDINGS ===")
                print(f"Organism search:")
                print(f"- Exact matches for '{target_organism}': {len(exact_matches)}")
                print(f"- Partial matches for 'Lophophora': {len(partial_matches)}")

                print(f"\nMolecule search:")
                print(f"- Molecules from {target_organism}: {len(target_molecules)}")

                print("\nCompound search (after manual filtering):")
                for compound, count in compound_counts.items():
                    print(f"- {compound}: {count} molecules")

                print(
                    "\nNOTE: The COCONUT API appears to have filtering issues - it returns all items regardless of filter criteria."
                )
                print("Client-side filtering has been used as a workaround.")
            else:
                print(
                    f"Failed to search molecules. Status code: {molecule_response.status_code}"
                )
                print(f"Response: {molecule_response.text}")
        else:
            print(
                f"Failed to search organisms. Status code: {organism_response.status_code}"
            )
            print(f"Response: {organism_response.text}")
    else:
        print("Authentication failed")
        print(f"Status code: {auth_response.status_code}")
        print(f"Response: {auth_response.text}")


if __name__ == "__main__":
    test_search()
