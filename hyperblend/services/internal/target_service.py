"""Service for querying targets from the internal database."""

import logging
from typing import List, Optional, Dict, Any
from py2neo import Graph
from .base_service import BaseService
from ..external.uniprot_service import UniProtService
from hyperblend.app.web.core.exceptions import ResourceNotFoundError
from hyperblend.repository.target_repository import TargetRepository
from hyperblend.utils.entity_utils import EntityUtils

logger = logging.getLogger(__name__)


class TargetService(BaseService):
    """Service for querying targets from the database."""

    def __init__(
        self, graph: Graph, target_repository: Optional[TargetRepository] = None
    ):
        """
        Initialize the target service.

        Args:
            graph: Neo4j graph database connection
            target_repository: Optional target repository (will be created if None)
        """
        super().__init__(graph)
        self.logger = logging.getLogger(__name__)

        # Initialize repository
        self.target_repository = target_repository or TargetRepository(graph)

        # Initialize external services
        self.uniprot_service = UniProtService()

    def get_all_targets(self) -> List[Dict[str, Any]]:
        """
        Get all targets from the database.

        Returns:
            List of target dictionaries
        """
        try:
            return self.target_repository.find_all("Target", 1000)
        except Exception as e:
            self.logger.error(f"Error getting all targets: {str(e)}")
            return []

    def search_targets(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for targets by name, description, or type.

        Args:
            query: Search term

        Returns:
            List of matching target dictionaries
        """
        try:
            # Search across multiple fields
            return self.target_repository.search_by_text(
                "Target", query, ["name", "description", "type"], 100
            )
        except Exception as e:
            self.logger.error(f"Error searching targets: {str(e)}")
            return []

    def get_target(self, target_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific target by ID.

        Args:
            target_id: The ID of the target to retrieve

        Returns:
            Dictionary containing target details and related molecules
        """
        try:
            # Get target by ID
            target = self.target_repository.find_target_by_id(target_id)

            if not target:
                return None

            # Add associated molecules
            molecules = self.target_repository.get_target_molecules(target_id)
            target["molecules"] = molecules

            # Add synonyms and sources
            target["synonyms"] = self._get_target_synonyms(target_id)
            target["sources"] = self._get_target_sources(target_id)

            return target
        except Exception as e:
            self.logger.error(f"Error getting target: {str(e)}")
            return None

    def get_target_molecules(self, target_id: str) -> List[Dict[str, Any]]:
        """
        Get molecules associated with a target.

        Args:
            target_id: Target ID

        Returns:
            List of molecule dictionaries
        """
        try:
            return self.target_repository.get_target_molecules(target_id)
        except Exception as e:
            self.logger.error(f"Error getting target molecules: {str(e)}")
            return []

    def update_target(
        self, target_id: str, target_data: Dict[str, Any], source: str = "manual"
    ) -> Optional[Dict[str, Any]]:
        """
        Update a target with new data.

        Args:
            target_id: Target ID
            target_data: New target data
            source: Source of the data (default: "manual")

        Returns:
            Updated target data or None if failed
        """
        try:
            return self.target_repository.update_target(target_id, target_data, source)
        except Exception as e:
            self.logger.error(f"Error updating target: {str(e)}")
            return None

    def find_by_name(self, name: str, exact: bool = False) -> List[Dict[str, Any]]:
        """
        Find targets by name.

        Args:
            name: Name to search for
            exact: Whether to perform exact match (default: False)

        Returns:
            List[Dict[str, Any]]: List of targets found
        """
        try:
            targets = self.target_repository.find_targets_by_name(name, exact)

            # Add synonyms and sources to each target
            formatted_targets = []
            for target in targets:
                target_id = target.get("id")
                if target_id:
                    synonyms = self._get_target_synonyms(target_id)
                    sources = self._get_target_sources(target_id)
                    molecule_count = self._get_target_molecule_count(target_id)

                    formatted = target.copy()
                    formatted["synonyms"] = synonyms
                    formatted["sources"] = sources
                    formatted["molecule_count"] = molecule_count
                    formatted_targets.append(formatted)

            return formatted_targets
        except Exception as e:
            self.logger.error(f"Error finding targets by name: {str(e)}")
            return []

    def find_by_type(self, target_type: str) -> List[Dict[str, Any]]:
        """
        Find targets by type (e.g., 'protein', 'enzyme', 'receptor').

        Args:
            target_type: Type of target to filter by

        Returns:
            List[Dict[str, Any]]: List of targets found
        """
        try:
            targets = self.target_repository.find_targets_by_type(target_type)

            # Add synonyms and sources to each target
            formatted_targets = []
            for target in targets:
                target_id = target.get("id")
                if target_id:
                    synonyms = self._get_target_synonyms(target_id)
                    sources = self._get_target_sources(target_id)
                    molecule_count = self._get_target_molecule_count(target_id)

                    formatted = target.copy()
                    formatted["synonyms"] = synonyms
                    formatted["sources"] = sources
                    formatted["molecule_count"] = molecule_count
                    formatted_targets.append(formatted)

            return formatted_targets
        except Exception as e:
            self.logger.error(f"Error finding targets by type: {str(e)}")
            return []

    def find_by_source(self, source: str) -> List[Dict[str, Any]]:
        """
        Find targets from a specific source.

        Args:
            source: Source name to filter by

        Returns:
            List[Dict[str, Any]]: List of targets found
        """
        try:
            targets = self.target_repository.find_targets_by_source(source)

            # Add synonyms and other sources to each target
            formatted_targets = []
            for target in targets:
                target_id = target.get("id")
                if target_id:
                    synonyms = self._get_target_synonyms(target_id)
                    all_sources = self._get_target_sources(target_id)
                    molecule_count = self._get_target_molecule_count(target_id)

                    formatted = target.copy()
                    formatted["synonyms"] = synonyms
                    formatted["sources"] = all_sources
                    formatted["molecule_count"] = molecule_count
                    formatted_targets.append(formatted)

            return formatted_targets
        except Exception as e:
            self.logger.error(f"Error finding targets by source: {str(e)}")
            return []

    def find_by_organism(self, organism: str) -> List[Dict[str, Any]]:
        """
        Find targets by organism.

        Args:
            organism: Organism name or taxonomy ID

        Returns:
            List[Dict[str, Any]]: List of targets found
        """
        try:
            targets = self.target_repository.find_targets_by_organism(organism)

            # Add synonyms and sources to each target
            formatted_targets = []
            for target in targets:
                target_id = target.get("id")
                if target_id:
                    synonyms = self._get_target_synonyms(target_id)
                    sources = self._get_target_sources(target_id)
                    molecule_count = self._get_target_molecule_count(target_id)

                    formatted = target.copy()
                    formatted["synonyms"] = synonyms
                    formatted["sources"] = sources
                    formatted["molecule_count"] = molecule_count
                    formatted_targets.append(formatted)

            return formatted_targets
        except Exception as e:
            self.logger.error(f"Error finding targets by organism: {str(e)}")
            return []

    def create_target(
        self, target_data: Dict[str, Any], source: str = "manual"
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new target.

        Args:
            target_data: Target data
            source: Source of the data (default: "manual")

        Returns:
            Created target data or None if failed
        """
        try:
            return self.target_repository.create_target(target_data, source)
        except Exception as e:
            self.logger.error(f"Error creating target: {str(e)}")
            return None

    def delete_target(self, target_id: str) -> bool:
        """
        Delete a target.

        Args:
            target_id: Target ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            return self.target_repository.delete_target(target_id)
        except Exception as e:
            self.logger.error(f"Error deleting target: {str(e)}")
            return False

    def _get_target_synonyms(self, target_id: str) -> List[str]:
        """
        Get synonyms for a target.

        Args:
            target_id: Target ID

        Returns:
            List[str]: List of synonyms
        """
        try:
            query = """
            MATCH (t:Target {id: $id})-[:HAS_SYNONYM]->(s:Synonym)
            RETURN s.name as synonym
            """
            results = self.run_query(query, {"id": target_id})
            return [result["synonym"] for result in results if result.get("synonym")]
        except Exception as e:
            self.logger.error(f"Error getting target synonyms: {str(e)}")
            return []

    def _get_target_sources(self, target_id: str) -> List[str]:
        """
        Get sources for a target.

        Args:
            target_id: Target ID

        Returns:
            List[str]: List of sources
        """
        try:
            query = """
            MATCH (t:Target {id: $id})-[:FROM_SOURCE]->(s:Source)
            RETURN s.name as source
            """
            results = self.run_query(query, {"id": target_id})
            return [result["source"] for result in results if result.get("source")]
        except Exception as e:
            self.logger.error(f"Error getting target sources: {str(e)}")
            return []

    def _get_target_molecule_count(self, target_id: str) -> int:
        """
        Get the number of molecules associated with a target.

        Args:
            target_id: Target ID

        Returns:
            int: Number of molecules
        """
        try:
            query = """
            MATCH (t:Target {id: $id})-[]->(m:Molecule)
            RETURN count(m) as count
            """
            results = self.run_query(query, {"id": target_id})
            return results[0].get("count", 0) if results else 0
        except Exception as e:
            self.logger.error(f"Error getting target molecule count: {str(e)}")
            return 0
