"""Service for interacting with the DrugBank API."""

import logging
from typing import List, Optional, Dict, Any
import requests
from py2neo import Graph

from hyperblend.database.entry_manager import DatabaseEntryManager
from hyperblend.models.molecule import Molecule
from .base_service import BaseExternalService


class DrugBankService(BaseExternalService):
    """Service for fetching drug data from DrugBank."""

    BASE_URL = "https://go.drugbank.com/api/v1"

    def __init__(self, api_key: str, graph: Graph):
        """
        Initialize the DrugBank service.

        Args:
            api_key: DrugBank API key
            graph: Neo4j graph database connection
        """
        super().__init__(self.BASE_URL)
        self.graph = graph
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseEntryManager(graph)
        self.api_key = api_key
        self.session.headers.update(
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )

    def health_check(self) -> bool:
        """
        Check if the DrugBank service is available.

        Returns:
            bool: True if service is available, False otherwise
        """
        try:
            response = self._make_request("status")
            return response is not None and response.get("status") == "ok"
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False

    def search_molecule_by_name(
        self, name: str, max_results: int = 5
    ) -> List[Molecule]:
        """
        Search for molecules by name in DrugBank.

        Args:
            name: Name of the molecule to search for
            max_results: Maximum number of results to return

        Returns:
            List[Molecule]: List of found molecules
        """
        try:
            response = self._make_request(
                "drugs/search", method="GET", params={"q": name, "limit": max_results}
            )

            if not response or "drugs" not in response:
                return []

            molecules = []
            for drug_data in response["drugs"]:
                molecule = self._convert_to_molecule(drug_data)
                if molecule:
                    molecules.append(molecule)
                    self.db_manager.create_or_update_molecule(
                        molecule=molecule, source="DrugBank"
                    )

            return molecules

        except Exception as e:
            self.logger.error(f"Error searching molecule by name: {str(e)}")
            return []

    def get_molecule_by_drugbank_id(self, drugbank_id: str) -> Optional[Molecule]:
        """
        Get molecule details by DrugBank ID.

        Args:
            drugbank_id: DrugBank identifier

        Returns:
            Optional[Molecule]: Molecule if found, None otherwise
        """
        try:
            response = self._make_request(f"drugs/{drugbank_id}")
            if not response:
                return None

            molecule = self._convert_to_molecule(response)
            if molecule:
                self.db_manager.create_or_update_molecule(
                    molecule=molecule, source="DrugBank"
                )
                return molecule

            return None

        except Exception as e:
            self.logger.error(f"Error getting molecule by DrugBank ID: {str(e)}")
            return None

    def get_molecule_targets(self, drugbank_id: str) -> List[Dict[str, Any]]:
        """
        Get biological targets for a molecule.

        Args:
            drugbank_id: DrugBank molecule identifier

        Returns:
            List[Dict[str, Any]]: List of target information
        """
        try:
            response = self._make_request(f"drugs/{drugbank_id}/targets")
            if not response or "targets" not in response:
                return []

            targets = []
            for target_data in response["targets"]:
                target_info = {
                    "target_id": target_data.get("id"),
                    "name": target_data.get("name"),
                    "organism": target_data.get("organism"),
                    "actions": target_data.get("actions", []),
                    "uniprot_id": target_data.get("uniprot_id"),
                    "gene_name": target_data.get("gene_name"),
                }

                # Store target in database
                self.db_manager.create_or_update_target(
                    target_id=target_info["target_id"],
                    name=target_info["name"],
                    type="protein",
                    organism=target_info["organism"],
                )

                targets.append(target_info)

            return targets

        except Exception as e:
            self.logger.error(f"Error getting molecule targets: {str(e)}")
            return []

    def _convert_to_molecule(self, drugbank_data: Dict[str, Any]) -> Optional[Molecule]:
        """
        Convert DrugBank data to our Molecule model.

        Args:
            drugbank_data: DrugBank molecule data

        Returns:
            Optional[Molecule]: Our internal molecule model
        """
        try:
            # Extract properties from DrugBank data
            properties = drugbank_data.get("properties", {})
            calculated_properties = drugbank_data.get("calculated_properties", {})

            # Get molecular weight
            mol_weight = next(
                (
                    prop["value"]
                    for prop in calculated_properties
                    if prop["kind"] == "Molecular Weight"
                ),
                0.0,
            )

            # Get LogP
            logp = next(
                (
                    float(prop["value"])
                    for prop in calculated_properties
                    if prop["kind"] == "LogP"
                ),
                0.0,
            )

            # Get TPSA
            tpsa = next(
                (
                    float(prop["value"])
                    for prop in calculated_properties
                    if prop["kind"] == "Polar Surface Area"
                ),
                0.0,
            )

            molecule = Molecule(
                id=f"MOL_DRUGBANK_{drugbank_data.get('drugbank_id', '')}",
                name=drugbank_data.get("name", ""),
                formula=drugbank_data.get("molecular_formula", ""),
                molecular_weight=float(mol_weight),
                smiles=drugbank_data.get("smiles", ""),
                inchi=drugbank_data.get("inchi", ""),
                inchikey=drugbank_data.get("inchikey", ""),
                pubchem_cid=drugbank_data.get("pubchem_compound_id"),
                chembl_id=drugbank_data.get("chembl_id"),
                drugbank_id=drugbank_data.get("drugbank_id"),
                logp=logp,
                polar_surface_area=tpsa,
                known_activities=[],  # Would need additional processing
            )

            return molecule

        except Exception as e:
            self.logger.error(f"Error converting DrugBank data to molecule: {str(e)}")
            self.logger.debug(f"Problematic data: {drugbank_data}")
            return None

    def get_molecule_by_inchikey(self, inchikey: str) -> Optional[Molecule]:
        """
        Get molecule details by InChI Key from DrugBank.

        Args:
            inchikey: InChI Key of the molecule

        Returns:
            Optional[Molecule]: Molecule if found, None otherwise
        """
        try:
            # Search by InChI Key
            response = self._make_request(
                "drugs/search", method="GET", params={"q": inchikey, "limit": 1}
            )

            if not response or "drugs" not in response or not response["drugs"]:
                return None

            # Get detailed information for the first result
            drugbank_id = response["drugs"][0].get("drugbank_id")
            if not drugbank_id:
                return None

            return self.get_molecule_by_drugbank_id(drugbank_id)

        except Exception as e:
            self.logger.error(f"Error getting molecule by InChI Key: {str(e)}")
            return None

    def search_molecule_by_smiles(self, smiles: str) -> Optional[Molecule]:
        """
        Search for molecule by SMILES string in DrugBank.

        Args:
            smiles: SMILES string of the molecule

        Returns:
            Optional[Molecule]: Molecule if found, None otherwise
        """
        try:
            # Unfortunately, DrugBank API doesn't support direct SMILES search,
            # but we can try to search by the SMILES string as a generic query
            response = self._make_request(
                "drugs/search", method="GET", params={"q": smiles, "limit": 1}
            )

            if not response or "drugs" not in response or not response["drugs"]:
                return None

            # Get detailed information for the first result
            drugbank_id = response["drugs"][0].get("drugbank_id")
            if not drugbank_id:
                return None

            return self.get_molecule_by_drugbank_id(drugbank_id)

        except Exception as e:
            self.logger.error(f"Error searching molecule by SMILES: {str(e)}")
            return None

    def enrich_molecule(self, identifiers):
        """
        Enrich a molecule with data from DrugBank based on provided identifiers.

        Args:
            identifiers (dict): Dictionary of identifiers with keys like 'inchikey', 'smiles', 'name'

        Returns:
            dict: Enriched molecule data or None if no data found
        """
        if not self.api_key:
            self.logger.warning(
                "DrugBank API key not available. Unable to enrich molecule."
            )
            return None

        self.logger.info(f"Enriching molecule with identifiers: {identifiers}")

        molecule = None

        # Try to get molecule by name first, as DrugBank search is best with names
        if identifiers.get("name"):
            try:
                self.logger.info(f"Searching by name: {identifiers['name']}")
                molecules = self.search_molecule_by_name(identifiers["name"])
                if molecules and len(molecules) > 0:
                    molecule = molecules[0]
                    self.logger.info("Found molecule by name")
            except Exception as e:
                self.logger.warning(f"Error finding by name: {str(e)}")

        # If not found, try by InChI Key
        if not molecule and identifiers.get("inchikey"):
            try:
                self.logger.info(f"Searching by InChI Key: {identifiers['inchikey']}")
                molecule = self.get_molecule_by_inchikey(identifiers["inchikey"])
                if molecule:
                    self.logger.info("Found molecule by InChI Key")
            except Exception as e:
                self.logger.warning(f"Error finding by InChI Key: {str(e)}")

        # If not found, try using SMILES (note that DrugBank API doesn't support direct SMILES search)
        if not molecule and identifiers.get("smiles"):
            self.logger.info(
                "DrugBank API doesn't support direct SMILES search. No further attempts for SMILES."
            )

        # If we found a molecule, extract properties
        if molecule:
            # Format response with enriched properties
            properties = {
                "LogP": getattr(molecule, "logp", None),
                "Molecular Weight": getattr(molecule, "molecular_weight", None),
                "DrugBank Description": getattr(molecule, "description", None),
                "Drug Categories": getattr(molecule, "categories", None),
                "Drug Groups": getattr(molecule, "groups", None),
                "Mechanism of Action": getattr(molecule, "mechanism_of_action", None),
            }

            # Create identifiers dictionary
            returned_identifiers = {
                "DrugBank ID": getattr(molecule, "drugbank_id", None),
                "InChI Key": getattr(molecule, "inchikey", None),
                "SMILES": getattr(molecule, "smiles", None),
                "CAS Number": getattr(molecule, "cas_number", None),
            }

            # Filter out None values
            properties = {k: v for k, v in properties.items() if v is not None}
            returned_identifiers = {
                k: v for k, v in returned_identifiers.items() if v is not None
            }

            return {
                "properties": properties,
                "identifiers": returned_identifiers,
            }

        self.logger.warning("No molecule found with provided identifiers")
        return None
