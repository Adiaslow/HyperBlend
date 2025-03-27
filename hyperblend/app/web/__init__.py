from flask import Flask, g, render_template
import os
import logging
import datetime
import traceback
import atexit

# Import application components
from hyperblend.app.web.routes.pages import pages
from hyperblend.app.web.routes.molecules import molecules
from hyperblend.app.web.routes.targets import targets
from hyperblend.app.web.routes.effects import effects
from hyperblend.app.web.routes.organisms import organisms
from hyperblend.app.web.routes.graph import graph
from hyperblend.app.web.routes.db import db
from hyperblend.app.web.routes.api import api
from hyperblend.app.web.core.errors import register_error_handlers
from hyperblend.app.web.config import get_config
from hyperblend.database import get_graph
from flask_cors import CORS
from flask_bootstrap import Bootstrap
from hyperblend.app.config.settings import settings
from py2neo import Graph
from hyperblend.utils.job_queue import start_worker, stop_worker

# Import repositories
from hyperblend.repository.molecule_repository import MoleculeRepository
from hyperblend.repository.target_repository import TargetRepository
from hyperblend.repository.organism_repository import OrganismRepository
from hyperblend.repository.effect_repository import EffectRepository

# Import services
from hyperblend.services.internal.molecule_service import MoleculeService
from hyperblend.services.internal.target_service import TargetService
from hyperblend.services.internal.organism_service import OrganismService
from hyperblend.services.internal.effect_service import EffectService

logger = logging.getLogger(__name__)


def get_db():
    """Get or create database connection."""
    if not hasattr(g, "neo4j_db"):
        # Create new Graph instance if none exists
        try:
            logger.info("Creating new Neo4j connection")
            g.neo4j_db = Graph(
                settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            logger.info("Neo4j connection established successfully")
        except Exception as e:
            logger.error(f"Error connecting to Neo4j: {str(e)}")
            logger.error(traceback.format_exc())
            # Still need to return something to avoid cascading errors
            raise
    return g.neo4j_db


def create_app(config_name="development"):
    """Create and configure the Flask application."""
    # Calculate absolute paths for templates and static folders
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_folder = os.path.join(current_dir, "templates")
    static_folder = os.path.join(current_dir, "static")

    # Ensure the paths exist - this is for debugging
    logger.info(f"Template folder path: {template_folder}")
    logger.info(f"Static folder path: {static_folder}")
    logger.info(f"Template folder exists: {os.path.exists(template_folder)}")
    logger.info(f"Static folder exists: {os.path.exists(static_folder)}")

    # Create the Flask app with absolute paths
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)

    # Configure logging early
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set specific log levels for different components
    logging.getLogger("hyperblend.app.web").setLevel(logging.INFO)
    logging.getLogger("hyperblend.app.web.routes").setLevel(logging.INFO)
    logging.getLogger("hyperblend.utils.db_utils").setLevel(logging.INFO)
    logging.getLogger("hyperblend.repository").setLevel(logging.INFO)

    # Set external libraries to WARNING or higher to reduce noise
    logging.getLogger("py2neo").setLevel(logging.WARNING)
    logging.getLogger("py2neo.client").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("urllib3.util").setLevel(logging.WARNING)

    # Database connection errors should still be visible
    logging.getLogger("hyperblend.database").setLevel(logging.INFO)

    # Load configuration
    app_config = get_config(config_name)
    app.config.from_object(app_config)

    # Set development mode for admin authentication
    app.config["ENV"] = os.environ.get("FLASK_ENV", config_name)
    app.config["BYPASS_ADMIN_AUTH"] = (
        os.environ.get("BYPASS_ADMIN_AUTH", "false").lower() == "true"
    )

    # Set admin credentials
    app.config["ADMIN_PASSWORD"] = os.environ.get(
        "HYPERBLEND_ADMIN_PASSWORD", "hyperblend_admin"
    )
    app.config["ADMIN_TOKEN"] = os.environ.get(
        "HYPERBLEND_ADMIN_TOKEN", "admin_token_for_hyperblend"
    )

    # Add custom Jinja2 functions
    @app.context_processor
    def utility_processor():
        def now():
            return datetime.datetime.now()

        return dict(now=now)

    # Initialize extensions - update CORS to allow all origins in development
    if app.config["ENV"] == "development" or app.config["DEBUG"]:
        # In development, allow all origins
        CORS(app, resources={r"/*": {"origins": "*"}})
        logger.info("CORS configured for development (all origins allowed)")
    else:
        # In production, be more restrictive
        CORS(app, resources={r"/api/*": {"origins": "*"}})
        logger.info("CORS configured for production (restricted origins)")

    Bootstrap(app)

    # Register error handlers
    register_error_handlers(app)

    # Database connection setup
    @app.before_request
    def before_request():
        """Ensure database connection is available for each request."""
        try:
            # Get database connection
            g.db = get_db()

            # Create repositories and services
            try:
                # Create repositories
                g.molecule_repository = MoleculeRepository(g.db)
                g.target_repository = TargetRepository(g.db)
                g.organism_repository = OrganismRepository(g.db)
                g.effect_repository = EffectRepository(g.db, use_database=True)

                # Create services with repositories
                g.molecule_service = MoleculeService(
                    graph=g.db, molecule_repository=g.molecule_repository
                )
                g.target_service = TargetService(
                    graph=g.db, target_repository=g.target_repository
                )
                g.organism_service = OrganismService(
                    graph=g.db,
                    organism_repository=g.organism_repository,
                    molecule_repository=g.molecule_repository,
                )
                g.effect_service = EffectService(
                    graph=g.db, effect_repository=g.effect_repository
                )
            except Exception as e:
                logger.error(f"Error creating repositories or services: {str(e)}")
                logger.error(traceback.format_exc())
                # Continue without failing to allow fallback to direct queries

        except Exception as e:
            logger.error(f"Error in before_request: {str(e)}")
            logger.error(traceback.format_exc())
            # Don't raise the exception - allow the request to continue
            # but repositories and services might not be available

    # Start the background job worker
    start_worker()
    logger.info("Started background job worker")

    # Register shutdown handler for the job worker
    atexit.register(stop_worker)
    logger.info("Registered shutdown handler for job worker")

    @app.teardown_appcontext
    def teardown_db(error):
        """Close the database connection when the application shuts down."""
        if hasattr(g, "neo4j_db"):
            g.neo4j_db = None

    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors."""
        logger.error(f"Internal Server Error: {error}")
        return render_template("500.html"), 500

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle not found errors."""
        logger.error(f"Not Found Error: {error}")
        return render_template("404.html"), 404

    # Register blueprints
    app.register_blueprint(pages)
    app.register_blueprint(molecules)
    app.register_blueprint(targets)
    app.register_blueprint(effects)
    app.register_blueprint(organisms)
    app.register_blueprint(graph)
    app.register_blueprint(db)
    app.register_blueprint(api)

    return app
