# hyperblend/app/web/app.py

from flask import Flask, g, request
from flask_cors import CORS
from flask_bootstrap import Bootstrap
from hyperblend.app.config.settings import settings
from hyperblend.db.neo4j import db
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
    app.config["SERVER_NAME"] = f"{settings.HOST}:{settings.PORT}"

    # Initialize extensions
    CORS(app, resources={r"/api/*": {"origins": settings.CORS_ORIGINS}})
    Bootstrap(app)

    # Register blueprints
    from .routes import main as main_blueprint, init_app

    app.register_blueprint(main_blueprint)

    # Initialize services
    init_app(app)

    # Initialize database
    def init_db():
        """Initialize database connection."""
        if not hasattr(g, "db_initialized"):
            try:
                # Connect to database if not already connected
                if not db.driver:
                    db.connect()

                # Verify connectivity with retries
                if not db.verify_connectivity():
                    raise Exception("Failed to verify database connectivity")

                # Only perform one-time initialization tasks if needed
                if not db._initialized:
                    try:
                        db.create_constraints()
                        db.create_indexes()
                        db.remove_duplicates()
                        logger.info("Database initialized successfully")
                    except Exception as e:
                        logger.error(
                            f"Failed to perform database initialization tasks: {str(e)}"
                        )
                        # Continue even if initialization tasks fail
                        pass
                else:
                    logger.debug("Database already initialized")

                g.db_initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize database: {str(e)}")
                g.db_initialized = False
                raise

    @app.before_request
    def before_request():
        """Initialize database before each request if not already initialized."""
        # Skip database initialization for static files and health check endpoint
        if not request.path.startswith("/static/") and not request.path == "/health":
            init_db()

    @app.teardown_appcontext
    def close_db(error):
        """Close the database connection when the app context is torn down."""
        if hasattr(g, "db_initialized") and not g.db_initialized:
            # Only close the connection if initialization failed
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
