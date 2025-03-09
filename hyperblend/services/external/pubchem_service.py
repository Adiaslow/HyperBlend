"""PubChem service for retrieving chemical data."""

import logging
from typing import List, Optional, Dict, Any, Union
import pubchempy as pcp
from py2neo import Graph

from hyperblend.database.entry_manager import DatabaseEntryManager
from hyperblend.models.molecule import Molecule
from .base_service import BaseExternalService


class PubChemService(BaseExternalService):
    """Service for fetching chemical data from PubChem."""

    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    def __init__(self, graph: Graph):
        """
        Initialize the PubChem service.

        Args:
            graph: Neo4j graph database connection
        """
        super().__init__(self.BASE_URL)
        self.graph = graph
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseEntryManager(graph)

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
        Search for molecules by name in PubChem and store results in database.

        Args:
            name: Name of the molecule to search for
            max_results: Maximum number of results to return

        Returns:
            List[Molecule]: List of molecules found
        """
        try:
            # Search by name
            results = pcp.get_compounds(name, "name", listkey_count=max_results)

            molecules = []
            for result in results:
                molecule = self._convert_to_molecule(result)
                if molecule:
                    # Extract synonyms
                    synonyms = result.synonyms if hasattr(result, "synonyms") else []
                    if result.iupac_name:
                        synonyms.append(result.iupac_name)

                    # Store in database
                    db_molecule = self.db_manager.create_or_update_molecule(
                        molecule=molecule, source="PubChem"
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
                    db_molecule = self.db_manager.create_or_update_molecule(
                        molecule=molecule, source="PubChem"
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
                result = results[0]  # Take the first match
                molecule = self._convert_to_molecule(result)
                if molecule:
                    # Extract synonyms
                    synonyms = result.synonyms if hasattr(result, "synonyms") else []
                    if result.iupac_name:
                        synonyms.append(result.iupac_name)

                    # Store in database
                    db_molecule = self.db_manager.create_or_update_molecule(
                        molecule=molecule, source="PubChem"
                    )
                    return molecule

            return None

        except Exception as e:
            self.logger.error(f"Error searching molecule by SMILES: {str(e)}")
            return None

    def _convert_to_molecule(self, pubchem_data: pcp.Compound) -> Optional[Molecule]:
        """
        Convert PubChem compound data to our Molecule model.

        Args:
            pubchem_data: PubChem compound data

        Returns:
            Optional[Molecule]: Our internal molecule model
        """
        try:
            # Get molecular weight
            mol_weight = (
                pubchem_data.molecular_weight
                if hasattr(pubchem_data, "molecular_weight")
                else 0.0
            )

            # Get XLogP
            logp = pubchem_data.xlogp if hasattr(pubchem_data, "xlogp") else 0.0

            # Get TPSA
            tpsa = pubchem_data.tpsa if hasattr(pubchem_data, "tpsa") else 0.0

            # Get the most common name from synonyms, falling back to IUPAC name or CID
            name = None
            if hasattr(pubchem_data, "synonyms") and pubchem_data.synonyms:
                name = pubchem_data.synonyms[
                    0
                ]  # First synonym is typically the most common name
            if not name and hasattr(pubchem_data, "iupac_name"):
                name = pubchem_data.iupac_name
            if not name:
                name = str(pubchem_data.cid)

            # Get DrugBank ID if available
            drugbank_id = None
            if hasattr(pubchem_data, "synonyms"):
                for synonym in pubchem_data.synonyms:
                    if (
                        synonym.startswith("DB")
                        and len(synonym) == 7
                        and synonym[2:].isdigit()
                    ):
                        drugbank_id = synonym
                        break

            molecule = Molecule(
                id=f"MOL_PUBCHEM_{pubchem_data.cid}",
                name=name,
                formula=(
                    pubchem_data.molecular_formula
                    if hasattr(pubchem_data, "molecular_formula")
                    else ""
                ),
                molecular_weight=mol_weight,
                smiles=(
                    pubchem_data.canonical_smiles
                    if hasattr(pubchem_data, "canonical_smiles")
                    else ""
                ),
                inchi=pubchem_data.inchi if hasattr(pubchem_data, "inchi") else "",
                inchikey=(
                    pubchem_data.inchikey if hasattr(pubchem_data, "inchikey") else ""
                ),
                pubchem_cid=str(pubchem_data.cid),
                chembl_id=None,  # Would need to cross-reference with ChEMBL
                drugbank_id=drugbank_id,  # Add DrugBank ID if found
                logp=logp,
                polar_surface_area=tpsa,
                known_activities=[],  # Would need additional processing
            )

            return molecule

        except Exception as e:
            self.logger.error(f"Error converting PubChem data to molecule: {str(e)}")
            self.logger.debug(f"Problematic data: {pubchem_data}")
            return None
