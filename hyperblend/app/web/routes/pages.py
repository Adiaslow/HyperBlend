# hyperblend/app/web/routes/pages.py

from flask import Blueprint, render_template, jsonify
from hyperblend.app.web.core.decorators import handle_db_error
from hyperblend.db.neo4j import db
import logging

logger = logging.getLogger(__name__)

pages = Blueprint('pages', __name__)

@pages.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@pages.route('/molecules')
def molecules_page():
    """Render the molecules page."""
    return render_template('molecules.html', item_type='Molecule')

@pages.route('/targets')
def targets_page():
    """Render the targets page."""
    return render_template('targets.html', item_type='Target')

@pages.route('/organisms')
def organisms_page():
    """Render the organisms page."""
    return render_template('organisms.html', item_type='Organism')

@pages.route('/effects')
def effects_page():
    """Render the effects page."""
    return render_template('effects.html', item_type='Effect')

@pages.route('/api/health')
def health_check():
    """
    Check the health status of the application and its services.
    
    Returns:
        JSON response with health status
    """
    try:
        # Check database connection
        db_status = "healthy" if db.verify_connectivity() else "unhealthy"
        
        return jsonify({
            'status': 'healthy' if db_status == 'healthy' else 'degraded',
            'services': {
                'database': db_status
            },
            'version': '1.0.0'  # You might want to get this from your settings
        })
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@pages.route('/api/db-status')
@handle_db_error
def get_db_status():
    """
    Get database status and statistics.
    
    Returns:
        JSON response with database statistics
    """
    try:
        status = db.get_database_stats()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting database status: {str(e)}")
        return jsonify({'error': str(e)}), 500 