# hyperblend/app/web/routes/effects.py

from flask import Blueprint, jsonify, request
from hyperblend.app.web.core.decorators import (
    handle_db_error,
    cors_enabled,
    validate_json,
)
from hyperblend.app.web.core.exceptions import ResourceNotFoundError, ValidationError
from hyperblend.services.internal.effect_service import EffectService
import logging

logger = logging.getLogger(__name__)

effects = Blueprint("effects", __name__)
effect_service = EffectService()  # Create a single instance


@effects.route("/api/effects/<int:effect_id>", methods=["GET"])
@cors_enabled
def get_effect(effect_id: int):
    """
    Get details for a specific effect.

    Args:
        effect_id: The ID of the effect to retrieve

    Returns:
        JSON response with effect details
    """
    try:
        effect = effect_service.get_effect(effect_id)
        if not effect:
            raise ResourceNotFoundError("Effect not found")

        return jsonify(effect)
    except ResourceNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Error in get_effect: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@effects.route("/api/effects", methods=["GET"])
@cors_enabled
def list_effects():
    """
    Get all effects or search for effects.

    Query Parameters:
        q (str, optional): Search query string

    Returns:
        JSON response with list of effects
    """
    try:
        query = request.args.get("q", "").strip()

        if query:
            effects = effect_service.search_effects(query)
        else:
            effects = effect_service.get_all_effects()

        return jsonify({"status": "success", "effects": effects})
    except Exception as e:
        logger.error(f"Error in list_effects: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@effects.route("/api/effects", methods=["POST"])
@cors_enabled
@handle_db_error
@validate_json
def create_effect():
    """
    Create a new effect.

    Request Body:
        {
            "name": str,
            "description": str (optional),
            "category": str (optional)
        }

    Returns:
        JSON response with created effect details
    """
    try:
        # Get database connection
        graph = get_graph()
        if not graph:
            return (
                jsonify(
                    {"status": "error", "message": "Database connection not available"}
                ),
                503,
            )

        effect_service = EffectService(graph)
        data = request.get_json()

        effect = effect_service.create_effect(data)
        return jsonify({"status": "success", "effect": effect}), 201
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Error in create_effect: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@effects.route("/api/effects/<effect_id>", methods=["PUT"])
@cors_enabled
@handle_db_error
@validate_json
def update_effect(effect_id: str):
    """
    Update an existing effect.

    Args:
        effect_id: The ID of the effect to update

    Request Body:
        {
            "name": str (optional),
            "description": str (optional),
            "category": str (optional)
        }

    Returns:
        JSON response with updated effect details
    """
    try:
        # Get database connection
        graph = get_graph()
        if not graph:
            return (
                jsonify(
                    {"status": "error", "message": "Database connection not available"}
                ),
                503,
            )

        effect_service = EffectService(graph)
        data = request.get_json()

        effect = effect_service.update_effect(effect_id, data)
        return jsonify({"status": "success", "effect": effect})
    except ResourceNotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Error in update_effect: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@effects.route("/api/effects/<effect_id>", methods=["DELETE"])
@cors_enabled
@handle_db_error
def delete_effect(effect_id: str):
    """
    Delete an effect.

    Args:
        effect_id: The ID of the effect to delete

    Returns:
        JSON response indicating success
    """
    try:
        # Get database connection
        graph = get_graph()
        if not graph:
            return (
                jsonify(
                    {"status": "error", "message": "Database connection not available"}
                ),
                503,
            )

        effect_service = EffectService(graph)
        effect_service.delete_effect(effect_id)

        return jsonify({"status": "success", "message": "Effect deleted successfully"})
    except ResourceNotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        logger.error(f"Error in delete_effect: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@effects.route("/api/effects/<effect_id>/enrich", methods=["POST"])
@cors_enabled
@handle_db_error
@validate_json
def enrich_effect(effect_id: str):
    """
    Enrich an effect with data from external databases.

    Args:
        effect_id: The ID of the effect to enrich

    Request Body:
        {
            "identifiers": [
                {"type": "external_id", "value": "..."},
                {"type": "name", "value": "..."}
            ]
        }

    Returns:
        JSON response with enrichment results
    """
    try:
        # Get the effect first to verify it exists
        effect = effect_service.get_effect(effect_id)
        if not effect:
            raise ResourceNotFoundError("Effect not found")

        # Get identifiers from request
        data = request.get_json()
        identifiers = data.get("identifiers", [])

        if not identifiers:
            # If no identifiers provided, try to use effect's existing identifiers
            if effect.get("external_id"):
                identifiers.append(
                    {"type": "external_id", "value": effect["external_id"]}
                )
            if effect.get("name"):
                identifiers.append({"type": "name", "value": effect["name"]})

            # If still no identifiers, error out
            if not identifiers:
                return (
                    jsonify({"error": "No identifiers available for enrichment"}),
                    400,
                )

        # Collect enrichment data from multiple sources
        enrichment_results = {}
        sources = []

        # This is a placeholder for potential external services to fetch effect data
        # For now, we'll use mock data based on categories

        # Determine which sources to show based on the effect category
        category = effect.get("category", "").lower()

        # Mock data sources based on effect type
        if "psychological" in category or "cognitive" in category:
            sources.append(
                {
                    "name": "PsychonautWiki",
                    "url": f"https://psychonautwiki.org/wiki/{effect['name'].replace(' ', '_')}",
                }
            )

            enrichment_results["mechanism"] = "Receptor modulation"
            enrichment_results["risk_level"] = "Moderate"

        if "perceptual" in category:
            sources.append(
                {
                    "name": "EffectIndex",
                    "url": f"https://effectindex.com/effects/{effect['name'].replace(' ', '-').lower()}",
                }
            )

            enrichment_results["subjective_index"] = 4.2

        if any(x in category for x in ["physiological", "therapeutic"]):
            sources.append({"name": "RxList", "url": "https://www.rxlist.com/"})

            enrichment_results["clinical_relevance"] = "Significant"
            enrichment_results["studied_in_trials"] = True

        # Always add TripSit as a source (just for demo purposes)
        sources.append({"name": "TripSit", "url": "https://drugs.tripsit.me/"})

        # Process enrichment data into a standardized format
        if not enrichment_results:
            return jsonify(
                {
                    "success": False,
                    "message": "No enrichment data found from external sources",
                }
            )

        # Format the response
        attributes = []
        identifiers_dict = {}

        # Extract attributes
        attribute_mappings = {
            "mechanism": "Mechanism",
            "risk_level": "Risk Level",
            "subjective_index": "Subjective Index",
            "clinical_relevance": "Clinical Relevance",
            "studied_in_trials": "Studied in Clinical Trials",
        }

        for attr_key, display_name in attribute_mappings.items():
            if (
                attr_key in enrichment_results
                and enrichment_results[attr_key] is not None
            ):
                attributes.append(
                    {"name": display_name, "value": str(enrichment_results[attr_key])}
                )

        # Extract identifiers - these would come from real services in production
        if category:
            identifiers_dict["PsychonautWiki"] = f"PSYW-{effect_id}"
            identifiers_dict["EffectIndex"] = f"EI-{effect_id}"

        # Update the effect in the database with enriched data
        update_data = {k: v for k, v in enrichment_results.items() if v is not None}
        if update_data:
            effect_service.update_effect(effect_id, update_data)

        # Return the formatted enrichment data
        return jsonify(
            {
                "success": True,
                "data": {"attributes": attributes, "identifiers": identifiers_dict},
                "sources": sources,
            }
        )
    except ResourceNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
