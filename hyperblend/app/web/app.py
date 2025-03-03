# hyperblend/app/web/app.py

from flask import Flask, g, request
from flask_cors import CORS
from hyperblend.app.config.settings import settings
from hyperblend.app.db.neo4j import db
import logging

logger = logging.getLogger(__name__)


def create_app():
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder=settings.STATIC_FOLDER,
        template_folder=settings.TEMPLATE_FOLDER,
    )

    # Load configuration
    app.config.update(settings.to_dict())

    # Initialize extensions
    CORS(app, resources={r"/api/*": {"origins": settings.CORS_ORIGINS}})

    # Register blueprints
    from .routes import main as main_blueprint

    app.register_blueprint(main_blueprint)

    # Initialize database
    def init_db():
        """Initialize database connection."""
        if not hasattr(g, "db_initialized"):
            try:
                # Connect to database if not already connected
                if not db.driver:
                    db.connect()
                    db.verify_connection()

                # Only perform one-time initialization tasks
                if not db._initialized:
                    db.remove_duplicates()
                    db.create_constraints()
                    db.create_indexes()
                    logger.info("Database initialized successfully")
                else:
                    logger.debug("Database already initialized")

                g.db_initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize database: {str(e)}")
                raise

    @app.before_request
    def before_request():
        """Initialize database before each request if not already initialized."""
        # Skip database initialization for static files
        if not request.path.startswith("/static/"):
            init_db()

    @app.teardown_appcontext
    def close_db(error):
        """Close the database connection when the app context is torn down."""
        if hasattr(g, "db_initialized"):
            db.close()

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors."""
        return {"error": "Not Found"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors."""
        return {"error": "Internal Server Error"}, 500

    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 Forbidden errors."""
        return {"error": "Forbidden"}, 403

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5001, debug=True)
