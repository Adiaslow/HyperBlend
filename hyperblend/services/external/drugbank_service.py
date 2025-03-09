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
                logp=logp,
                polar_surface_area=tpsa,
                known_activities=[],  # Would need additional processing
            )

            return molecule

        except Exception as e:
            self.logger.error(f"Error converting DrugBank data to molecule: {str(e)}")
            self.logger.debug(f"Problematic data: {drugbank_data}")
            return None
