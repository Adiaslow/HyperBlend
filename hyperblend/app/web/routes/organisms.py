# hyperblend/app/web/routes/organisms.py

from flask import Blueprint, jsonify, request
from hyperblend.app.web.core.decorators import handle_db_error, cors_enabled
from hyperblend.app.web.core.exceptions import ResourceNotFoundError
from hyperblend.services.internal.organism_service import OrganismService
from hyperblend.database import get_graph
import logging

logger = logging.getLogger(__name__)
organisms = Blueprint('organisms', __name__)

@organisms.route('/api/organisms', methods=['GET'])
@cors_enabled
@handle_db_error
def list_organisms():
    """
    Get all organisms or search for organisms.
    
    Query Parameters:
        q (str, optional): Search query string
        
    Returns:
        JSON response with list of organisms
    """
    try:
        # Get database connection
        graph = get_graph()
        if not graph:
            return jsonify({'status': 'error', 'message': 'Database connection not available'}), 503
            
        organism_service = OrganismService(graph)
        query = request.args.get('q', '').strip()
        
        if query:
            organisms = organism_service.search_organisms(query)
        else:
            organisms = organism_service.get_all_organisms()
            
        return jsonify({'status': 'success', 'organisms': organisms})
    except Exception as e:
        logger.error(f"Error in list_organisms: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@organisms.route('/api/organisms/<organism_id>', methods=['GET'])
@cors_enabled
@handle_db_error
def get_organism(organism_id: str):
    """
    Get a specific organism by ID.
    
    Args:
        organism_id: The ID of the organism to retrieve
        
    Returns:
        JSON response with organism details
    """
    try:
        # Get database connection
        graph = get_graph()
        if not graph:
            return jsonify({'status': 'error', 'message': 'Database connection not available'}), 503
            
        organism_service = OrganismService(graph)
        organism = organism_service.get_organism(organism_id)
        
        if not organism:
            raise ResourceNotFoundError('Organism not found')
            
        return jsonify(organism)
    except ResourceNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error in get_organism: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500 