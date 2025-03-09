"""Test script for PubChem service using PubChemPy."""

from hyperblend.services.external.pubchem_service import PubChemService


def main():
    """Test PubChem service with Mescaline."""
    service = PubChemService()

    print("\nSearching for Mescaline in PubChem...")
    molecules = service.search_molecule_by_name("Mescaline")

    if not molecules:
        print("No molecules found")
        return

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

        # Get additional information
        print("\nSynonyms:")
        synonyms = service.get_synonyms(molecule.pubchem_cid)
        for synonym in synonyms[:5]:  # Show first 5 synonyms
            print(f"- {synonym}")

        print("\nAdditional Properties:")
        properties = service.get_properties(molecule.pubchem_cid)
        for prop_name, value in properties.items():
            if value is not None:
                print(f"- {prop_name}: {value}")

        print("-" * 50)


if __name__ == "__main__":
    main()
