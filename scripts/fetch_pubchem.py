# scripts/fetch_pubchem.py

"""Script to fetch compound data from PubChem."""

from typing import Dict, List, Optional, Any, Mapping

from hyperblend.domain.models import Compound, Source, BiologicalTarget
from hyperblend.infrastructure.database import SessionLocal
from hyperblend.domain.chemistry import chemistry_utils


def fetch_pubchem_data(cas_number: str) -> Optional[Mapping[str, Dict[str, Any]]]:
    """Fetch compound data from PubChem using CAS number."""
    try:
        # First get PubChem ID from CAS number
        pubchem_id = None
        # TODO: Implement CAS to PubChem ID lookup
        if not pubchem_id:
            print(f"Could not find PubChem ID for CAS {cas_number}")
            return None

        pubchem_data = chemistry_utils.get_pubchem_info(pubchem_id)
        chembl_data = chemistry_utils.get_chembl_info(pubchem_id)
        if not pubchem_data:
            return None

        result: Dict[str, Dict[str, Any]] = {
            "pubchem": pubchem_data,
            "chembl": chembl_data or {},
        }
        return result
    except Exception as e:
        print(f"Error fetching data for CAS {cas_number}: {e}")
        return None


def map_target_type(chembl_type: str) -> str:
    """Map ChEMBL target type to our simplified target types."""
    if "receptor" in chembl_type.lower():
        return "receptor"
    elif "enzyme" in chembl_type.lower():
        return "enzyme"
    elif "ion channel" in chembl_type.lower():
        return "ion_channel"
    elif "transport" in chembl_type.lower():
        return "transporter"
    elif "transcription" in chembl_type.lower():
        return "transcription_factor"
    return "protein_complex"  # Default type


def process_target_data(target_data: dict) -> BiologicalTarget:
    """Process target data from ChEMBL and create a BiologicalTarget instance."""
    chembl_type = target_data.get("target_type", "").lower()
    target_type = map_target_type(chembl_type)

    return BiologicalTarget(
        name=target_data.get("target_name", ""),
        type=target_type,
        description=target_data.get("target_desc", ""),
        external_ids={"chembl": target_data.get("target_chembl_id")},
    )


def create_compound_from_pubchem(cas_number: str) -> Optional[Compound]:
    """Create a compound entry from PubChem data."""
    data = fetch_pubchem_data(cas_number)
    if not data:
        return None

    pubchem_data = data["pubchem"]
    chembl_data = data["chembl"]

    # Create compound
    compound = Compound(
        name=pubchem_data.get("iupac_name", ""),
        cas_number=cas_number,
        smiles=pubchem_data.get("canonical_smiles", ""),
        molecular_formula=pubchem_data.get("molecular_formula", ""),
        molecular_weight=pubchem_data.get("molecular_weight", 0.0),
        external_ids={
            "pubchem": pubchem_data.get("pubchem_id"),
            "chembl": chembl_data.get("chembl_id") if chembl_data else None,
        },
    )

    # Process target interactions from ChEMBL
    if chembl_data and "target_interactions" in chembl_data:
        for interaction in chembl_data["target_interactions"]:
            target = process_target_data(interaction)
            compound.targets.append(target)

    return compound


def main():
    """Main function to fetch and store compound data."""
    session = SessionLocal()
    try:
        # Example CAS numbers
        cas_numbers = [
            "50-37-3",  # LSD
            "520-52-5",  # Psilocybin
            "57-27-2",  # Morphine
        ]

        for cas in cas_numbers:
            compound = create_compound_from_pubchem(cas)
            if compound:
                session.merge(compound)

        session.commit()
        print("Successfully fetched and stored compound data.")
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
