# hyperblend/app/web/routes/molecules.py

from flask import Blueprint, jsonify, request
from hyperblend.app.web.core.decorators import handle_db_error, cors_enabled, validate_json
from hyperblend.app.web.core.exceptions import ResourceNotFoundError
from hyperblend.services.internal.molecule_service import MoleculeService
from hyperblend.models.molecule import Molecule
from hyperblend.database import get_graph

molecules = Blueprint('molecules', __name__)

@molecules.route('/api/molecules', methods=['GET'])
@cors_enabled
@handle_db_error
def list_molecules():
    """
    Get all molecules or search for molecules.
    
    Query Parameters:
        q (str, optional): Search query string
        
    Returns:
        JSON response with list of molecules
    """
    molecule_service = MoleculeService(get_graph())
    query = request.args.get('q', '').strip()
    
    try:
        if query:
            molecules = molecule_service.search_molecules(query)
        else:
            molecules = molecule_service.get_all_molecules()
        return jsonify({'status': 'success', 'molecules': molecules})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 503

@molecules.route('/api/molecules/<molecule_id>', methods=['GET'])
@cors_enabled
@handle_db_error
def get_molecule(molecule_id: str):
    """
    Get a specific molecule by ID.
    
    Args:
        molecule_id: The ID of the molecule to retrieve
        
    Returns:
        JSON response with molecule details
    """
    molecule_service = MoleculeService(get_graph())
    try:
        molecule = molecule_service.get_molecule(molecule_id)
        if not molecule:
            raise ResourceNotFoundError('Molecule not found')
        return jsonify(molecule)
    except ResourceNotFoundError as e:
        return jsonify({'error': str(e)}), 404

@molecules.route('/api/molecules', methods=['POST'])
@cors_enabled
@handle_db_error
@validate_json
def create_molecule():
    """
    Create a new molecule.
    
    Request Body:
        JSON object containing molecule data
    
    Returns:
        JSON response with created molecule
    """
    molecule_service = MoleculeService(get_graph())
    try:
        data = request.get_json()
        created_molecule = molecule_service.create_molecule(data)
        if not created_molecule:
            raise ValueError("Failed to create molecule")
        return jsonify(created_molecule), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@molecules.route('/api/molecules/<molecule_id>', methods=['PUT'])
@cors_enabled
@handle_db_error
@validate_json
def update_molecule(molecule_id: str):
    """
    Update an existing molecule.
    
    Args:
        molecule_id: The ID of the molecule to update
    
    Request Body:
        JSON object containing updated molecule data
        
    Returns:
        JSON response with updated molecule
    """
    molecule_service = MoleculeService(get_graph())
    try:
        data = request.get_json()
        updated_molecule = molecule_service.update_molecule(molecule_id, data)
        if not updated_molecule:
            raise ResourceNotFoundError('Molecule not found')
        return jsonify(updated_molecule)
    except ResourceNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@molecules.route('/api/molecules/<molecule_id>', methods=['DELETE'])
@cors_enabled
@handle_db_error
def delete_molecule(molecule_id: str):
    """
    Delete a molecule.
    
    Args:
        molecule_id: The ID of the molecule to delete
        
    Returns:
        Empty response on success
    """
    molecule_service = MoleculeService(get_graph())
    try:
        if molecule_service.delete_molecule(molecule_id):
            return '', 204
        raise ResourceNotFoundError('Molecule not found')
    except ResourceNotFoundError as e:
        return jsonify({'error': str(e)}), 404

@molecules.route('/api/molecules/<molecule_id>/enrich', methods=['POST'])
@cors_enabled
@handle_db_error
@validate_json
def enrich_molecule(molecule_id: str):
    """
    Enrich a molecule with data from external databases.
    
    Args:
        molecule_id: The ID of the molecule to enrich
    
    Request Body:
        {
            "database": str,  # The external database to use (e.g., "pubchem", "chembl")
            "identifier": str  # The identifier in the external database
        }
        
    Returns:
        JSON response with enrichment results
    """
    molecule_service = MoleculeService(get_graph())
    try:
        data = request.get_json()
        if not data or 'database' not in data or 'identifier' not in data:
            return jsonify({'error': 'Missing database or identifier'}), 400
            
        result = molecule_service.enrich_molecule(
            molecule_id,
            data['database'],
            data['identifier']
        )
        if not result:
            raise ResourceNotFoundError('Molecule not found')
        return jsonify(result)
    except ResourceNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400 