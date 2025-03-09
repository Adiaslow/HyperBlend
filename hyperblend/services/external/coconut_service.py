"""Service for interacting with the COCONUT (COlleCtion of Open NatUral producTs) database."""

import logging
from typing import List, Optional, Dict, Any
import requests
from py2neo import Graph
from hyperblend.database.entry_manager import DatabaseEntryManager
from hyperblend.models.molecule import Molecule
from .base_service import BaseExternalService


class CoconutService(BaseExternalService):
    """Service for fetching natural product data from COCONUT."""

    BASE_URL = "https://coconut.naturalproducts.net/api"

    def __init__(self, email: str, password: str, graph: Graph):
        """
        Initialize the COCONUT service.

        Args:
            email: Email for authentication
            password: Password for authentication
            graph: Neo4j graph database connection
        """
        super().__init__(self.BASE_URL)
        self.graph = graph
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update(
            {"accept": "application/json", "Content-Type": "application/json"}
        )
        self.db_manager = DatabaseEntryManager(graph)
        self._authenticate(email, password)

    def _authenticate(self, email: str, password: str):
        """
        Authenticate with COCONUT API.

        Args:
            email: User email
            password: User password
        """
        try:
            auth_payload = {"email": email, "password": password}
            response = self.session.post(
                f"{self.BASE_URL}/auth/login", json=auth_payload
            )
            response.raise_for_status()
            data = response.json()

            # Update session headers with the access token
            token = data.get("access_token")
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
            else:
                raise ValueError("No access token received")

        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            raise

    def search_molecule_by_name(
        self, name: str, max_results: int = 5
    ) -> List[Molecule]:
        """
        Search for molecules by name in COCONUT and store results in database.

        Args:
            name: Name of the molecule to search for
            max_results: Maximum number of results to return

        Returns:
            List[Molecule]: List of molecules found
        """
        try:
            search_payload = {
                "search": {
                    "filters": [
                        {"field": "name", "operator": "like", "value": f"%{name}%"}
                    ],
                    "selects": [
                        {"field": "standard_inchi"},
                        {"field": "standard_inchi_key"},
                        {"field": "canonical_smiles"},
                        {"field": "sugar_free_smiles"},
                        {"field": "identifier"},
                        {"field": "name"},
                        {"field": "cas"},
                        {"field": "iupac_name"},
                        {"field": "murko_framework"},
                        {"field": "structural_comments"},
                        {"field": "annotation_level"},
                        {"field": "has_stereo"},
                        {"field": "is_parent"},
                        {"field": "synonyms"},  # Add synonyms field
                    ],
                    "includes": [
                        {
                            "relation": "properties",
                            "selects": [
                                {"field": "molecular_weight"},
                                {"field": "exact_molecular_weight"},
                                {"field": "molecular_formula"},
                                {"field": "alogp"},
                                {"field": "topological_polar_surface_area"},
                                {"field": "rotatable_bond_count"},
                                {"field": "hydrogen_bond_acceptors"},
                                {"field": "hydrogen_bond_donors"},
                                {"field": "aromatic_rings_count"},
                                {"field": "qed_drug_likeliness"},
                                {"field": "formal_charge"},
                            ],
                        }
                    ],
                    "page": 1,
                    "limit": max_results,
                }
            }

            response = self.session.post(
                f"{self.BASE_URL}/molecules/search", json=search_payload
            )
            response.raise_for_status()
            data = response.json()

            self.logger.debug(f"Search response: {data}")

            molecules = []
            for mol_data in data.get("data", []):
                molecule = self._convert_to_molecule(mol_data)
                if molecule:
                    # Extract synonyms from the response
                    synonyms = mol_data.get("synonyms", [])
                    if mol_data.get("iupac_name"):
                        synonyms.append(mol_data["iupac_name"])

                    # Store in database
                    db_molecule = self.db_manager.add_or_update_molecule(
                        molecule=molecule, source="COCONUT", synonyms=synonyms
                    )
                    molecules.append(molecule)

            return molecules

        except Exception as e:
            self.logger.error(f"Error searching molecule by name: {str(e)}")
            return []

    def search_molecule_by_smiles(self, smiles: str) -> List[Molecule]:
        """
        Search for molecules by SMILES in COCONUT.

        Args:
            smiles: SMILES string of the molecule

        Returns:
            List[Molecule]: List of molecules found
        """
        try:
            search_payload = {
                "search": {
                    "filters": [
                        {"field": "canonical_smiles", "operator": "=", "value": smiles}
                    ],
                    "selects": [
                        {"field": "standard_inchi"},
                        {"field": "standard_inchi_key"},
                        {"field": "canonical_smiles"},
                        {"field": "identifier"},
                        {"field": "name"},
                        {"field": "cas"},
                        {"field": "iupac_name"},
                        {"field": "structural_comments"},
                        {"field": "annotation_level"},
                    ],
                    "includes": [{"relation": "properties"}],
                    "page": 1,
                    "limit": 10,
                }
            }

            response = self.session.post(
                f"{self.BASE_URL}/molecules/search", json=search_payload
            )
            response.raise_for_status()
            data = response.json()

            # Filter out None values from molecule conversion
            molecules = [
                mol
                for mol in (self._convert_to_molecule(m) for m in data.get("data", []))
                if mol is not None
            ]
            return molecules

        except Exception as e:
            self.logger.error(f"Error searching molecule by SMILES: {str(e)}")
            return []

    def get_molecule_by_identifier(self, identifier: str) -> Optional[Molecule]:
        """
        Get molecule by COCONUT identifier.

        Args:
            identifier: COCONUT molecule identifier

        Returns:
            Optional[Molecule]: Molecule if found, None otherwise
        """
        try:
            search_payload = {
                "search": {
                    "filters": [
                        {"field": "identifier", "operator": "=", "value": identifier}
                    ],
                    "selects": [
                        {"field": "standard_inchi"},
                        {"field": "standard_inchi_key"},
                        {"field": "canonical_smiles"},
                        {"field": "identifier"},
                        {"field": "name"},
                        {"field": "cas"},
                        {"field": "iupac_name"},
                        {"field": "structural_comments"},
                        {"field": "annotation_level"},
                    ],
                    "includes": [{"relation": "properties"}],
                    "page": 1,
                    "limit": 1,
                }
            }

            response = self.session.post(
                f"{self.BASE_URL}/molecules/search", json=search_payload
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("data"):
                return None

            return self._convert_to_molecule(data["data"][0])

        except Exception as e:
            self.logger.error(f"Error getting molecule by identifier: {str(e)}")
            return None

    def search_organisms(
        self, name: Optional[str] = None, rank: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for organisms in COCONUT and store results in database.

        Args:
            name: Name of the organism (optional)
            rank: Taxonomic rank (optional)

        Returns:
            List[Dict[str, Any]]: List of organisms found
        """
        try:
            filters = []
            if name:
                filters.append(
                    {"field": "name", "operator": "like", "value": f"%{name}%"}
                )
            if rank:
                filters.append({"field": "rank", "operator": "=", "value": rank})

            search_payload = {
                "search": {
                    "filters": filters,
                    "selects": [
                        {"field": "name"},
                        {"field": "iri"},
                        {"field": "rank"},
                        {"field": "molecule_count"},
                    ],
                    "page": 1,
                    "limit": 10,
                }
            }

            response = self.session.post(
                f"{self.BASE_URL}/organisms/search", json=search_payload
            )
            response.raise_for_status()
            data = response.json()

            organisms = []
            for org_data in data.get("data", []):
                # Store in database
                db_organism = self.db_manager.add_or_update_organism(
                    name=org_data.get("name", ""),
                    rank=org_data.get("rank", ""),
                    iri=org_data.get("iri", ""),
                    molecule_count=org_data.get("molecule_count", 0),
                    source="COCONUT",
                )
                organisms.append(org_data)

            return organisms

        except Exception as e:
            self.logger.error(f"Error searching organisms: {str(e)}")
            return []

    def _convert_to_molecule(self, coconut_data: Dict[str, Any]) -> Optional[Molecule]:
        """
        Convert COCONUT molecule data to our Molecule model.

        Args:
            coconut_data: Molecule data from COCONUT

        Returns:
            Optional[Molecule]: Our internal molecule model
        """
        try:
            # Debug logging
            self.logger.debug(f"Converting COCONUT data: {coconut_data}")

            # Extract properties from the properties array
            properties = {}
            raw_properties = coconut_data.get("properties", [])
            if isinstance(raw_properties, list):
                for prop in raw_properties:
                    if isinstance(prop, dict):
                        name = prop.get("name", "").lower()
                        value = prop.get("value")
                        if name and value is not None:
                            try:
                                # Try to convert numeric values
                                if (
                                    isinstance(value, str)
                                    and value.replace(".", "").isdigit()
                                ):
                                    value = float(value)
                                properties[name] = value
                            except ValueError:
                                properties[name] = value

            # Get molecular weight (try multiple property names)
            mol_weight = 0.0
            weight_props = [
                "molecular_weight",
                "exact_molecular_weight",
                "monoisotopic_mass",
            ]
            for prop in weight_props:
                if prop in properties:
                    try:
                        mol_weight = float(properties[prop])
                        break
                    except (ValueError, TypeError):
                        continue

            # Get LogP (try multiple property names)
            logp = 0.0
            logp_props = ["alogp", "xlogp", "logp"]
            for prop in logp_props:
                if prop in properties:
                    try:
                        logp = float(properties[prop])
                        break
                    except (ValueError, TypeError):
                        continue

            # Get polar surface area (try multiple property names)
            psa = 0.0
            psa_props = ["topological_polar_surface_area", "tpsa", "polar_surface_area"]
            for prop in psa_props:
                if prop in properties:
                    try:
                        psa = float(properties[prop])
                        break
                    except (ValueError, TypeError):
                        continue

            # Get formula (try multiple property names)
            formula = ""
            formula_props = ["molecular_formula", "formula", "mol_formula"]
            for prop in formula_props:
                if prop in properties and properties[prop]:
                    formula = str(properties[prop])
                    break

            molecule = Molecule(
                id=f"MOL_COCONUT_{coconut_data.get('identifier', '')}",
                name=coconut_data.get("name", "") or coconut_data.get("iupac_name", ""),
                formula=formula,
                molecular_weight=mol_weight,
                smiles=coconut_data.get("canonical_smiles", ""),
                inchi=coconut_data.get("standard_inchi", ""),
                inchikey=coconut_data.get("standard_inchi_key", ""),
                pubchem_cid=None,  # Would need to cross-reference with PubChem
                chembl_id=None,  # Would need to cross-reference with ChEMBL
                logp=logp,
                polar_surface_area=psa,
                known_activities=[],  # Would need additional processing
            )

            # Log successful conversion
            self.logger.debug(
                f"Successfully converted molecule: {molecule.id} - {molecule.name}"
            )
            return molecule

        except Exception as e:
            self.logger.error(f"Error converting COCONUT data to molecule: {str(e)}")
            self.logger.debug(f"Problematic data: {coconut_data}")
            return None

    def health_check(self) -> bool:
        """
        Check if the COCONUT service is available.

        Returns:
            bool: True if service is available, False otherwise
        """
        try:
            response = self._make_request("health")
            return response is not None and response.get("status") == "ok"
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False
