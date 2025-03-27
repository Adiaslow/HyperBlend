"""Repository for target database operations."""

import logging
from typing import List, Optional, Dict, Any
from py2neo import Graph
from hyperblend.repository.base_repository import BaseRepository


class TargetRepository(BaseRepository):
    """Repository for target-specific database operations."""

    def __init__(self, graph: Optional[Graph] = None):
        """
        Initialize the target repository.

        Args:
            graph: Neo4j graph database connection
        """
        super().__init__(graph=graph, label="Target")
        self.logger = logging.getLogger(__name__)

    def find_target_by_id(self, target_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a target by ID.

        Args:
            target_id: Target ID

        Returns:
            Optional[Dict[str, Any]]: Target data or None if not found
        """
        try:
            return self.find_by_id(target_id)
        except Exception as e:
            self.logger.error(f"Error finding target by ID: {str(e)}")
            return None

    def find_targets_by_name(
        self, name: str, exact: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Find targets by name.

        Args:
            name: Target name
            exact: Whether to perform exact match

        Returns:
            List[Dict[str, Any]]: List of matching targets
        """
        try:
            if exact:
                return self.find_by_property("name", name)
            else:
                return self.search_by_text(name, ["name"], 100)
        except Exception as e:
            self.logger.error(f"Error finding targets by name: {str(e)}")
            return []

    def find_targets_by_type(self, target_type: str) -> List[Dict[str, Any]]:
        """
        Find targets by type (e.g., 'protein', 'enzyme', 'receptor').

        Args:
            target_type: Type of target

        Returns:
            List[Dict[str, Any]]: List of matching targets
        """
        try:
            return self.find_by_property("type", target_type)
        except Exception as e:
            self.logger.error(f"Error finding targets by type: {str(e)}")
            return []

    def find_targets_by_organism(self, organism: str) -> List[Dict[str, Any]]:
        """
        Find targets from a specific organism.

        Args:
            organism: Organism name

        Returns:
            List[Dict[str, Any]]: List of matching targets
        """
        try:
            return self.find_by_property("organism", organism)
        except Exception as e:
            self.logger.error(f"Error finding targets by organism: {str(e)}")
            return []

    def find_targets_by_source(self, source: str) -> List[Dict[str, Any]]:
        """
        Find targets from a specific source.

        Args:
            source: Source name

        Returns:
            List[Dict[str, Any]]: List of matching targets
        """
        try:
            query = """
            MATCH (t:Target)-[:FROM_SOURCE]->(s:Source {name: $source})
            RETURN t
            """
            results = self.db_utils.run_query(query, {"source": source})
            return [dict(result["t"]) for result in results if result.get("t")]
        except Exception as e:
            self.logger.error(f"Error finding targets by source: {str(e)}")
            return []

    def create_target(
        self, target_data: Dict[str, Any], source: str
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new target.

        Args:
            target_data: Target data
            source: Source of the target data

        Returns:
            Optional[Dict[str, Any]]: Created target data or None if failed
        """
        try:
            # Check if target with name already exists
            if "name" in target_data and target_data["name"]:
                existing = self.find_targets_by_name(target_data["name"], exact=True)
                if existing:
                    # Update existing target instead of creating
                    return self.update_target(existing[0]["id"], target_data, source)

            # Create target
            target = self.create(target_data)

            # Create source relationship
            if target:
                self._create_source_relationship(target["id"], source)

            return target
        except Exception as e:
            self.logger.error(f"Error creating target: {str(e)}")
            return None

    def update_target(
        self, target_id: str, target_data: Dict[str, Any], source: str
    ) -> Optional[Dict[str, Any]]:
        """
        Update a target.

        Args:
            target_id: Target ID
            target_data: Updated target data
            source: Source of the target data

        Returns:
            Optional[Dict[str, Any]]: Updated target data or None if failed
        """
        try:
            # Update target
            target = self.update(target_id, target_data)

            # Create source relationship
            if target:
                self._create_source_relationship(target["id"], source)

            return target
        except Exception as e:
            self.logger.error(f"Error updating target: {str(e)}")
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
            return self.delete(target_id)
        except Exception as e:
            self.logger.error(f"Error deleting target: {str(e)}")
            return False

    def get_target_molecules(self, target_id: str) -> List[Dict[str, Any]]:
        """
        Get molecules associated with a target.

        Args:
            target_id: Target ID

        Returns:
            List[Dict[str, Any]]: List of molecules
        """
        try:
            query = """
            MATCH (t:Target)-[r]->(m:Molecule)
            WHERE ID(t) = toInteger($id)
            RETURN m, type(r) as relationship_type, 
                   properties(r) as relationship_properties
            """

            results = self.db_utils.run_query(query, {"id": target_id})

            molecules = []
            for result in results:
                if result.get("m"):
                    molecule_data = dict(result["m"])
                    molecule_data["relationship"] = {
                        "type": result.get("relationship_type"),
                        "properties": result.get("relationship_properties", {}),
                    }
                    molecules.append(molecule_data)

            return molecules
        except Exception as e:
            self.logger.error(f"Error getting target molecules: {str(e)}")
            return []

    def _create_source_relationship(self, target_id: str, source: str) -> bool:
        """
        Create relationship between target and source.

        Args:
            target_id: Target ID
            source: Source name

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # First ensure source node exists
            query = """
            MERGE (s:Source {name: $source})
            WITH s
            MATCH (t:Target)
            WHERE ID(t) = toInteger($target_id)
            MERGE (t)-[r:FROM_SOURCE]->(s)
            RETURN r
            """

            results = self.db_utils.run_query(
                query, {"target_id": target_id, "source": source}
            )

            return bool(results)
        except Exception as e:
            self.logger.error(f"Error creating source relationship: {str(e)}")
            return False
