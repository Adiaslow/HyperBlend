# hyperblend/app/web/app.py

from flask import Flask, g, render_template
from flask_cors import CORS
from flask_bootstrap import Bootstrap
from hyperblend.app.config.settings import settings
from hyperblend.db.neo4j import db
from py2neo import Graph
import logging
import os
from hyperblend.app.web.routes import (
    molecules, targets, effects, organisms,
    pages, graph, db, api
)

logger = logging.getLogger(__name__)

def get_db():
    """Get or create database connection."""
    if not hasattr(g, 'neo4j_db'):
        # Create new Graph instance if none exists
        g.neo4j_db = Graph(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
    return g.neo4j_db

def create_app():
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder=settings.STATIC_FOLDER,
        template_folder=settings.TEMPLATE_FOLDER,
    )

    # Load configuration
    app.config.update(settings.to_dict())
    app.config["SERVER_NAME"] = None  # Let Flask handle the host:port binding
    app.config["SECRET_KEY"] = settings.SECRET_KEY

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger.info(f"Template folder: {settings.TEMPLATE_FOLDER}")
    logger.info(f"Static folder: {settings.STATIC_FOLDER}")

    # Initialize extensions
    CORS(app, resources={r"/api/*": {"origins": settings.CORS_ORIGINS}})
    Bootstrap(app)

    # Register blueprints
    app.register_blueprint(molecules)
    app.register_blueprint(targets)
    app.register_blueprint(effects)
    app.register_blueprint(organisms)
    app.register_blueprint(pages)
    app.register_blueprint(graph)
    app.register_blueprint(db)
    app.register_blueprint(api)

    @app.before_request
    def before_request():
        """Ensure database connection is available for each request."""
        g.db = get_db()

    @app.teardown_appcontext
    def teardown_db(error):
        """Close the database connection when the application shuts down."""
        if hasattr(g, 'neo4j_db'):
            g.neo4j_db = None

    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors."""
        logger.error(f"Internal Server Error: {error}")
        return render_template('500.html'), 500

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle not found errors."""
        logger.error(f"Not Found Error: {error}")
        return render_template('404.html'), 404

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5001, debug=True)
