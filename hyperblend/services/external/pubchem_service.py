"""PubChem service for retrieving chemical data."""

import logging
from typing import List, Optional, Dict, Any, Union
import pubchempy as pcp
from py2neo import Graph

from hyperblend.models.molecule import Molecule
from hyperblend.repository.molecule_repository import MoleculeRepository
from hyperblend.utils.http_utils import HttpClient
from .base_service import BaseExternalService


class PubChemService(BaseExternalService):
    """Service for fetching chemical data from PubChem."""

    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    def __init__(
        self,
        graph: Optional[Graph] = None,
        molecule_repository: Optional[MoleculeRepository] = None,
    ):
        """
        Initialize the PubChem service.

        Args:
            graph: Neo4j graph database connection
            molecule_repository: Repository for molecule operations
        """
        super().__init__(self.BASE_URL)
        self.logger = logging.getLogger(__name__)
        self.molecule_repository = molecule_repository or MoleculeRepository(graph)

    def health_check(self) -> bool:
        """
        Check if the PubChem service is available.

        Returns:
            bool: True if service is available, False otherwise
        """
        try:
            response = self._make_request("ping")
            return response is not None and "Ping" in str(response)
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False

    def search_molecule_by_name(
        self, name: str, max_results: int = 5
    ) -> List[Molecule]:
        """
        Search for molecules by name in PubChem.

        Args:
            name: Name to search for
            max_results: Maximum number of results to return

        Returns:
            List[Molecule]: List of found molecules
        """
        try:
            # Search by name
            results = pcp.get_compounds(name, "name")[:max_results]

            molecules = []
            for result in results:
                # Ensure the result is a valid Compound object before processing
                if not hasattr(result, "cid"):
                    self.logger.warning(f"Skipping invalid PubChem result without CID")
                    continue

                molecule = self._convert_to_molecule(result)
                if molecule:
                    # Extract synonyms (safely check for attributes)
                    synonyms = []
                    if hasattr(result, "synonyms") and result.synonyms:
                        synonyms = result.synonyms
                    if hasattr(result, "iupac_name") and result.iupac_name:
                        synonyms.append(result.iupac_name)

                    # Store in database
                    properties = molecule.model_dump(exclude_none=True)
                    properties["synonyms"] = synonyms
                    self.molecule_repository.create_molecule(
                        properties, source="PubChem"
                    )
                    molecules.append(molecule)

            return molecules

        except Exception as e:
            self.logger.error(f"Error searching molecule by name: {str(e)}")
            return []

    def get_molecule_by_cid(self, cid: int) -> Optional[Molecule]:
        """
        Get molecule details by PubChem CID and store in database.

        Args:
            cid: PubChem compound identifier

        Returns:
            Optional[Molecule]: Molecule if found, None otherwise
        """
        try:
            result = pcp.Compound.from_cid(cid)
            if result:
                molecule = self._convert_to_molecule(result)
                if molecule:
                    # Extract synonyms
                    synonyms = result.synonyms if hasattr(result, "synonyms") else []
                    if result.iupac_name:
                        synonyms.append(result.iupac_name)

                    # Store in database
                    properties = molecule.model_dump(exclude_none=True)
                    properties["synonyms"] = synonyms
                    self.molecule_repository.create_molecule(
                        properties, source="PubChem"
                    )
                    return molecule

            return None

        except Exception as e:
            self.logger.error(f"Error getting molecule by CID: {str(e)}")
            return None

    def search_molecule_by_smiles(self, smiles: str) -> Optional[Molecule]:
        """
        Search for molecule by SMILES in PubChem and store in database.

        Args:
            smiles: SMILES string of the molecule

        Returns:
            Optional[Molecule]: Molecule if found, None otherwise
        """
        try:
            results = pcp.get_compounds(smiles, "smiles")
            if results:
                # Ensure the result is a valid Compound object before processing
                result = results[0]  # Take the first match
                if not hasattr(result, "cid"):
                    self.logger.warning(f"Invalid PubChem result without CID")
                    return None

                molecule = self._convert_to_molecule(result)
                if molecule:
                    # Extract synonyms (safely check for attributes)
                    synonyms = []
                    if hasattr(result, "synonyms") and result.synonyms:
                        synonyms = result.synonyms
                    if hasattr(result, "iupac_name") and result.iupac_name:
                        synonyms.append(result.iupac_name)

                    # Store in database
                    properties = molecule.model_dump(exclude_none=True)
                    properties["synonyms"] = synonyms
                    self.molecule_repository.create_molecule(
                        properties, source="PubChem"
                    )
                    return molecule

            return None

        except Exception as e:
            self.logger.error(f"Error searching molecule by SMILES: {str(e)}")
            return None

    def get_molecule_by_inchikey(self, inchikey: str) -> Optional[Molecule]:
        """
        Get molecule details by InChI Key from PubChem.

        Args:
            inchikey: InChI Key of the molecule

        Returns:
            Optional[Molecule]: Molecule if found, None otherwise
        """
        try:
            results = pcp.get_compounds(inchikey, "inchikey")
            if results:
                # Ensure the result is a valid Compound object before processing
                result = results[0]  # Take the first match
                if not hasattr(result, "cid"):
                    self.logger.warning(f"Invalid PubChem result without CID")
                    return None

                molecule = self._convert_to_molecule(result)
                return molecule
            return None
        except Exception as e:
            self.logger.error(f"Error getting molecule by InChI Key: {str(e)}")
            return None

    def enrich_molecule(self, identifiers):
        """
        Enrich a molecule with data from PubChem based on provided identifiers.

        Args:
            identifiers (dict): Dictionary of identifiers with keys like 'inchikey', 'smiles', 'name'

        Returns:
            dict: Enriched molecule data or None if no data found
        """
        self.logger.info(f"Enriching molecule with identifiers: {identifiers}")

        molecule = None

        # Try to get molecule by PubChem CID first (most reliable)
        if identifiers.get("pubchem_cid"):
            try:
                self.logger.info(
                    f"Searching by PubChem CID: {identifiers['pubchem_cid']}"
                )
                molecule = self.get_molecule_by_cid(identifiers["pubchem_cid"])
                if molecule:
                    self.logger.info("Found molecule by PubChem CID")
            except Exception as e:
                self.logger.warning(f"Error finding by PubChem CID: {str(e)}")

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

        # If still not found, try by name - use exact match first
        if not molecule and identifiers.get("name"):
            try:
                name = identifiers["name"]
                self.logger.info(f"Searching by name (exact): {name}")

                # Try exact match first
                try:
                    # PubChem's exact name search
                    exact_results = pcp.get_compounds(name, "name", "substance")
                    if exact_results and len(exact_results) > 0:
                        molecule = self._convert_to_molecule(exact_results[0])
                        if molecule:
                            self.logger.info("Found molecule by exact name match")
                except Exception as e:
                    self.logger.warning(f"Error in exact name search: {str(e)}")

                # If exact match failed, try known specific drug names with direct CID mapping
                if not molecule:
                    # Common psychoactive substances with known CIDs
                    known_substances = {
                        "mescaline": "4076",
                        "lsd": "5761",
                        "psilocybin": "10624",
                        "dmt": "6089",
                        "mdma": "1615",
                        "cocaine": "5760",
                        "morphine": "5288826",
                        "caffeine": "2519",
                        "nicotine": "89594",
                        "thc": "16078",
                        "ketamine": "3821",
                    }

                    # Normalize name (lowercase, remove spaces)
                    normalized_name = name.lower().strip()

                    # Check if this is a known substance
                    if normalized_name in known_substances:
                        cid = known_substances[normalized_name]
                        self.logger.info(
                            f"Found known substance match for '{normalized_name}' with CID {cid}"
                        )
                        try:
                            molecule = self.get_molecule_by_cid(cid)
                            if molecule:
                                self.logger.info(
                                    f"Successfully retrieved molecule for known substance '{normalized_name}'"
                                )
                        except Exception as e:
                            self.logger.warning(
                                f"Error retrieving known substance: {str(e)}"
                            )

                # If still not found, try fuzzy search
                if not molecule:
                    self.logger.info(f"Trying fuzzy name search for: {name}")
                    molecules = self.search_molecule_by_name(name)
                    if molecules and len(molecules) > 0:
                        molecule = molecules[0]
                        self.logger.info("Found molecule by fuzzy name search")
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
                "pubchem_cid": molecule_dict.get("pubchem_cid"),
            },
        }

        return enriched

    def _convert_to_molecule(self, pubchem_data) -> Optional[Molecule]:
        """
        Convert PubChem compound data to our Molecule model.
        Safely handles different types of PubChem data.

        Args:
            pubchem_data: PubChem compound data

        Returns:
            Optional[Molecule]: Our internal molecule model
        """
        try:
            # Make sure we have a valid object with a CID
            if not hasattr(pubchem_data, "cid"):
                self.logger.warning("Invalid PubChem data without CID")
                return None

            # Get molecular weight (safely)
            mol_weight = 0.0
            try:
                if hasattr(pubchem_data, "molecular_weight"):
                    mol_weight = float(pubchem_data.molecular_weight)
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Error converting molecular weight: {str(e)}")

            # Get XLogP (safely)
            logp = 0.0
            try:
                if hasattr(pubchem_data, "xlogp"):
                    logp = float(pubchem_data.xlogp)
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Error converting XLogP: {str(e)}")

            # Get TPSA (safely)
            tpsa = 0.0
            try:
                if hasattr(pubchem_data, "tpsa"):
                    tpsa = float(pubchem_data.tpsa)
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Error converting TPSA: {str(e)}")

            # Get the most common name from synonyms, falling back to IUPAC name or CID
            name = None
            if (
                hasattr(pubchem_data, "synonyms")
                and pubchem_data.synonyms
                and len(pubchem_data.synonyms) > 0
            ):
                name = pubchem_data.synonyms[
                    0
                ]  # First synonym is typically the most common name
            if (
                not name
                and hasattr(pubchem_data, "iupac_name")
                and pubchem_data.iupac_name
            ):
                name = pubchem_data.iupac_name
            if not name:
                name = f"Compound {str(pubchem_data.cid)}"

            # Get DrugBank ID if available (safely)
            drugbank_id = None
            if hasattr(pubchem_data, "synonyms") and pubchem_data.synonyms:
                for synonym in pubchem_data.synonyms:
                    if (
                        isinstance(synonym, str)
                        and synonym.startswith("DB")
                        and len(synonym) == 7
                        and synonym[2:].isdigit()
                    ):
                        drugbank_id = synonym
                        break

            # Get SMILES (safely)
            smiles = ""
            if (
                hasattr(pubchem_data, "canonical_smiles")
                and pubchem_data.canonical_smiles
            ):
                smiles = pubchem_data.canonical_smiles
            elif (
                hasattr(pubchem_data, "isomeric_smiles")
                and pubchem_data.isomeric_smiles
            ):
                smiles = pubchem_data.isomeric_smiles

            # Get InChI (safely)
            inchi = ""
            if hasattr(pubchem_data, "inchi") and pubchem_data.inchi:
                inchi = pubchem_data.inchi

            # Get InChI Key (safely)
            inchikey = ""
            if hasattr(pubchem_data, "inchikey") and pubchem_data.inchikey:
                inchikey = pubchem_data.inchikey

            # Create molecule
            molecule = Molecule(
                id=f"MOL_PUBCHEM_{pubchem_data.cid}",
                name=name,
                formula=getattr(pubchem_data, "molecular_formula", ""),
                molecular_weight=mol_weight,
                smiles=smiles,
                inchi=inchi,
                inchikey=inchikey,
                pubchem_cid=str(pubchem_data.cid),
                chembl_id=None,  # Not available from PubChem directly
                drugbank_id=drugbank_id,  # Add the DrugBank ID if found
                logp=logp,
                polar_surface_area=tpsa,
                known_activities=[],  # Would need additional processing
            )

            return molecule

        except Exception as e:
            self.logger.error(f"Error converting PubChem data to molecule: {str(e)}")
            return None
