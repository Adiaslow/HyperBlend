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
                drugbank_id=None,  # Not available from ChEMBL directly
                logp=properties.get("alogp", 0.0),
                polar_surface_area=properties.get("psa", 0.0),
                known_activities=[],  # Would need additional processing
            )

            return molecule

        except Exception as e:
            self.logger.error(f"Error converting ChEMBL data to molecule: {str(e)}")
            self.logger.debug(f"Problematic data: {chembl_data}")
            return None

    def get_molecule_by_inchikey(self, inchikey: str) -> Optional[Molecule]:
        """
        Get molecule details by InChI Key from ChEMBL.

        Args:
            inchikey: InChI Key of the molecule

        Returns:
            Optional[Molecule]: Molecule if found, None otherwise
        """
        try:
            # Search by InChI Key
            results = self.molecule_client.filter(
                molecule_structures__standard_inchi_key__exact=inchikey
            ).only(
                "molecule_chembl_id",
                "pref_name",
                "molecule_synonyms",
                "molecule_properties",
                "molecule_structures",
            )

            if results and len(results) > 0:
                # Take the first result
                result = results[0]
                molecule = self._convert_to_molecule(result)
                if molecule:
                    # Store in database
                    self.db_manager.create_or_update_molecule(
                        molecule=molecule, source="ChEMBL"
                    )
                    return molecule

            return None

        except Exception as e:
            self.logger.error(f"Error getting molecule by InChI Key: {str(e)}")
            return None

    def search_molecule_by_smiles(self, smiles: str) -> Optional[Molecule]:
        """
        Search for molecule by SMILES string in ChEMBL.

        Args:
            smiles: SMILES string of the molecule

        Returns:
            Optional[Molecule]: Molecule if found, None otherwise
        """
        try:
            # Search by canonical SMILES
            results = self.molecule_client.filter(
                molecule_structures__canonical_smiles__exact=smiles
            ).only(
                "molecule_chembl_id",
                "pref_name",
                "molecule_synonyms",
                "molecule_properties",
                "molecule_structures",
            )

            # If no results, try with less exact matching
            if not results:
                # This is more permissive but might be less accurate
                results = self.molecule_client.filter(
                    molecule_structures__canonical_smiles__icontains=smiles
                ).only(
                    "molecule_chembl_id",
                    "pref_name",
                    "molecule_synonyms",
                    "molecule_properties",
                    "molecule_structures",
                )[
                    :1
                ]

            if results and len(results) > 0:
                # Take the first result
                result = results[0]
                molecule = self._convert_to_molecule(result)
                if molecule:
                    # Store in database
                    self.db_manager.create_or_update_molecule(
                        molecule=molecule, source="ChEMBL"
                    )
                    return molecule

            return None

        except Exception as e:
            self.logger.error(f"Error searching molecule by SMILES: {str(e)}")
            return None

    def enrich_molecule(self, identifiers):
        """
        Enrich a molecule with data from ChEMBL based on provided identifiers.

        Args:
            identifiers (dict): Dictionary of identifiers with keys like 'inchikey', 'smiles', 'name'

        Returns:
            dict: Enriched molecule data or None if no data found
        """
        self.logger.info(f"Enriching molecule with identifiers: {identifiers}")

        molecule = None

        # Try ChEMBL ID first (most reliable)
        if identifiers.get("chembl_id"):
            try:
                self.logger.info(f"Searching by ChEMBL ID: {identifiers['chembl_id']}")
                molecule = self.get_molecule_by_chembl_id(identifiers["chembl_id"])
                if molecule:
                    self.logger.info("Found molecule by ChEMBL ID")
            except Exception as e:
                self.logger.warning(f"Error finding by ChEMBL ID: {str(e)}")

        # Try to get molecule by InChI Key (also very specific)
        if not molecule and identifiers.get("inchikey"):
            try:
                self.logger.info(f"Searching by InChI Key: {identifiers['inchikey']}")
                molecule = self.get_molecule_by_inchikey(identifiers["inchikey"])
                if molecule:
                    self.logger.info("Found molecule by InChI Key")
            except Exception as e:
                self.logger.warning(f"Error finding by InChI Key: {str(e)}")

        # If not found, try SMILES
        if not molecule and identifiers.get("smiles"):
            try:
                self.logger.info(f"Searching by SMILES: {identifiers['smiles']}")
                molecule = self.search_molecule_by_smiles(identifiers["smiles"])
                if molecule:
                    self.logger.info("Found molecule by SMILES")
            except Exception as e:
                self.logger.warning(f"Error finding by SMILES: {str(e)}")

        # If still not found, try by name
        if not molecule and identifiers.get("name"):
            try:
                name = identifiers["name"]
                self.logger.info(f"Searching by name: {name}")

                # Try known specific drug names with direct ChEMBL ID mapping
                known_substances = {
                    "mescaline": "CHEMBL8857",
                    "lsd": "CHEMBL18597",
                    "psilocybin": "CHEMBL9237",
                    "dmt": "CHEMBL1336",
                    "mdma": "CHEMBL1833",
                    "cocaine": "CHEMBL370847",
                    "morphine": "CHEMBL70",
                    "caffeine": "CHEMBL113",
                    "nicotine": "CHEMBL3",
                    "thc": "CHEMBL465",
                    "ketamine": "CHEMBL658",
                }

                # Normalize name (lowercase, remove spaces)
                normalized_name = name.lower().strip()

                # Check if this is a known substance
                if normalized_name in known_substances:
                    chembl_id = known_substances[normalized_name]
                    self.logger.info(
                        f"Found known substance match for '{normalized_name}' with ChEMBL ID {chembl_id}"
                    )
                    try:
                        molecule = self.get_molecule_by_chembl_id(chembl_id)
                        if molecule:
                            self.logger.info(
                                f"Successfully retrieved molecule for known substance '{normalized_name}'"
                            )
                    except Exception as e:
                        self.logger.warning(
                            f"Error retrieving known substance: {str(e)}"
                        )

                # If still not found, try normal name search
                if not molecule:
                    self.logger.info(f"Trying regular name search for: {name}")
                    molecules = self.search_molecule_by_name(name)
                    if molecules and len(molecules) > 0:
                        molecule = molecules[0]
                        self.logger.info("Found molecule by name search")
            except Exception as e:
                self.logger.warning(f"Error finding by name: {str(e)}")

        if not molecule:
            self.logger.warning("No molecule found with provided identifiers")
            return None

        # Convert to dictionary format
        if not isinstance(molecule, dict):
            try:
                molecule_dict = molecule.model_dump()
            except AttributeError:
                try:
                    molecule_dict = molecule.__dict__
                except AttributeError:
                    self.logger.error("Failed to convert molecule to dictionary")
                    return None
        else:
            molecule_dict = molecule

        # Prepare the enriched data structure
        enriched = {
            "properties": molecule_dict,
            "identifiers": {
                "inchikey": molecule_dict.get("inchikey"),
                "smiles": molecule_dict.get("smiles"),
                "chembl_id": molecule_dict.get("chembl_id"),
            },
        }

        return enriched
