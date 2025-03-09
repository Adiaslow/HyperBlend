"""Test script for ChEMBL service."""

from hyperblend.services.external.chembl_service import ChEMBLService


def main():
    """Test ChEMBL service with Mescaline."""
    service = ChEMBLService()

    print("\nSearching for Mescaline in ChEMBL...")
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
        print(f"ChEMBL ID: {molecule.chembl_id}")
        print(f"LogP: {molecule.logp}")
        print(f"Polar Surface Area: {molecule.polar_surface_area}")

        if molecule.chembl_id:
            # Get target information
            print("\nTargets and Activities:")
            targets = service.get_molecule_targets(molecule.chembl_id)
            for target in targets:
                print(f"\nTarget: {target['target_name']}")
                print(f"ChEMBL ID: {target['target_chembl_id']}")
                print(f"Type: {target['target_type']}")
                print(f"Organism: {target['organism']}")
                print(f"Confidence: {target['confidence_score']}")

                print("\nActivities for this target:")
                for activity in target["activities"]:
                    print(
                        f"- {activity['standard_type']}: {activity['standard_value']} {activity['standard_units']}"
                    )

            # Get bioactivity data with high confidence
            print("\nHigh-confidence Bioactivities (confidence >= 7):")
            activities = service.get_molecule_bioactivities(molecule.chembl_id)
            for activity in activities:
                print(f"\nTarget: {activity['target_name']}")
                print(f"Type: {activity['standard_type']}")
                print(
                    f"Value: {activity['standard_value']} {activity['standard_units']}"
                )
                if activity["pchembl_value"]:
                    print(f"pChEMBL Value: {activity['pchembl_value']}")
                print(f"Confidence: {activity['confidence_score']}")

        print("-" * 50)


if __name__ == "__main__":
    main()
