# hyperblend/app/web/routes/targets.py

from flask import Blueprint, jsonify, request
from hyperblend.app.web.core.decorators import handle_db_error, cors_enabled, validate_json
from hyperblend.app.web.core.exceptions import ResourceNotFoundError
from hyperblend.services.internal.target_service import TargetService
from hyperblend.services.external.chembl_service import ChEMBLService
from hyperblend.database import get_graph
import logging

logger = logging.getLogger(__name__)
targets = Blueprint('targets', __name__)

@targets.route('/api/targets', methods=['GET'])
@cors_enabled
@handle_db_error
def list_targets():
    """
    Get all targets or search for targets.
    
    Query Parameters:
        q (str, optional): Search query string
        
    Returns:
        JSON response with list of targets
    """
    try:
        # Get database connection
        graph = get_graph()
        if not graph:
            return jsonify({'status': 'error', 'message': 'Database connection not available'}), 503
            
        target_service = TargetService(graph)
        query = request.args.get('q', '').strip()
        
        if query:
            targets = target_service.search_targets(query)
        else:
            targets = target_service.get_all_targets()
            
        return jsonify({'status': 'success', 'targets': targets})
    except Exception as e:
        logger.error(f"Error in list_targets: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@targets.route('/api/targets/<target_id>', methods=['GET'])
@cors_enabled
@handle_db_error
def get_target(target_id: str):
    """
    Get a specific target by ID.
    
    Args:
        target_id: The ID of the target to retrieve
        
    Returns:
        JSON response with target details
    """
    try:
        # Get database connection
        graph = get_graph()
        if not graph:
            return jsonify({'status': 'error', 'message': 'Database connection not available'}), 503
            
        target_service = TargetService(graph)
        target = target_service.get_target(target_id)
        
        if not target:
            raise ResourceNotFoundError('Target not found')
            
        return jsonify(target)
    except ResourceNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error in get_target: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@targets.route('/api/targets/search', methods=['GET'])
@cors_enabled
def search_targets():
    """
    Search for targets in ChEMBL database.
    
    Query Parameters:
        query (str): Search query string
        limit (int, optional): Maximum number of results to return (default: 10)
        
    Returns:
        JSON response with search results
    """
    query = request.args.get('query')
    limit = request.args.get('limit', 10, type=int)

    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400

    if not 1 <= limit <= 100:
        return jsonify({'error': 'Limit must be between 1 and 100'}), 400

    chembl = ChEMBLService()
    targets = chembl.search_targets(query, limit)
    return jsonify(targets)

@targets.route('/api/targets/<target_id>/enrich', methods=['POST'])
@cors_enabled
@handle_db_error
@validate_json
def enrich_target(target_id: str):
    """
    Enrich a target with data from external databases.
    
    Args:
        target_id: The ID of the target to enrich
        
    Request Body:
        {
            "database": str,  # The external database to use (e.g., "chembl")
            "identifier": str  # The identifier in the external database
        }
        
    Returns:
        JSON response with enrichment results
    """
    target_service = TargetService()
    try:
        data = request.get_json()
        if not data or 'database' not in data or 'identifier' not in data:
            return jsonify({'error': 'Missing database or identifier'}), 400
            
        result = target_service.enrich_target(
            target_id,
            data['database'],
            data['identifier']
        )
        return jsonify(result)
    except ResourceNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400 