"""Service for querying organisms from the internal database."""

import logging
from typing import List, Optional, Dict, Any
from py2neo import Graph

from hyperblend.repository.organism_repository import OrganismRepository
from hyperblend.repository.molecule_repository import MoleculeRepository
from .base_service import BaseService

logger = logging.getLogger(__name__)


class OrganismService(BaseService):
    """Service for handling organism-related operations."""

    def __init__(
        self,
        graph: Optional[Graph] = None,
        organism_repository: Optional[OrganismRepository] = None,
        molecule_repository: Optional[MoleculeRepository] = None,
    ):
        """Initialize the organism service.

        Args:
            graph: Neo4j graph database connection
            organism_repository: Repository for organism operations
            molecule_repository: Repository for molecule operations
        """
        super().__init__(graph)
        self.logger = logging.getLogger(__name__)
        self.organism_repository = organism_repository or OrganismRepository(graph)
        self.molecule_repository = molecule_repository or MoleculeRepository(graph)

    def get_organism(self, organism_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific organism by ID.

        Args:
            organism_id: The ID of the organism to retrieve

        Returns:
            Dictionary containing organism details and related molecules
        """
        try:
            organism = self.organism_repository.find_organism_by_id(organism_id)
            if not organism:
                return None

            # Get associated molecules
            molecules = self.organism_repository.get_organism_molecules(organism_id)

            # Format the result
            result = {
                "id": organism.get("id"),
                "name": organism.get("name"),
                "description": organism.get("description"),
                "taxonomy": organism.get("taxonomy"),
                "molecules": molecules,
            }

            return result
        except Exception as e:
            self.logger.error(f"Error getting organism {organism_id}: {str(e)}")
            return None

    def get_all_organisms(self) -> List[Dict[str, Any]]:
        """
        Get all organisms.

        Returns:
            List of dictionaries containing organism details
        """
        try:
            organisms = self.organism_repository.get_all_organisms()
            return [
                {
                    "id": org.get("id"),
                    "name": org.get("name"),
                    "description": org.get("description"),
                    "taxonomy": org.get("taxonomy"),
                }
                for org in organisms
            ]
        except Exception as e:
            self.logger.error(f"Error getting all organisms: {str(e)}")
            return []

    def search_organisms(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for organisms by name, description, or taxonomy.

        Args:
            query: Search query string

        Returns:
            List of dictionaries containing matching organism details
        """
        try:
            organisms = self.organism_repository.search_organisms(query)
            return [
                {
                    "id": org.get("id"),
                    "name": org.get("name"),
                    "description": org.get("description"),
                    "taxonomy": org.get("taxonomy"),
                }
                for org in organisms
            ]
        except Exception as e:
            self.logger.error(f"Error searching organisms with query {query}: {str(e)}")
            return []

    def find_by_name(self, name: str, exact: bool = False) -> List[Dict[str, Any]]:
        """
        Find organisms by name.

        Args:
            name: Name to search for
            exact: Whether to perform exact match (default: False)

        Returns:
            List[Dict[str, Any]]: List of organisms found
        """
        try:
            organisms = self.organism_repository.find_organisms_by_name(
                name, exact_match=exact
            )
            return organisms
        except Exception as e:
            self.logger.error(f"Error finding organisms by name: {str(e)}")
            return []

    def find_by_rank(self, rank: str) -> List[Dict[str, Any]]:
        """
        Find organisms by taxonomic rank.

        Args:
            rank: Taxonomic rank to filter by

        Returns:
            List[Dict[str, Any]]: List of organisms found
        """
        try:
            organisms = self.organism_repository.find_organisms_by_rank(rank)
            return organisms
        except Exception as e:
            self.logger.error(f"Error finding organisms by rank: {str(e)}")
            return []

    def find_by_source(self, source: str) -> List[Dict[str, Any]]:
        """
        Find organisms from a specific source.

        Args:
            source: Source name to filter by

        Returns:
            List[Dict[str, Any]]: List of organisms found
        """
        try:
            organisms = self.organism_repository.find_organisms_by_source(source)
            return organisms
        except Exception as e:
            self.logger.error(f"Error finding organisms by source: {str(e)}")
            return []

    def get_organism_molecules(self, organism_id: str) -> List[Dict[str, Any]]:
        """
        Get molecules associated with an organism.

        Args:
            organism_id: ID of the organism

        Returns:
            List[Dict[str, Any]]: List of molecules
        """
        try:
            molecules = self.organism_repository.get_organism_molecules(organism_id)
            return molecules
        except Exception as e:
            self.logger.error(f"Error getting organism molecules: {str(e)}")
            return []

    def create_organism(
        self, properties: Dict[str, Any], source: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new organism.

        Args:
            properties: Dictionary of organism properties
            source: Optional source of the organism data

        Returns:
            Optional[Dict[str, Any]]: Created organism or None if failed
        """
        try:
            organism = self.organism_repository.create_organism(properties, source)
            return organism
        except Exception as e:
            self.logger.error(f"Error creating organism: {str(e)}")
            return None

    def update_organism(
        self, organism_id: str, properties: Dict[str, Any], source: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing organism.

        Args:
            organism_id: ID of the organism to update
            properties: Updated properties
            source: Optional source of the data

        Returns:
            Optional[Dict[str, Any]]: Updated organism or None if failed
        """
        try:
            organism = self.organism_repository.update_organism(
                organism_id, properties, source
            )
            return organism
        except Exception as e:
            self.logger.error(f"Error updating organism: {str(e)}")
            return None

    def delete_organism(self, organism_id: str) -> bool:
        """
        Delete an organism.

        Args:
            organism_id: ID of the organism to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            return self.organism_repository.delete_organism(organism_id)
        except Exception as e:
            self.logger.error(f"Error deleting organism: {str(e)}")
            return False

    def link_molecule_to_organism(
        self, organism_id: str, molecule_id: str, relationship_type: str = "PRODUCES"
    ) -> bool:
        """
        Link a molecule to an organism.

        Args:
            organism_id: ID of the organism
            molecule_id: ID of the molecule
            relationship_type: Type of relationship

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            return self.organism_repository.link_molecule_to_organism(
                organism_id=organism_id,
                molecule_id=molecule_id,
                relationship_type=relationship_type,
            )
        except Exception as e:
            self.logger.error(f"Error linking molecule to organism: {str(e)}")
            return False

    def _format_organism_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format organism result for API response.

        Args:
            result: Raw result from the database

        Returns:
            Dict[str, Any]: Formatted organism data
        """
        if not result or "o" not in result:
            return {}

        organism = dict(result["o"])
        organism.update(
            {
                "id": organism.get("id"),
                "sources": result.get("sources", []),
                "molecule_count": result.get("molecule_count", 0),
            }
        )

        return organism
