"""Repository for effect-related operations."""

import json
import os
import logging
from typing import List, Optional, Dict, Any
from py2neo import Graph

from hyperblend.repository.base_repository import BaseRepository


class EffectRepository:
    """Repository for effect-related operations using JSON file or database."""

    def __init__(self, graph: Optional[Graph] = None, use_database: bool = False):
        """Initialize the effect repository.

        Args:
            graph: Neo4j graph database connection (when using database)
            use_database: Whether to use database or JSON file
        """
        self.logger = logging.getLogger(__name__)
        self.use_database = use_database

        if use_database:
            self.db_repository = BaseRepository(graph=graph, label="Effect")
        else:
            # Use JSON file
            self.effects_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "references",
                "effects.json",
            )
            self._effects_cache = None

    def _load_effects(self) -> Dict[str, List[Dict[str, str]]]:
        """Load effects from JSON file.

        Returns:
            Dictionary of effects by category
        """
        if self._effects_cache is None:
            try:
                with open(self.effects_file, "r") as f:
                    self._effects_cache = json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading effects file: {str(e)}")
                self._effects_cache = {}
        return self._effects_cache

    def _flatten_effects(self) -> List[Dict[str, Any]]:
        """Flatten effects from categories into a single list and sort alphabetically.

        Returns:
            List of effect objects
        """
        effects = []
        data = self._load_effects()

        for category, effect_list in data.items():
            # Format the category for display
            display_category = category.replace("_", " ").title()
            # Get the main category type (first word)
            badge_category = display_category.split()[0]

            for effect_dict in effect_list:
                for name, description in effect_dict.items():
                    effects.append(
                        {
                            "id": len(effects),
                            "name": name,
                            "description": description,
                            "category": display_category,
                            "type": badge_category,
                        }
                    )

        # Sort effects alphabetically by name
        return sorted(effects, key=lambda x: x["name"].lower())

    def get_effect(self, effect_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific effect by ID.

        Args:
            effect_id: ID of the effect

        Returns:
            Effect data or None if not found
        """
        try:
            if self.use_database:
                return self.db_repository.find_by_id(str(effect_id))
            else:
                effects = self._flatten_effects()
                return next((e for e in effects if e["id"] == effect_id), None)
        except Exception as e:
            self.logger.error(f"Error getting effect {effect_id}: {str(e)}")
            return None

    def get_all_effects(self) -> List[Dict[str, Any]]:
        """Get all effects.

        Returns:
            List of all effects
        """
        try:
            if self.use_database:
                return self.db_repository.find_all()
            else:
                return self._flatten_effects()
        except Exception as e:
            self.logger.error(f"Error getting all effects: {str(e)}")
            return []

    def search_effects(self, query: str) -> List[Dict[str, Any]]:
        """Search for effects by name, description, or category.

        Args:
            query: Search query string

        Returns:
            List of matching effects
        """
        try:
            if self.use_database:
                search_fields = ["name", "description", "category"]
                return self.db_repository.search_by_text(query, search_fields)
            else:
                effects = self._flatten_effects()
                query = query.lower()
                return [
                    effect
                    for effect in effects
                    if query in effect["name"].lower()
                    or query in effect["description"].lower()
                    or query in effect["category"].lower()
                ]
        except Exception as e:
            self.logger.error(f"Error searching effects with query {query}: {str(e)}")
            return []

    def create_effect(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new effect (only available in database mode).

        Args:
            data: Effect properties

        Returns:
            Created effect data or None if creation failed
        """
        if not self.use_database:
            self.logger.error("Effect creation not supported in JSON file mode")
            return None

        try:
            # Basic validation
            if "name" not in data or not data["name"]:
                self.logger.error("Effect name is required")
                return None

            # Set defaults for optional fields
            if "description" not in data:
                data["description"] = ""
            if "category" not in data:
                data["category"] = "General"

            # Add timestamps
            data["created_at"] = data["updated_at"] = (
                None  # Neo4j will use current datetime
            )

            return self.db_repository.create(data)
        except Exception as e:
            self.logger.error(f"Error creating effect: {str(e)}")
            return None

    def update_effect(
        self, effect_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update an existing effect (only available in database mode).

        Args:
            effect_id: ID of the effect to update
            data: Updated properties

        Returns:
            Updated effect data or None if update failed
        """
        if not self.use_database:
            self.logger.error("Effect update not supported in JSON file mode")
            return None

        try:
            # Update timestamp
            data["updated_at"] = None  # Neo4j will use current datetime

            return self.db_repository.update(effect_id, data)
        except Exception as e:
            self.logger.error(f"Error updating effect: {str(e)}")
            return None

    def delete_effect(self, effect_id: str) -> bool:
        """Delete an effect (only available in database mode).

        Args:
            effect_id: ID of the effect to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.use_database:
            self.logger.error("Effect deletion not supported in JSON file mode")
            return False

        try:
            return self.db_repository.delete(effect_id)
        except Exception as e:
            self.logger.error(f"Error deleting effect: {str(e)}")
            return False
