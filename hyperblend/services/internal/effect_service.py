"""Service for handling effect-related operations."""

import logging
from typing import List, Optional, Dict, Any
from hyperblend.app.web.core.exceptions import ResourceNotFoundError, ValidationError
from hyperblend.repository.effect_repository import EffectRepository

logger = logging.getLogger(__name__)


class EffectService:
    """Service for handling effect-related operations."""

    def __init__(
        self, graph=None, effect_repository: Optional[EffectRepository] = None
    ):
        """
        Initialize the effect service.

        Args:
            graph: Neo4j graph database connection (optional)
            effect_repository: Repository for effect operations (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.effect_repository = effect_repository or EffectRepository(graph=graph)

    def get_effect(self, effect_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific effect by ID.

        Args:
            effect_id: The ID of the effect to retrieve

        Returns:
            Dictionary containing effect details

        Raises:
            ResourceNotFoundError: If effect not found
        """
        try:
            effect = self.effect_repository.get_effect(effect_id)
            if not effect:
                raise ResourceNotFoundError(f"Effect with ID {effect_id} not found")
            return effect
        except ResourceNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Error getting effect {effect_id}: {str(e)}")
            raise

    def get_all_effects(self) -> List[Dict[str, Any]]:
        """
        Get all effects.

        Returns:
            List of dictionaries containing effect details
        """
        try:
            return self.effect_repository.get_all_effects()
        except Exception as e:
            self.logger.error(f"Error getting all effects: {str(e)}")
            raise

    def search_effects(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for effects by name, description, or category.

        Args:
            query: Search query string

        Returns:
            List of dictionaries containing matching effect details
        """
        try:
            return self.effect_repository.search_effects(query)
        except Exception as e:
            self.logger.error(f"Error searching effects with query {query}: {str(e)}")
            raise

    def create_effect(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new effect.

        Args:
            data: Dictionary containing effect data:
                - name (str): Effect name
                - description (str, optional): Effect description
                - category (str, optional): Effect category

        Returns:
            Dictionary containing the created effect details

        Raises:
            ValidationError: If required fields are missing or invalid
        """
        # Validate required fields
        required_fields = ["name"]
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError(f"Missing required field: {field}")

        try:
            effect = self.effect_repository.create_effect(data)
            if not effect:
                raise ValidationError("Failed to create effect")
            return effect
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error creating effect: {str(e)}")
            raise

    def update_effect(self, effect_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing effect.

        Args:
            effect_id: ID of the effect to update
            data: Dictionary containing effect data to update:
                - name (str, optional): New effect name
                - description (str, optional): New effect description
                - category (str, optional): New effect category

        Returns:
            Dictionary containing the updated effect details

        Raises:
            ResourceNotFoundError: If effect not found
        """
        try:
            # First check if effect exists
            if not self.effect_repository.get_effect(int(effect_id)):
                raise ResourceNotFoundError(f"Effect with ID {effect_id} not found")

            effect = self.effect_repository.update_effect(effect_id, data)
            if not effect:
                raise ValidationError("Failed to update effect")
            return effect
        except ResourceNotFoundError:
            raise
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error updating effect {effect_id}: {str(e)}")
            raise

    def delete_effect(self, effect_id: str) -> bool:
        """
        Delete an effect.

        Args:
            effect_id: ID of the effect to delete

        Returns:
            True if successful

        Raises:
            ResourceNotFoundError: If effect not found
        """
        try:
            # First check if effect exists
            if not self.effect_repository.get_effect(int(effect_id)):
                raise ResourceNotFoundError(f"Effect with ID {effect_id} not found")

            success = self.effect_repository.delete_effect(effect_id)
            if not success:
                raise Exception("Failed to delete effect")
            return True
        except ResourceNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Error deleting effect {effect_id}: {str(e)}")
            raise
