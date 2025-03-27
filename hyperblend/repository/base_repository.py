"""Base repository for database access."""

import logging
from typing import Any, Dict, List, Optional, Union
from py2neo import Graph, Node, Relationship
from hyperblend.utils.db_utils import DatabaseUtils, DatabaseError


class BaseRepository:
    """Base repository for database access with common CRUD operations."""

    def __init__(self, graph: Optional[Graph] = None, label: Optional[str] = None):
        """
        Initialize the base repository.

        Args:
            graph: Neo4j graph database connection
            label: Entity type label (e.g., 'Molecule', 'Target')
        """
        if graph is None:
            raise ValueError("Graph connection is required")

        self.graph = graph
        self.db_utils = DatabaseUtils(graph)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.entity_type = label

    def find_by_id(self, id_value: str) -> Optional[Dict[str, Any]]:
        """
        Find an entity by ID.

        Args:
            id_value: Entity ID

        Returns:
            Optional[Dict[str, Any]]: Entity data or None if not found
        """
        try:
            if not self.entity_type:
                raise ValueError("Entity type (label) is required")

            query = """
            MATCH (e:{entity_type})
            WHERE e.id = $id
            RETURN e
            """.format(
                entity_type=self.entity_type
            )

            results = self.db_utils.run_query(query, {"id": id_value})
            if not results or not results[0].get("e"):
                return None

            return dict(results[0]["e"])
        except Exception as e:
            self.logger.error(f"Error finding {self.entity_type} by ID: {str(e)}")
            return None

    def find_by_property(
        self, property_name: str, property_value: Any
    ) -> List[Dict[str, Any]]:
        """
        Find entities by property.

        Args:
            property_name: Property name to match
            property_value: Property value to match

        Returns:
            List[Dict[str, Any]]: List of matching entities
        """
        try:
            if not self.entity_type:
                raise ValueError("Entity type (label) is required")

            query = """
            MATCH (e:{entity_type})
            WHERE e.{property_name} = $value
            RETURN e
            """.format(
                entity_type=self.entity_type, property_name=property_name
            )

            results = self.db_utils.run_query(query, {"value": property_value})
            return [dict(result["e"]) for result in results if result.get("e")]
        except Exception as e:
            self.logger.error(f"Error finding {self.entity_type} by property: {str(e)}")
            return []

    def create(self, properties: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new entity.

        Args:
            properties: Entity properties

        Returns:
            Optional[Dict[str, Any]]: Created entity data or None if failed
        """
        try:
            if not self.entity_type:
                raise ValueError("Entity type (label) is required")

            # Add debug logging
            self.logger.debug(
                f"Creating new {self.entity_type} with properties: {properties}"
            )

            query = """
            CREATE (e:{entity_type} $props)
            RETURN e {{
                .*, 
                id: CASE 
                    WHEN e.id IS NOT NULL THEN e.id 
                    ELSE toString(elementId(e)) 
                END
            }} as e
            """.format(
                entity_type=self.entity_type
            )

            results = self.db_utils.run_query(query, {"props": properties})
            if not results or not results[0].get("e"):
                self.logger.warning(
                    f"Failed to create {self.entity_type}: no result returned"
                )
                return None

            created_entity = dict(results[0]["e"])

            # Ensure entity has an ID
            if "id" not in created_entity or not created_entity["id"]:
                # Try to get ID from Neo4j elementId if possible
                try:
                    created_entity["id"] = str(results[0]["e"]._id)
                except Exception as e:
                    self.logger.warning(f"Could not get Neo4j ID: {str(e)}")
                    # Generate a fallback ID
                    import uuid

                    created_entity["id"] = (
                        f"{self.entity_type.lower()}-{uuid.uuid4().hex[:8]}"
                    )

            self.logger.debug(
                f"Created {self.entity_type} with ID: {created_entity.get('id')}"
            )
            return created_entity

        except Exception as e:
            self.logger.error(f"Error creating {self.entity_type}: {str(e)}")
            import traceback

            self.logger.error(traceback.format_exc())
            return None

    def update(
        self, id_value: str, properties: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update an entity.

        Args:
            id_value: Entity ID
            properties: Updated properties

        Returns:
            Optional[Dict[str, Any]]: Updated entity data or None if failed
        """
        try:
            if not self.entity_type:
                raise ValueError("Entity type (label) is required")

            self.logger.debug(f"Updating {self.entity_type} with ID: {id_value}")
            self.logger.debug(f"Properties to update: {properties}")

            # Try to convert ID to integer for element ID comparison
            try:
                id_as_int = int(id_value)
            except (ValueError, TypeError):
                id_as_int = -1  # Use invalid ID if conversion fails

            # More robust query to match by various ID formats
            query = """
            MATCH (e:{entity_type})
            WHERE e.id = $id OR 
                  toString(elementId(e)) = $id OR 
                  elementId(e) = $id_as_int
            SET e += $props
            RETURN e {{
                .*, 
                id: CASE 
                    WHEN e.id IS NOT NULL THEN e.id 
                    ELSE toString(elementId(e)) 
                END
            }} as e
            """.format(
                entity_type=self.entity_type
            )

            results = self.db_utils.run_query(
                query, {"id": id_value, "id_as_int": id_as_int, "props": properties}
            )

            if not results or not results[0].get("e"):
                self.logger.warning(f"No {self.entity_type} found with ID: {id_value}")
                return None

            updated_entity = dict(results[0]["e"])
            self.logger.debug(
                f"Successfully updated {self.entity_type}: {updated_entity.get('id', 'Unknown ID')}"
            )
            return updated_entity

        except Exception as e:
            self.logger.error(f"Error updating {self.entity_type}: {str(e)}")
            import traceback

            self.logger.error(traceback.format_exc())
            return None

    def delete(self, id_value: str) -> bool:
        """
        Delete an entity.

        Args:
            id_value: Entity ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.entity_type:
                raise ValueError("Entity type (label) is required")

            query = """
            MATCH (e:{entity_type})
            WHERE e.id = $id
            DETACH DELETE e
            """.format(
                entity_type=self.entity_type
            )

            self.db_utils.run_query(query, {"id": id_value})
            return True
        except Exception as e:
            self.logger.error(f"Error deleting {self.entity_type}: {str(e)}")
            return False

    def find_all(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find all entities of the repository's type.

        Args:
            limit: Maximum number of entities to return

        Returns:
            List[Dict[str, Any]]: List of entities
        """
        try:
            if not self.entity_type:
                raise ValueError("Entity type (label) is required")

            # Use elementId in the query for better performance and compatibility
            query = """
            MATCH (e:{entity_type})
            RETURN e {{
                .*, 
                id: CASE 
                    WHEN e.id IS NOT NULL THEN e.id 
                    ELSE toString(elementId(e)) 
                END
            }} as e
            LIMIT $limit
            """.format(
                entity_type=self.entity_type
            )

            results = self.db_utils.run_query(query, {"limit": limit})

            # Process results to ensure all have an ID
            processed_results = []
            for record in results:
                if record and "e" in record:
                    item = dict(record["e"])
                    if "id" not in item or not item["id"]:
                        # Fallback ID if the projection didn't work
                        try:
                            item["id"] = str(record["e"]._id)
                        except:
                            item["id"] = (
                                f"{self.entity_type.lower()}-{len(processed_results)}"
                            )
                    processed_results.append(item)

            return processed_results
        except Exception as e:
            self.logger.error(f"Error finding all {self.entity_type}: {str(e)}")
            # Return empty list instead of raising exception
            return []

    def create_relationship(
        self,
        from_id: str,
        to_id: str,
        relationship_type: str,
        from_label: Optional[str] = None,
        to_label: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Create a relationship between two entities.

        Args:
            from_id: ID of the source entity
            to_id: ID of the target entity
            relationship_type: Type of relationship
            from_label: Label of the source entity (defaults to repository's entity_type)
            to_label: Label of the target entity (defaults to repository's entity_type)
            properties: Optional relationship properties

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from_type = from_label or self.entity_type
            to_type = to_label or self.entity_type

            if not from_type or not to_type:
                raise ValueError("Entity types (labels) are required")

            # Handle properties correctly
            if properties is None:
                properties = {}

            self.logger.debug(
                f"Creating relationship: {from_type}({from_id}) -[{relationship_type}]-> {to_type}({to_id})"
            )

            # Try to convert IDs to integers for element ID comparison
            try:
                from_id_int = int(from_id)
            except (ValueError, TypeError):
                from_id_int = -1

            try:
                to_id_int = int(to_id)
            except (ValueError, TypeError):
                to_id_int = -1

            query = """
            MATCH (from:{from_type}), (to:{to_type})
            WHERE (from.id = $from_id OR toString(elementId(from)) = $from_id OR elementId(from) = $from_id_int)
              AND (to.id = $to_id OR toString(elementId(to)) = $to_id OR elementId(to) = $to_id_int)
            CREATE (from)-[r:{rel_type} $props]->(to)
            RETURN r
            """.format(
                from_type=from_type, to_type=to_type, rel_type=relationship_type
            )

            results = self.db_utils.run_query(
                query,
                {
                    "from_id": from_id,
                    "to_id": to_id,
                    "from_id_int": from_id_int,
                    "to_id_int": to_id_int,
                    "props": properties,
                },
            )

            success = bool(results)
            self.logger.debug(
                f"Relationship creation {'successful' if success else 'failed'}"
            )
            return success

        except Exception as e:
            self.logger.error(f"Error creating relationship: {str(e)}")
            import traceback

            self.logger.error(traceback.format_exc())
            return False

    def search_by_text(
        self,
        search_text: str,
        properties: List[str],
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search entities by text across specified properties.

        Args:
            search_text: Text to search for
            properties: List of properties to search in
            limit: Maximum number of results to return

        Returns:
            List[Dict[str, Any]]: List of matching entities
        """
        try:
            if not self.entity_type:
                raise ValueError("Entity type (label) is required")
            if not properties:
                raise ValueError("At least one property must be specified for search")

            # Build WHERE conditions for each property
            where_clauses = []
            for prop in properties:
                where_clauses.append(f"e.{prop} =~ $pattern")

            query = f"""
            MATCH (e:{self.entity_type})
            WHERE {" OR ".join(where_clauses)}
            RETURN e
            LIMIT $limit
            """

            # Case-insensitive pattern match
            pattern = f"(?i).*{search_text}.*"
            results = self.db_utils.run_query(
                query, {"pattern": pattern, "limit": limit}
            )
            return [dict(result["e"]) for result in results if result.get("e")]
        except Exception as e:
            self.logger.error(f"Error searching {self.entity_type} by text: {str(e)}")
            return []
