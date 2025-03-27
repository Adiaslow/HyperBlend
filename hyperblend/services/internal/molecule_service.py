"""Service for querying molecules from the internal database."""

import logging
from typing import List, Optional, Dict, Any
from py2neo import Graph
from hyperblend.app.web.core.exceptions import ResourceNotFoundError
from .base_service import BaseService
from hyperblend.models.molecule import Molecule
from hyperblend.repository.molecule_repository import MoleculeRepository
from hyperblend.services.external.pubchem_service import PubChemService
from hyperblend.services.external.chembl_service import ChEMBLService
from hyperblend.services.external.drugbank_service import DrugBankService
from hyperblend.utils.entity_utils import EntityUtils

logger = logging.getLogger(__name__)


class MoleculeService(BaseService):
    """Service for querying molecules from the database."""

    def __init__(
        self,
        graph: Graph,
        molecule_repository: Optional[MoleculeRepository] = None,
        drugbank_api_key: Optional[str] = None,
    ):
        """
        Initialize the molecule service.

        Args:
            graph: Neo4j graph database connection
            molecule_repository: Optional molecule repository (will be created if None)
            drugbank_api_key: Optional DrugBank API key
        """
        super().__init__(graph)
        self.logger = logging.getLogger(__name__)

        # Initialize repository
        self.molecule_repository = molecule_repository or MoleculeRepository(graph)

        # Initialize external services
        try:
            self.pubchem_service = PubChemService(graph)
            self.logger.info("PubChem service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize PubChem service: {str(e)}")
            self.pubchem_service = None

        try:
            self.chembl_service = ChEMBLService(graph)
            self.logger.info("ChEMBL service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize ChEMBL service: {str(e)}")
            self.chembl_service = None

        try:
            self.drugbank_service = (
                DrugBankService(api_key=drugbank_api_key, graph=graph)
                if drugbank_api_key
                else None
            )
            if self.drugbank_service:
                self.logger.info("DrugBank service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize DrugBank service: {str(e)}")
            self.drugbank_service = None

    def find_by_name(self, name: str, exact: bool = False) -> List[Dict[str, Any]]:
        """
        Find molecules by name.

        Args:
            name: Name to search for
            exact: Whether to perform exact match (default: False)

        Returns:
            List[Dict[str, Any]]: List of molecules found
        """
        try:
            molecules = self.molecule_repository.find_molecules_by_name(name, exact)

            # Add synonyms and sources for each molecule
            formatted_molecules = []
            for molecule in molecules:
                molecule_id = molecule.get("id")
                if molecule_id:
                    synonyms = self._get_molecule_synonyms(molecule_id)
                    sources = self._get_molecule_sources(molecule_id)
                    formatted = molecule.copy()
                    formatted["synonyms"] = synonyms
                    formatted["sources"] = sources
                    formatted_molecules.append(formatted)

            return formatted_molecules
        except Exception as e:
            self.logger.error(f"Error finding molecules by name: {str(e)}")
            return []

    def find_by_inchikey(self, inchikey: str) -> Optional[Dict[str, Any]]:
        """
        Find molecule by InChIKey.

        Args:
            inchikey: InChIKey to search for

        Returns:
            Optional[Dict[str, Any]]: Molecule if found, None otherwise
        """
        try:
            molecule = self.molecule_repository.find_molecule_by_inchikey(inchikey)
            if not molecule:
                return None

            # Add synonyms and sources
            molecule_id = molecule.get("id")
            if molecule_id:
                synonyms = self._get_molecule_synonyms(molecule_id)
                sources = self._get_molecule_sources(molecule_id)
                formatted = molecule.copy()
                formatted["synonyms"] = synonyms
                formatted["sources"] = sources
                return formatted

            return molecule
        except Exception as e:
            self.logger.error(f"Error finding molecule by InChIKey: {str(e)}")
            return None

    def find_by_source(self, source: str) -> List[Dict[str, Any]]:
        """
        Find molecules from a specific source.

        Args:
            source: Source name to filter by

        Returns:
            List[Dict[str, Any]]: List of molecules found
        """
        try:
            molecules = self.molecule_repository.find_molecules_by_source(source)

            # Add synonyms and sources for each molecule
            formatted_molecules = []
            for molecule in molecules:
                molecule_id = molecule.get("id")
                if molecule_id:
                    synonyms = self._get_molecule_synonyms(molecule_id)
                    sources = self._get_molecule_sources(molecule_id)
                    formatted = molecule.copy()
                    formatted["synonyms"] = synonyms
                    formatted["sources"] = sources
                    formatted_molecules.append(formatted)

            return formatted_molecules
        except Exception as e:
            self.logger.error(f"Error finding molecules by source: {str(e)}")
            return []

    def find_similar_molecules(
        self, molecule_id: str, threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Find molecules similar to the given one based on properties.

        Args:
            molecule_id: ID of the reference molecule
            threshold: Similarity threshold (0-1, default: 0.7)

        Returns:
            List[Dict[str, Any]]: List of similar molecules
        """
        try:
            # Use repository to find similar molecules
            similar_molecules = self.molecule_repository.find_similar_molecules(
                molecule_id, threshold
            )

            # Add synonyms and sources for each molecule
            formatted_molecules = []
            for molecule in similar_molecules:
                molecule_id = molecule.get("id")
                if molecule_id:
                    synonyms = self._get_molecule_synonyms(molecule_id)
                    sources = self._get_molecule_sources(molecule_id)
                    formatted = molecule.copy()
                    formatted["synonyms"] = synonyms
                    formatted["sources"] = sources
                    formatted_molecules.append(formatted)

            return formatted_molecules
        except Exception as e:
            self.logger.error(f"Error finding similar molecules: {str(e)}")
            return []

    def get_molecule(self, molecule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a molecule by ID.

        Args:
            molecule_id: ID of the molecule to retrieve

        Returns:
            Dictionary containing molecule details or None if not found
        """
        try:
            self.logger.debug(f"Getting molecule with ID: {molecule_id}")
            molecule = self.molecule_repository.find_molecule_by_id(molecule_id)

            if not molecule:
                return None

            # Add synonyms, sources, targets, and effects
            molecule_id = molecule.get("id")
            if molecule_id:
                # Add extra data
                molecule["synonyms"] = self._get_molecule_synonyms(molecule_id)
                molecule["sources"] = self._get_molecule_sources(molecule_id)
                molecule["targets"] = self.molecule_repository.get_molecule_targets(
                    molecule_id
                )
                molecule["effects"] = self._get_molecule_effects(molecule_id)

            return molecule
        except Exception as e:
            self.logger.error(f"Error getting molecule: {str(e)}")
            return None

    def create_molecule(
        self, molecule: Molecule, source: str
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new molecule.

        Args:
            molecule: Molecule data
            source: Source of the molecule data

        Returns:
            Optional[Dict[str, Any]]: Created molecule data or None if failed
        """
        try:
            return self.molecule_repository.create_molecule(molecule, source)
        except Exception as e:
            self.logger.error(f"Error creating molecule: {str(e)}")
            return None

    def update_molecule(
        self, molecule_id: str, molecule: Molecule, source: str
    ) -> Optional[Dict[str, Any]]:
        """
        Update a molecule.

        Args:
            molecule_id: Molecule ID
            molecule: Updated molecule data
            source: Source of the molecule data

        Returns:
            Optional[Dict[str, Any]]: Updated molecule data or None if failed
        """
        try:
            return self.molecule_repository.update_molecule(
                molecule_id, molecule, source
            )
        except Exception as e:
            self.logger.error(f"Error updating molecule: {str(e)}")
            return None

    def delete_molecule(self, molecule_id: str) -> bool:
        """
        Delete a molecule.

        Args:
            molecule_id: Molecule ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            return self.molecule_repository.delete_molecule(molecule_id)
        except Exception as e:
            self.logger.error(f"Error deleting molecule: {str(e)}")
            return False

    def _get_molecule_synonyms(self, molecule_id: str) -> List[str]:
        """
        Get synonyms for a molecule.

        Args:
            molecule_id: Molecule ID

        Returns:
            List[str]: List of synonyms
        """
        try:
            query = """
            MATCH (m:Molecule {id: $id})-[:HAS_SYNONYM]->(s:Synonym)
            RETURN s.name as synonym
            """
            results = self.run_query(query, {"id": molecule_id})
            return [result["synonym"] for result in results if result.get("synonym")]
        except Exception as e:
            self.logger.error(f"Error getting molecule synonyms: {str(e)}")
            return []

    def _get_molecule_sources(self, molecule_id: str) -> List[str]:
        """
        Get sources for a molecule.

        Args:
            molecule_id: Molecule ID

        Returns:
            List[str]: List of sources
        """
        try:
            query = """
            MATCH (m:Molecule {id: $id})-[:FROM_SOURCE]->(s:Source)
            RETURN s.name as source
            """
            results = self.run_query(query, {"id": molecule_id})
            return [result["source"] for result in results if result.get("source")]
        except Exception as e:
            self.logger.error(f"Error getting molecule sources: {str(e)}")
            return []

    def _get_molecule_effects(self, molecule_id: str) -> List[Dict[str, Any]]:
        """
        Get effects for a molecule.

        Args:
            molecule_id: Molecule ID

        Returns:
            List[Dict[str, Any]]: List of effects
        """
        try:
            query = """
            MATCH (m:Molecule {id: $id})-[r:HAS_EFFECT]->(e:Effect)
            RETURN e, properties(r) as relationship_properties
            """
            results = self.run_query(query, {"id": molecule_id})

            effects = []
            for result in results:
                if result.get("e"):
                    effect_data = dict(result["e"])
                    effect_data["relationship"] = result.get(
                        "relationship_properties", {}
                    )
                    effects.append(effect_data)

            return effects
        except Exception as e:
            self.logger.error(f"Error getting molecule effects: {str(e)}")
            return []

    def get_all_molecules(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all molecules up to a limit.

        Args:
            limit: Maximum number of molecules to return

        Returns:
            List[Dict[str, Any]]: List of molecules
        """
        try:
            self.logger.debug(f"Getting all molecules with limit {limit}")
            molecules = self.molecule_repository.find_all(limit=limit)

            # Add synonyms and sources for each molecule
            formatted_molecules = []
            for molecule in molecules:
                molecule_id = molecule.get("id")
                if molecule_id:
                    try:
                        synonyms = self._get_molecule_synonyms(molecule_id)
                        sources = self._get_molecule_sources(molecule_id)
                        formatted = molecule.copy()
                        formatted["synonyms"] = synonyms
                        formatted["sources"] = sources
                        formatted_molecules.append(formatted)
                    except Exception as e:
                        self.logger.warning(
                            f"Error formatting molecule {molecule_id}: {str(e)}"
                        )
                        # Still include the molecule even if we can't get synonyms/sources
                        formatted_molecules.append(molecule)
                else:
                    formatted_molecules.append(molecule)

            self.logger.debug(f"Returning {len(formatted_molecules)} molecules")
            return formatted_molecules
        except Exception as e:
            self.logger.error(f"Error getting all molecules: {str(e)}")
            return []

    def search_molecules(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for molecules by name, formula, or SMILES.

        Args:
            query: Search query

        Returns:
            List[Dict[str, Any]]: List of matching molecules
        """
        try:
            self.logger.debug(f"Searching molecules with query: {query}")
            # Use the repository's find_by_name method which already handles pattern matching
            return self.find_by_name(query, exact=False)
        except Exception as e:
            self.logger.error(f"Error searching molecules: {str(e)}")
            return []

    def update_molecule_properties(
        self, molecule_id: str, properties: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update specific properties of a molecule.

        Args:
            molecule_id: ID of the molecule to update
            properties: Dictionary of properties to update

        Returns:
            Optional[Dict[str, Any]]: Updated molecule data or None if failed
        """
        try:
            self.logger.debug(f"Updating properties for molecule {molecule_id}")

            # First get the current molecule
            current_molecule = self.molecule_repository.find_molecule_by_id(molecule_id)
            if not current_molecule:
                self.logger.error(f"Molecule with ID {molecule_id} not found")
                return None

            # Merge properties with current data
            update_data = {**current_molecule, **properties}

            # Remove ID from update data to avoid conflicts
            if "id" in update_data:
                del update_data["id"]

            # Update the molecule
            updated = self.molecule_repository.update_molecule(
                molecule_id, update_data, "API"
            )

            if updated:
                self.logger.info(
                    f"Successfully updated properties for molecule {molecule_id}"
                )
                return updated
            else:
                self.logger.error(
                    f"Failed to update properties for molecule {molecule_id}"
                )
                return None
        except Exception as e:
            self.logger.error(f"Error updating molecule properties: {str(e)}")
            self.logger.exception(e)
            return None
