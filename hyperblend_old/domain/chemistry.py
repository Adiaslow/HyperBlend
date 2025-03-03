"""Chemistry utilities for molecular analysis and validation."""

import re
from typing import Dict, Optional, Any, cast
import requests
from urllib.parse import quote
import pubchempy as pcp
from chembl_webresource_client.new_client import new_client
from chembl_webresource_client.unichem import unichem_client
from rdkit import Chem
from rdkit.Chem import (
    AllChem,
    rdMolDescriptors,
    GetFormalCharge,
    GraphDescriptors,
)

from hyperblend_old.infrastructure.repositories.models.targets import BiologicalTarget

# Type alias for ChEMBL client
ChemblClient = Any  # TODO: Replace with proper type when available


class ChemistryUtils:
    """Utilities for chemical structure analysis and validation."""

    @staticmethod
    def validate_smiles(smiles: str) -> bool:
        """Validate SMILES string using RDKit."""
        if not smiles:
            return False
        mol = Chem.MolFromSmiles(smiles)
        return mol is not None

    @staticmethod
    def standardize_smiles(smiles: str) -> Optional[str]:
        """Standardize SMILES string to canonical form."""
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        return Chem.MolToSmiles(mol, canonical=True)

    @staticmethod
    def calculate_molecular_descriptors(smiles: str) -> Optional[Dict[str, float]]:
        """Calculate molecular properties from SMILES."""
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None

        descriptors = {
            "molecular_weight": float(rdMolDescriptors.CalcExactMolWt(mol)),
            "heavy_atom_count": mol.GetNumHeavyAtoms(),
            "aromatic_ring_count": rdMolDescriptors.CalcNumAromaticRings(mol),
            "rotatable_bond_count": rdMolDescriptors.CalcNumRotatableBonds(mol),
            "h_bond_donor_count": rdMolDescriptors.CalcNumHBD(mol),
            "h_bond_acceptor_count": rdMolDescriptors.CalcNumHBA(mol),
            "topological_polar_surface_area": float(rdMolDescriptors.CalcTPSA(mol)),
            "logp": float(rdMolDescriptors.CalcCrippenDescriptors(mol)[0]),
            "charge": GetFormalCharge(mol),
        }

        try:
            descriptors.update(
                {
                    "molecular_volume": float(AllChem.ComputeMolVolume(mol)),
                    "polarizable_area": float(rdMolDescriptors.CalcLabuteASA(mol)),
                    "complexity_score": float(GraphDescriptors.BertzCT(mol)),
                }
            )
        except Exception:
            pass

        return descriptors

    @staticmethod
    def get_pubchem_info(cid: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive compound information from PubChem using CID."""
        try:
            base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

            # Get compound property data
            property_fields = [
                "IUPACName",
                "MolecularFormula",
                "MolecularWeight",
                "CanonicalSMILES",
                "IsomericSMILES",
                "InChI",
                "InChIKey",
                "XLogP",
                "TPSA",
                "Complexity",
                "Charge",
                "HBondDonorCount",
                "HBondAcceptorCount",
                "RotatableBondCount",
                "HeavyAtomCount",
            ]

            property_url = f"{base_url}/compound/cid/{cid}/property/{','.join(property_fields)}/JSON"
            prop_response = requests.get(property_url)

            if prop_response.status_code != 200:
                return None

            prop_data = prop_response.json()["PropertyTable"]["Properties"][0]

            # Get synonyms
            synonym_url = f"{base_url}/compound/cid/{cid}/synonyms/JSON"
            syn_response = requests.get(synonym_url)
            synonyms = []
            if syn_response.status_code == 200:
                synonyms = syn_response.json()["InformationList"]["Information"][0].get(
                    "Synonym", []
                )

            return {
                "pubchem_id": cid,
                "name": prop_data.get("IUPACName"),
                "molecular_formula": prop_data.get("MolecularFormula"),
                "molecular_weight": prop_data.get("MolecularWeight"),
                "smiles": prop_data.get("CanonicalSMILES"),
                "isomeric_smiles": prop_data.get("IsomericSMILES"),
                "inchi": prop_data.get("InChI"),
                "inchi_key": prop_data.get("InChIKey"),
                "xlogp": prop_data.get("XLogP"),
                "tpsa": prop_data.get("TPSA"),
                "complexity": prop_data.get("Complexity"),
                "charge": prop_data.get("Charge"),
                "h_bond_donor_count": prop_data.get("HBondDonorCount"),
                "h_bond_acceptor_count": prop_data.get("HBondAcceptorCount"),
                "rotatable_bond_count": prop_data.get("RotatableBondCount"),
                "heavy_atom_count": prop_data.get("HeavyAtomCount"),
                "synonyms": synonyms,
            }

        except Exception as e:
            print(f"Error fetching PubChem data: {str(e)}")
            return None

    @staticmethod
    def get_chembl_info(pubchem_id: str) -> Optional[Dict[str, Any]]:
        """Get ChEMBL information for a compound by PubChem ID."""
        try:
            # Initialize ChEMBL clients
            molecule_client: ChemblClient = new_client.molecule
            activity_client: ChemblClient = new_client.activity
            target_client: ChemblClient = new_client.target

            # Search for compound in ChEMBL by PubChem ID
            results = molecule_client.filter(
                molecule_properties__acd_logp__isnull=False
            )
            results = results.filter(cross_references__xref_id=pubchem_id)
            results = results.filter(cross_references__xref_src="PubChem")

            if not results:
                return None

            chembl_compound = results[0]
            chembl_id = chembl_compound["molecule_chembl_id"]

            # Get activity data
            activities = activity_client.filter(molecule_chembl_id=chembl_id)
            if not activities:
                return None

            # Process target interactions
            target_interactions = []
            for activity in activities:
                target_chembl_id = activity.get("target_chembl_id")
                if not target_chembl_id:
                    continue

                target = target_client.get(target_chembl_id)
                if target.get("organism") != BiologicalTarget.HUMAN_ORGANISM:
                    continue

                interaction = {
                    "target_chembl_id": target_chembl_id,
                    "target_name": target.get("pref_name", "Unknown"),
                    "target_type": target.get("target_type", "Unknown"),
                    "activity_type": activity.get("standard_type"),
                    "activity_value": activity.get("standard_value"),
                    "activity_unit": activity.get("standard_units"),
                }
                target_interactions.append(interaction)

            return {
                "chembl_id": chembl_id,
                "name": chembl_compound.get("pref_name", "Not available"),
                "formula": chembl_compound.get("molecule_properties", {}).get(
                    "full_molformula", "Not available"
                ),
                "molecular_weight": chembl_compound.get("molecule_properties", {}).get(
                    "full_mwt", "Not available"
                ),
                "smiles": chembl_compound.get("molecule_structures", {}).get(
                    "canonical_smiles", "Not available"
                ),
                "target_interactions": target_interactions,
            }

        except Exception as e:
            print(f"[ChEMBL] Error fetching ChEMBL data: {str(e)}")
            return None


# Global chemistry utilities instance
chemistry_utils = ChemistryUtils()
