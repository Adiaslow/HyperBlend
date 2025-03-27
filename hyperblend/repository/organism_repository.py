"""Repository for organism database operations."""

import logging
from typing import List, Optional, Dict, Any
from py2neo import Graph

from hyperblend.repository.base_repository import BaseRepository


class OrganismRepository(BaseRepository):
    """Repository for organism-related database operations."""

    def __init__(self, graph: Optional[Graph] = None):
        """Initialize the repository with a database connection.

        Args:
            graph: Neo4j graph database connection
        """
        super().__init__(graph=graph, label="Organism")
        self.logger = logging.getLogger(__name__)

    def find_organism_by_id(self, organism_id: str) -> Optional[Dict[str, Any]]:
        """Find an organism by ID.

        Args:
            organism_id: ID of the organism

        Returns:
            Organism data or None if not found
        """
        try:
            return self.find_by_id(organism_id)
        except Exception as e:
            self.logger.error(f"Error finding organism by ID: {str(e)}")
            return None

    def find_organisms_by_name(
        self, name: str, exact_match: bool = False
    ) -> List[Dict[str, Any]]:
        """Find organisms by name.

        Args:
            name: Name to search for
            exact_match: Whether to perform exact match (True) or pattern match (False)

        Returns:
            List of organisms matching the name
        """
        try:
            if exact_match:
                return self.find_by_property("name", name)
            else:
                query = """
                MATCH (o:Organism)
                WHERE o.name =~ $pattern
                RETURN o
                """
                pattern = f"(?i).*{name}.*"
                results = self.db_utils.run_query(query, {"pattern": pattern})
                return [dict(record["o"]) for record in results]
        except Exception as e:
            self.logger.error(f"Error finding organisms by name: {str(e)}")
            return []

    def find_organisms_by_rank(self, rank: str) -> List[Dict[str, Any]]:
        """Find organisms by taxonomic rank.

        Args:
            rank: Taxonomic rank to filter by

        Returns:
            List of organisms with the specified rank
        """
        try:
            return self.find_by_property("rank", rank)
        except Exception as e:
            self.logger.error(f"Error finding organisms by rank: {str(e)}")
            return []

    def find_organisms_by_source(self, source: str) -> List[Dict[str, Any]]:
        """Find organisms from a specific source.

        Args:
            source: Source to filter by

        Returns:
            List of organisms from the specified source
        """
        try:
            query = """
            MATCH (o:Organism)-[:FROM_SOURCE]->(s:Source {name: $source})
            RETURN o
            """
            results = self.db_utils.run_query(query, {"source": source})
            return [dict(record["o"]) for record in results]
        except Exception as e:
            self.logger.error(f"Error finding organisms by source: {str(e)}")
            return []

    def get_all_organisms(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all organisms in the database.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of all organisms
        """
        try:
            return self.find_all(limit=limit)
        except Exception as e:
            self.logger.error(f"Error getting all organisms: {str(e)}")
            return []

    def search_organisms(self, query: str) -> List[Dict[str, Any]]:
        """Search for organisms by name, description, or taxonomy.

        Args:
            query: Search query string

        Returns:
            List of matching organisms
        """
        try:
            search_fields = ["name", "description", "taxonomy"]
            return self.search_by_text(query, search_fields, limit=100)
        except Exception as e:
            self.logger.error(f"Error searching organisms: {str(e)}")
            return []

    def get_organism_molecules(self, organism_id: str) -> List[Dict[str, Any]]:
        """Get molecules associated with an organism.

        Args:
            organism_id: ID of the organism

        Returns:
            List of molecules associated with the organism
        """
        try:
            query = """
            MATCH (o:Organism)-[r]->(m:Molecule)
            WHERE ID(o) = toInteger($id)
            RETURN m, type(r) as relationship_type
            """
            results = self.db_utils.run_query(query, {"id": organism_id})

            molecules = []
            for record in results:
                molecule = dict(record["m"])
                molecule["relationship_type"] = record["relationship_type"]
                molecules.append(molecule)

            return molecules
        except Exception as e:
            self.logger.error(f"Error getting organism molecules: {str(e)}")
            return []

    def create_organism(
        self, properties: Dict[str, Any], source: str = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new organism with the given properties.

        Args:
            properties: Organism properties
            source: Optional source to associate with the organism

        Returns:
            Created organism data or None if creation failed
        """
        try:
            # Check if organism with same name already exists
            if "name" in properties and properties["name"]:
                existing = self.find_organisms_by_name(
                    properties["name"], exact_match=True
                )
                if existing:
                    return self.update_organism(existing[0]["id"], properties, source)

            # Create the organism
            organism = self.create(properties)

            # Add source relationship if provided
            if source and organism:
                self._create_source_relationship(organism["id"], source)

            return organism
        except Exception as e:
            self.logger.error(f"Error creating organism: {str(e)}")
            return None

    def update_organism(
        self, organism_id: str, properties: Dict[str, Any], source: str = None
    ) -> Optional[Dict[str, Any]]:
        """Update an existing organism.

        Args:
            organism_id: ID of the organism to update
            properties: Updated properties
            source: Optional source to associate with the organism

        Returns:
            Updated organism data or None if update failed
        """
        try:
            # Update the organism
            organism = self.update(organism_id, properties)

            # Add source relationship if provided
            if source and organism:
                self._create_source_relationship(organism["id"], source)

            return organism
        except Exception as e:
            self.logger.error(f"Error updating organism: {str(e)}")
            return None

    def delete_organism(self, organism_id: str) -> bool:
        """Delete an organism.

        Args:
            organism_id: ID of the organism to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            return self.delete(organism_id)
        except Exception as e:
            self.logger.error(f"Error deleting organism: {str(e)}")
            return False

    def link_molecule_to_organism(
        self, organism_id: str, molecule_id: str, relationship_type: str = "PRODUCES"
    ) -> bool:
        """Link a molecule to an organism.

        Args:
            organism_id: ID of the organism
            molecule_id: ID of the molecule
            relationship_type: Type of relationship between organism and molecule

        Returns:
            True if successful, False otherwise
        """
        try:
            return self.create_relationship(
                from_id=organism_id,
                to_id=molecule_id,
                from_label="Organism",
                to_label="Molecule",
                relationship_type=relationship_type,
            )
        except Exception as e:
            self.logger.error(f"Error linking molecule to organism: {str(e)}")
            return False

    def _create_source_relationship(self, organism_id: str, source_name: str) -> bool:
        """Create a relationship between an organism and a source.

        Args:
            organism_id: ID of the organism
            source_name: Name of the source

        Returns:
            True if successful, False otherwise
        """
        try:
            # First ensure the source exists
            query = """
            MERGE (s:Source {name: $source})
            RETURN s
            """
            self.db_utils.run_query(query, {"source": source_name})

            # Create the relationship
            query = """
            MATCH (o:Organism), (s:Source {name: $source})
            WHERE ID(o) = toInteger($id)
            MERGE (o)-[:FROM_SOURCE]->(s)
            """

            self.db_utils.run_query(query, {"id": organism_id, "source": source_name})
            return True
        except Exception as e:
            self.logger.error(f"Error creating source relationship: {str(e)}")
            return False
