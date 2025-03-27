"""Utilities for handling entity objects (molecules, targets, organisms, effects)."""

import logging
from typing import Dict, List, Any, Optional, Set, Union
from py2neo import Node


logger = logging.getLogger(__name__)


class EntityUtils:
    """Utilities for working with entity data."""

    @staticmethod
    def merge_properties(
        existing: Dict[str, Any], new_data: Dict[str, Any], override: bool = False
    ) -> Dict[str, Any]:
        """
        Merge properties from new data into existing data.

        Args:
            existing: Existing property dictionary
            new_data: New property dictionary to merge
            override: Whether to override existing values with new ones

        Returns:
            Dict[str, Any]: Merged properties
        """
        result = existing.copy()

        for key, value in new_data.items():
            if key not in result or result[key] is None or override:
                if value is not None:  # Only add non-None values
                    result[key] = value

        return result

    @staticmethod
    def extract_props_from_node(node: Node) -> Dict[str, Any]:
        """
        Extract all properties from a Neo4j node.

        Args:
            node: Neo4j node

        Returns:
            Dict[str, Any]: Dictionary of node properties
        """
        if not node:
            return {}

        return {key: value for key, value in node.items()}

    @staticmethod
    def clean_entity_data(
        data: Dict[str, Any], allowed_props: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Clean entity data by removing None values and filtering for allowed properties.

        Args:
            data: Data dictionary to clean
            allowed_props: List of allowed property names (None for all)

        Returns:
            Dict[str, Any]: Cleaned data dictionary
        """
        # Remove None values
        cleaned = {k: v for k, v in data.items() if v is not None}

        # Filter for allowed properties if specified
        if allowed_props:
            cleaned = {k: v for k, v in cleaned.items() if k in allowed_props}

        return cleaned

    @staticmethod
    def combine_collections(
        existing: Optional[List[Any]], new_items: Optional[List[Any]]
    ) -> List[Any]:
        """
        Combine collections without duplicates.

        Args:
            existing: Existing collection (or None)
            new_items: New items to add (or None)

        Returns:
            List[Any]: Combined collection without duplicates
        """
        existing_set = set(existing or [])
        new_set = set(new_items or [])
        combined = existing_set.union(new_set)
        return list(combined)

    @staticmethod
    def format_entity_result(
        node_data: Dict[str, Any], extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format an entity result by combining node data with extra data.

        Args:
            node_data: Node data dictionary
            extra_data: Extra data to include

        Returns:
            Dict[str, Any]: Formatted entity result
        """
        result = node_data.copy()

        if extra_data:
            for key, value in extra_data.items():
                result[key] = value

        return result

    @staticmethod
    def validate_entity_data(data: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        Validate entity data by checking required fields.

        Args:
            data: Entity data dictionary
            required_fields: List of required field names

        Returns:
            bool: True if valid, False otherwise
        """
        for field in required_fields:
            if field not in data or data[field] is None:
                logger.error(f"Missing required field: {field}")
                return False

        return True
