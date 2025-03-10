# hyperblend/app/web/routes/effects.py

from flask import Blueprint, jsonify, request
from hyperblend.app.web.core.decorators import handle_db_error, cors_enabled, validate_json
from hyperblend.app.web.core.exceptions import ResourceNotFoundError, ValidationError
from hyperblend.services.internal.effect_service import EffectService
import logging

logger = logging.getLogger(__name__)

effects = Blueprint('effects', __name__)
effect_service = EffectService()  # Create a single instance

@effects.route('/api/effects/<int:effect_id>', methods=['GET'])
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
            raise ResourceNotFoundError('Effect not found')
            
        return jsonify(effect)
    except ResourceNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error in get_effect: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@effects.route('/api/effects', methods=['GET'])
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
        query = request.args.get('q', '').strip()
        
        if query:
            effects = effect_service.search_effects(query)
        else:
            effects = effect_service.get_all_effects()
            
        return jsonify({'status': 'success', 'effects': effects})
    except Exception as e:
        logger.error(f"Error in list_effects: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@effects.route('/api/effects', methods=['POST'])
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
            return jsonify({'status': 'error', 'message': 'Database connection not available'}), 503
            
        effect_service = EffectService(graph)
        data = request.get_json()
        
        effect = effect_service.create_effect(data)
        return jsonify({'status': 'success', 'effect': effect}), 201
    except ValidationError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in create_effect: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@effects.route('/api/effects/<effect_id>', methods=['PUT'])
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
            return jsonify({'status': 'error', 'message': 'Database connection not available'}), 503
            
        effect_service = EffectService(graph)
        data = request.get_json()
        
        effect = effect_service.update_effect(effect_id, data)
        return jsonify({'status': 'success', 'effect': effect})
    except ResourceNotFoundError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 404
    except ValidationError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in update_effect: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@effects.route('/api/effects/<effect_id>', methods=['DELETE'])
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
            return jsonify({'status': 'error', 'message': 'Database connection not available'}), 503
            
        effect_service = EffectService(graph)
        effect_service.delete_effect(effect_id)
        
        return jsonify({'status': 'success', 'message': 'Effect deleted successfully'})
    except ResourceNotFoundError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 404
    except Exception as e:
        logger.error(f"Error in delete_effect: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500 