import json
import os
from typing import List, Optional, Dict, Any
from hyperblend.app.web.core.exceptions import ResourceNotFoundError, ValidationError
import logging

logger = logging.getLogger(__name__)

class EffectService:
    """Service for handling effect-related operations using JSON file."""

    def __init__(self):
        """Initialize the effect service."""
        self.effects_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                       'references', 'effects.json')
        self._effects_cache = None

    def _load_effects(self) -> Dict[str, List[Dict[str, str]]]:
        """Load effects from JSON file."""
        if self._effects_cache is None:
            try:
                with open(self.effects_file, 'r') as f:
                    self._effects_cache = json.load(f)
            except Exception as e:
                logger.error(f"Error loading effects file: {str(e)}")
                raise
        return self._effects_cache

    def _flatten_effects(self) -> List[Dict[str, Any]]:
        """Flatten effects from categories into a single list and sort alphabetically."""
        effects = []
        data = self._load_effects()
        
        for category, effect_list in data.items():
            # Format the category for display
            display_category = category.replace('_', ' ').title()
            # Get the main category type (first word)
            badge_category = display_category.split()[0]
            
            for effect_dict in effect_list:
                for name, description in effect_dict.items():
                    effects.append({
                        'id': len(effects),
                        'name': name,
                        'description': description,
                        'category': display_category,
                        'type': badge_category  # Changed from badge_type to type to match frontend expectations
                    })
        
        # Sort effects alphabetically by name
        return sorted(effects, key=lambda x: x['name'].lower())

    def get_effect(self, effect_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific effect by ID.

        Args:
            effect_id: The ID of the effect to retrieve

        Returns:
            Dictionary containing effect details
        """
        try:
            effects = self._flatten_effects()
            effect = next((e for e in effects if e['id'] == effect_id), None)
            if not effect:
                raise ResourceNotFoundError(f"Effect with ID {effect_id} not found")
            return effect
        except Exception as e:
            logger.error(f"Error getting effect {effect_id}: {str(e)}")
            raise

    def get_all_effects(self) -> List[Dict[str, Any]]:
        """
        Get all effects.

        Returns:
            List of dictionaries containing effect details
        """
        try:
            return self._flatten_effects()
        except Exception as e:
            logger.error(f"Error getting all effects: {str(e)}")
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
            effects = self._flatten_effects()
            query = query.lower()
            return [
                effect for effect in effects
                if query in effect['name'].lower() or
                   query in effect['description'].lower() or
                   query in effect['category'].lower()
            ]
        except Exception as e:
            logger.error(f"Error searching effects with query {query}: {str(e)}")
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
        required_fields = ['name']
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError(f"Missing required field: {field}")

        try:
            cypher_query = """
            CREATE (e:Effect {
                name: $name,
                description: $description,
                category: $category,
                created_at: datetime(),
                updated_at: datetime()
            })
            RETURN {
                id: toString(elementId(e)),
                name: e.name,
                description: e.description,
                category: e.category
            } as effect
            """
            result = self.graph.run(cypher_query, 
                name=data['name'],
                description=data.get('description', ''),
                category=data.get('category', '')
            ).data()
            
            return result[0]['effect']
        except Exception as e:
            logger.error(f"Error creating effect: {str(e)}")
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
            if not self.get_effect(effect_id):
                raise ResourceNotFoundError(f"Effect with ID {effect_id} not found")

            # Build update query dynamically based on provided fields
            update_parts = []
            params = {'effect_id': int(effect_id)}
            
            for field in ['name', 'description', 'category']:
                if field in data and data[field] is not None:
                    update_parts.append(f"e.{field} = ${field}")
                    params[field] = data[field]
            
            if not update_parts:
                return self.get_effect(effect_id)  # No updates needed
            
            update_parts.append("e.updated_at = datetime()")
            
            cypher_query = f"""
            MATCH (e:Effect)
            WHERE elementId(e) = $effect_id
            SET {', '.join(update_parts)}
            RETURN {{
                id: toString(elementId(e)),
                name: e.name,
                description: e.description,
                category: e.category
            }} as effect
            """
            
            result = self.graph.run(cypher_query, **params).data()
            return result[0]['effect']
        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating effect {effect_id}: {str(e)}")
            raise

    def delete_effect(self, effect_id: str) -> bool:
        """
        Delete an effect.

        Args:
            effect_id: ID of the effect to delete

        Returns:
            True if effect was deleted, False otherwise

        Raises:
            ResourceNotFoundError: If effect not found
        """
        try:
            # First check if effect exists
            if not self.get_effect(effect_id):
                raise ResourceNotFoundError(f"Effect with ID {effect_id} not found")

            cypher_query = """
            MATCH (e:Effect)
            WHERE elementId(e) = $effect_id
            DETACH DELETE e
            """
            
            self.graph.run(cypher_query, effect_id=int(effect_id))
            return True
        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error deleting effect {effect_id}: {str(e)}")
            raise 