# hyperblend/app/web/core/decorators.py

from functools import wraps
from flask import jsonify, request
from hyperblend.app.web.core.exceptions import DatabaseError, ServiceError
import logging

logger = logging.getLogger(__name__)

def handle_db_error(f):
    """Decorator to handle database errors."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except DatabaseError as e:
            logger.error(f"Database error in {f.__name__}: {str(e)}")
            return jsonify({"error": "Database error", "message": str(e)}), 503
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500
    return decorated_function

def handle_service_error(f):
    """Decorator to handle service-related errors."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ServiceError as e:
            logger.error(f"Service error in {f.__name__}: {str(e)}")
            return jsonify({"error": "Service error", "message": str(e)}), 503
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500
    return decorated_function

def validate_json(f):
    """Decorator to validate JSON payload."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({"error": "Missing JSON in request"}), 400
        return f(*args, **kwargs)
    return decorated_function

def cors_enabled(f):
    """Decorator to handle CORS headers."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        if isinstance(response, tuple):
            response, status_code = response
        else:
            status_code = 200
        
        if isinstance(response, dict):
            response = jsonify(response)
        
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        
        return response, status_code
    return decorated_function 