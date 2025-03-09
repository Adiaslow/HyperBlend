"""ChEMBL service for retrieving chemical data."""

import logging
from typing import List, Optional, Dict, Any, Union
from chembl_webresource_client.new_client import new_client
from py2neo import Graph

from hyperblend.database.entry_manager import DatabaseEntryManager
from hyperblend.models.molecule import Molecule
from .base_service import BaseExternalService


class ChEMBLService(BaseExternalService):
    """Service for fetching chemical data from ChEMBL."""

    BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"

    def __init__(self, graph: Graph):
        """
        Initialize the ChEMBL service.

        Args:
            graph: Neo4j graph database connection
        """
        super().__init__(self.BASE_URL)
        self.graph = graph
        self.logger = logging.getLogger(__name__)
        self.molecule_client = new_client.molecule
        self.target_client = new_client.target
        self.activity_client = new_client.activity
        self.db_manager = DatabaseEntryManager(graph)

    def health_check(self) -> bool:
        """
        Check if the ChEMBL service is available.

        Returns:
            bool: True if service is available, False otherwise
        """
        try:
            response = self._make_request("status")
            return response is not None and response.get("status") == "UP"
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False

    def search_molecule_by_name(
        self, name: str, max_results: int = 5
    ) -> List[Molecule]:
        """
        Search for molecules by name in ChEMBL.

        Args:
            name: Name of the molecule to search for
            max_results: Maximum number of results to return

        Returns:
            List[Molecule]: List of found molecules
        """
        try:
            # Search by molecule name
            results = self.molecule_client.filter(pref_name__icontains=name).only(
                "molecule_chembl_id",
                "pref_name",
                "molecule_synonyms",
                "molecule_properties",
                "molecule_structures",
            )[:max_results]

            # If no results found by preferred name, try searching by synonyms
            if not results:
                results = self.molecule_client.filter(
                    molecule_synonyms__molecule_synonym__icontains=name
                ).only(
                    "molecule_chembl_id",
                    "pref_name",
                    "molecule_synonyms",
                    "molecule_properties",
                    "molecule_structures",
                )[
                    :max_results
                ]

            molecules = []
            for result in results:
                molecule = self._convert_to_molecule(result)
                if molecule:
                    molecules.append(molecule)
                    self.db_manager.create_or_update_molecule(
                        molecule=molecule, source="ChEMBL"
                    )

            return molecules

        except Exception as e:
            self.logger.error(f"Error searching molecule by name: {str(e)}")
            return []

    def get_molecule_by_chembl_id(self, chembl_id: str) -> Optional[Molecule]:
        """
        Get molecule details by ChEMBL ID and store in database.

        Args:
            chembl_id: ChEMBL molecule identifier

        Returns:
            Optional[Molecule]: Molecule if found, None otherwise
        """
        try:
            result = self.molecule_client.get(chembl_id)
            if result:
                molecule = self._convert_to_molecule(result)
                if molecule:
                    # Extract synonyms
                    synonyms = []
                    if result.get("molecule_synonyms"):
                        synonyms = [
                            syn.get("synonym")
                            for syn in result["molecule_synonyms"]
                            if syn.get("synonym")
                        ]
                    if result.get("pref_name"):
                        synonyms.append(result["pref_name"])

                    # Store in database
                    db_molecule = self.db_manager.create_or_update_molecule(
                        molecule=molecule, source="ChEMBL"
                    )
                    return molecule

            return None

        except Exception as e:
            self.logger.error(f"Error getting molecule by ChEMBL ID: {str(e)}")
            return None

    def get_molecule_targets(self, chembl_id: str) -> List[Dict[str, Any]]:
        """
        Get biological targets for a molecule with high confidence predictions.

        Args:
            chembl_id: ChEMBL molecule identifier

        Returns:
            List[Dict[str, Any]]: List of target information with confidence scores
        """
        try:
            # Get all activities for the molecule
            activities = self.activity_client.filter(molecule_chembl_id=chembl_id).only(
                "target_chembl_id",
                "standard_type",
                "standard_value",
                "standard_units",
                "standard_relation",
                "confidence_score",
                "assay_type",
                "pchembl_value",
            )

            # Filter activities for high confidence and collect target IDs
            target_activities = {}
            for act in activities:
                if act.get("confidence_score", 0) >= 0.9:  # 90% confidence threshold
                    target_id = act.get("target_chembl_id")
                    if target_id:
                        if target_id not in target_activities:
                            target_activities[target_id] = []
                        target_activities[target_id].append(act)

            targets = []
            for target_id, acts in target_activities.items():
                target = self.target_client.get(target_id)
                if target:
                    # Create target entry with detailed information
                    target_info = {
                        "target_id": target_id,
                        "name": target.get("pref_name", ""),
                        "organism": target.get("organism", ""),
                        "target_type": target.get("target_type", ""),
                        "confidence_score": max(
                            act.get("confidence_score", 0) for act in acts
                        ),
                        "activities": [
                            {
                                "type": act.get("standard_type"),
                                "value": act.get("standard_value"),
                                "units": act.get("standard_units"),
                                "relation": act.get("standard_relation"),
                                "pchembl_value": act.get("pchembl_value"),
                                "assay_type": act.get("assay_type"),
                            }
                            for act in acts
                        ],
                    }

                    # Store target in database
                    self.db_manager.create_or_update_target(
                        target_id=target_id,
                        name=target_info["name"],
                        type=target_info["target_type"],
                        organism=target_info["organism"],
                        confidence_score=target_info["confidence_score"],
                    )

                    # Create relationship between molecule and target
                    self.db_manager.create_molecule_target_relationship(
                        molecule_chembl_id=chembl_id,
                        target_chembl_id=target_id,
                        confidence_score=target_info["confidence_score"],
                        activities=target_info["activities"],
                    )

                    targets.append(target_info)

            return targets

        except Exception as e:
            self.logger.error(f"Error getting molecule targets: {str(e)}")
            return []

    def get_molecule_bioactivities(self, chembl_id: str) -> List[Dict[str, Any]]:
        """
        Get bioactivity data for a molecule.

        Args:
            chembl_id: ChEMBL molecule identifier

        Returns:
            List[Dict[str, Any]]: List of bioactivity data
        """
        try:
            activities = self.activity_client.filter(molecule_chembl_id=chembl_id).only(
                "activity_id",
                "standard_type",
                "standard_value",
                "standard_units",
                "target_chembl_id",
                "target_organism",
                "target_pref_name",
            )

            return list(activities)

        except Exception as e:
            self.logger.error(f"Error getting molecule bioactivities: {str(e)}")
            return []

    def _convert_to_molecule(self, chembl_data: Dict[str, Any]) -> Optional[Molecule]:
        """
        Convert ChEMBL molecule data to our Molecule model.

        Args:
            chembl_data: Molecule data from ChEMBL

        Returns:
            Optional[Molecule]: Our internal molecule model
        """
        try:
            structures = chembl_data.get("molecule_structures", {})
            properties = chembl_data.get("molecule_properties", {})

            molecule = Molecule(
                id=f"MOL_CHEMBL_{chembl_data.get('molecule_chembl_id', '')}",
                name=chembl_data.get("pref_name", ""),
                formula=properties.get("full_molformula", ""),
                molecular_weight=properties.get("full_mwt", 0.0),
                smiles=structures.get("canonical_smiles", ""),
                inchi=structures.get("standard_inchi", ""),
                inchikey=structures.get("standard_inchi_key", ""),
                pubchem_cid=None,  # Would need to cross-reference with PubChem
                chembl_id=chembl_data.get("molecule_chembl_id", ""),
                logp=properties.get("alogp", 0.0),
                polar_surface_area=properties.get("psa", 0.0),
                known_activities=[],  # Would need additional processing
            )

            return molecule

        except Exception as e:
            self.logger.error(f"Error converting ChEMBL data to molecule: {str(e)}")
            self.logger.debug(f"Problematic data: {chembl_data}")
            return None
