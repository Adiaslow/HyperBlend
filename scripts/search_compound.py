# scripts/search_compound.py

"""Script to search for compound information using PubChem and ChEMBL."""

from hyperblend.domain.chemistry import chemistry_utils
from chembl_webresource_client.new_client import new_client


def main():
    """Main function to search for compound information."""
    # Initialize ChEMBL API clients
    molecule_client = new_client.molecule
    activity_client = new_client.activity
    target_client = new_client.target

    chembl_id = "CHEMBL2008762"  # Known ChEMBL ID for mesembrine
    print(f"\nSearching for compound with ChEMBL ID: {chembl_id}")

    # Get molecule information
    molecule = molecule_client.get(chembl_id)
    if not molecule:
        print("No molecule found")
        return

    print("\nMolecule Information:")
    print(f"ChEMBL ID: {molecule['molecule_chembl_id']}")
    print(f"Name: {molecule.get('pref_name', 'Not available')}")
    print(
        f"Formula: {molecule.get('molecule_properties', {}).get('full_molformula', 'Not available')}"
    )
    print(
        f"SMILES: {molecule.get('molecule_structures', {}).get('canonical_smiles', 'Not available')}"
    )
    print(f"Development Phase: {molecule.get('max_phase', 'Unknown')}")

    # Get bioactivity data
    print("\nFetching bioactivity data...")
    activities = activity_client.filter(molecule_chembl_id=chembl_id)

    if activities:
        # Group activities by target
        target_activities = {}
        for activity in activities:
            target_id = activity.get("target_chembl_id")
            if not target_id:
                continue

            if target_id not in target_activities:
                # Get target information
                target_info = target_client.get(target_id)
                target_activities[target_id] = {
                    "target_name": target_info.get("pref_name", "Unknown"),
                    "target_type": target_info.get("target_type", "Unknown"),
                    "organism": target_info.get("organism", "Unknown"),
                    "activities": [],
                }

            # Add activity details
            target_activities[target_id]["activities"].append(
                {
                    "type": activity.get("standard_type", "Unknown"),
                    "value": activity.get("standard_value", "Unknown"),
                    "units": activity.get("standard_units", "Unknown"),
                    "assay_id": activity.get("assay_chembl_id", "Unknown"),
                    "assay_description": activity.get(
                        "assay_description", "Not provided"
                    ),
                }
            )

        print(f"\nFound activities against {len(target_activities)} targets:")
        for target_id, target_data in target_activities.items():
            print(f"\nTarget: {target_data['target_name']}")
            print(f"Type: {target_data['target_type']}")
            print(f"Organism: {target_data['organism']}")
            print("\nActivities:")
            for activity in target_data["activities"]:
                print(f"- {activity['type']}: {activity['value']} {activity['units']}")
                print(f"  Assay: {activity['assay_description']}")
    else:
        print("No bioactivity data found")


if __name__ == "__main__":
    main()
