# hyperblend/app/web/routes.py

from flask import (
    Blueprint,
    render_template,
    jsonify,
    request,
    make_response,
    send_from_directory,
    current_app,
    Response,
)
from functools import wraps
from hyperblend.services.internal.molecule_service import MoleculeService
from hyperblend.models.molecule import Molecule
from hyperblend.services.external.pubchem_service import PubChemService
from hyperblend.db.neo4j import db
import os
import logging
from hyperblend.services.external.chembl_service import ChEMBLService
from py2neo import Graph
from hyperblend.app.config.settings import settings
from datetime import datetime
from hyperblend.services.external.uniprot_service import UniProtService
from hyperblend.services.internal.target_service import TargetService
from neo4j.exceptions import ServiceUnavailable
from hyperblend.services.external.drugbank_service import DrugBankService
from hyperblend.app.web.utils import get_neo4j_connection
import time

# Create blueprint
main = Blueprint("main", __name__)

# Initialize logger
logger = logging.getLogger(__name__)


def handle_db_error(func):
    """Decorator to handle database errors."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ServiceUnavailable as e:
            logger.error(f"Database connection error in {func.__name__}: {str(e)}")
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Database connection error. Please try again later.",
                        "error_type": "database_connection",
                    }
                ),
                503,
            )
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": str(e),
                        "error_type": "general_error",
                    }
                ),
                500,
            )

    return wrapper


def initialize_services(app=None):
    """Initialize database services with proper error handling."""
    global molecule_service, pubchem_api, graph, chembl_service, target_service

    try:
        # First, ensure we have a valid Neo4j connection
        graph = get_neo4j_connection()
        if not graph:
            logger.error("Failed to establish Neo4j connection during initialization")
            return False

        # Get configuration
        config = {}
        if app:
            config = app.config
        else:
            from flask import current_app

            config = current_app.config

        # Initialize core services
        try:
            molecule_service = MoleculeService(
                graph, drugbank_api_key=config.get("DRUGBANK_API_KEY")
            )
            logger.info("Successfully initialized MoleculeService")
        except Exception as e:
            logger.error(
                f"Failed to initialize MoleculeService: {str(e)}", exc_info=True
            )
            molecule_service = None

        try:
            pubchem_api = PubChemService(graph)
            logger.info("Successfully initialized PubChemService")
        except Exception as e:
            logger.error(f"Failed to initialize PubChemService: {str(e)}")
            pubchem_api = None

        try:
            chembl_service = ChEMBLService(graph)
            logger.info("Successfully initialized ChEMBLService")
        except Exception as e:
            logger.error(f"Failed to initialize ChEMBLService: {str(e)}")
            chembl_service = None

        try:
            target_service = TargetService(graph)
            logger.info("Successfully initialized TargetService")
        except Exception as e:
            logger.error(f"Failed to initialize TargetService: {str(e)}")
            target_service = None

        # Check if critical services are available
        if not molecule_service:
            logger.error("Critical service MoleculeService failed to initialize")
            return False

        logger.info("Successfully initialized all services")
        return True

    except Exception as e:
        logger.error(
            f"Failed to initialize services: {str(e)}",
            exc_info=True,
        )
        graph = None
        molecule_service = None
        pubchem_api = None
        chembl_service = None
        target_service = None
        return False


def init_app(app):
    """Initialize the Flask application with services."""
    with app.app_context():
        initialization_result = initialize_services(app)
        if not initialization_result:
            logger.error(
                "Failed to initialize services on startup. "
                "The application will continue to run but some features may be unavailable."
            )


def add_cors_headers(response):
    """Add CORS headers to the response."""
    # Handle tuple responses (error responses with status codes)
    if isinstance(response, tuple):
        response_obj = make_response(response[0])
        response_obj.status_code = response[1]
        response = response_obj
    elif not isinstance(response, Response):
        response = make_response(response)

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def cors_enabled(f):
    """Decorator to enable CORS for routes."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        return add_cors_headers(response)

    return decorated_function


@main.route("/")
def index():
    """Render the main page."""
    try:
        return render_template("index.html", now=datetime.now())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route("/test")
def test():
    """Test route to verify the application is working."""
    return jsonify({"status": "ok", "message": "Test route working!"})


@main.route("/static/<path:filename>")
def serve_static(filename):
    """Serve static files."""
    try:
        return send_from_directory(main.static_folder, filename)
    except Exception as e:
        return make_response(jsonify({"error": str(e)}), 404)


@main.route("/api/graph")
def get_graph():
    """Get graph data for visualization."""
    try:
        search_query = request.args.get("q", "")
        logger.info(f"Fetching graph data with query: {search_query}")

        # Get nodes with labels and relationships
        cypher_query = """
        MATCH (n)
        WHERE n.name IS NOT NULL
        AND (CASE WHEN $search_query <> ''
             THEN toLower(n.name) CONTAINS toLower($search_query)
             ELSE true END)
        AND (n:Molecule OR n:Organism OR n:Target)
        WITH n
        OPTIONAL MATCH (n)-[r]->(m)
        WHERE m.name IS NOT NULL
        AND (m:Molecule OR m:Organism OR m:Target)
        WITH n, collect(DISTINCT m) as neighbors,
             collect(DISTINCT {
                 id: toString(elementId(m)),
                 name: m.name,
                 type: labels(m)[0],
                 relationship_type: type(r),
                 activity_type: r.activity_type,
                 activity_value: CASE 
                     WHEN r.activity_value IS NOT NULL AND r.activity_unit IS NOT NULL
                     THEN r.activity_value + ' ' + r.activity_unit
                     WHEN r.activity_value IS NOT NULL
                     THEN toString(r.activity_value)
                     ELSE null 
                 END,
                 confidence_score: r.confidence_score
             }) as connections
        RETURN DISTINCT toString(elementId(n)) as id, 
               n.name as name,
               labels(n)[0] as type,
               n.smiles as smiles,
               n.description as description,
               n.molecular_weight as molecular_weight,
               n.formula as formula,
               n.organism as organism,
               n.confidence_score as confidence_score,
               size(neighbors) as degree,
               connections
        ORDER BY degree DESC
        LIMIT 100
        """

        nodes = graph.run(cypher_query, search_query=search_query)

        # Process nodes and create links
        processed_nodes = []
        links = []
        node_map = {}
        connections_map = {}  # Store connections for later processing

        # First pass: Process all nodes
        for record in nodes:
            node_data = {
                "id": record["id"],
                "name": record["name"],
                "type": record["type"],
                "smiles": record["smiles"],
                "description": record["description"],
                "molecular_weight": record["molecular_weight"],
                "formula": record["formula"],
                "organism": record["organism"],
                "confidence_score": record["confidence_score"],
                "degree": record["degree"],
                "width": 30,  # Set a default width for all nodes
            }
            processed_nodes.append(node_data)
            node_map[record["id"]] = True
            connections_map[record["id"]] = record["connections"]

        # Second pass: Process all connections to create links
        for node_id, connections in connections_map.items():
            for conn in connections:
                if conn["id"] in node_map:
                    link_data = {
                        "source": node_id,
                        "target": conn["id"],
                        "type": conn["relationship_type"],
                        "activity_type": conn.get("activity_type", "unknown"),
                        "activity_value": conn.get("activity_value"),
                        "confidence_score": conn.get("confidence_score", 0.5),
                    }
                    links.append(link_data)

        logger.info(f"Returning {len(processed_nodes)} nodes and {len(links)} links")
        return jsonify({"nodes": processed_nodes, "links": links})

    except Exception as e:
        logger.error(f"Error getting graph data: {str(e)}")
        return jsonify({"error": str(e)}), 500


@main.route("/molecules")
def molecules_page():
    """Render the molecules list page."""
    return render_template("molecules.html", item_type="Molecule", now=datetime.now())


@main.route("/sources")
def sources_page():
    """Render the sources page."""
    return render_template("sources.html", now=datetime.now())


@main.route("/targets")
def targets_page():
    """Render the targets list page."""
    return render_template("targets.html", item_type="Target", now=datetime.now())


@main.route("/api/molecules", methods=["GET"])
def get_molecules():
    """Get a list of molecules, optionally filtered by search query."""
    try:
        if not molecule_service:
            logger.error("Molecule service is not available")
            return (
                jsonify(
                    {
                        "error": "Database service unavailable",
                        "message": "The molecule service is currently unavailable. Please try again later.",
                        "items": [],
                    }
                ),
                503,
            )

        # Get a new connection for this request
        graph = get_neo4j_connection()
        if not graph:
            logger.error("Failed to establish database connection")
            return (
                jsonify(
                    {
                        "error": "Database connection unavailable",
                        "message": "Could not establish a connection to the database. Please try again later.",
                        "items": [],
                    }
                ),
                503,
            )

        query = request.args.get("q", "").strip()
        search_pattern = f"(?i).*{query}.*"

        # Get molecules from the database
        try:
            cypher_query = """
            MATCH (m:Molecule)
            WHERE m.name IS NOT NULL
            AND (
                $query = '' OR 
                m.name =~ $search_pattern OR
                m.formula =~ $search_pattern OR
                m.smiles =~ $search_pattern
            )
            RETURN {
                id: toString(elementId(m)),
                name: m.name,
                formula: m.formula,
                smiles: m.smiles,
                description: m.description,
                molecular_weight: m.molecular_weight
            } as molecule
            ORDER BY molecule.name
            """

            result = graph.run(cypher_query, query=query, search_pattern=search_pattern)
            molecules = [dict(record["molecule"]) for record in result]

            return jsonify(
                {"items": molecules if molecules else [], "status": "success"}
            )
        except Exception as e:
            logger.error(f"Database query error: {str(e)}", exc_info=True)
            return (
                jsonify(
                    {
                        "error": "Database query failed",
                        "message": "An error occurred while querying the database. Please try again later.",
                        "items": [],
                    }
                ),
                500,
            )
    except Exception as e:
        logger.error(f"Error getting molecules: {str(e)}", exc_info=True)
        return (
            jsonify(
                {
                    "error": str(e),
                    "message": "An unexpected error occurred. Please try again later.",
                    "items": [],
                }
            ),
            500,
        )


@main.route("/api/molecules/<molecule_id>", methods=["GET"])
def get_molecule(molecule_id):
    """Get a specific molecule by ID with its relationships."""
    try:
        if not molecule_service:
            return jsonify({"error": "Database service unavailable"}), 503

        # Get molecule details with relationships
        cypher_query = """
        MATCH (m:Molecule)
        WHERE toString(elementId(m)) = $molecule_id
        OPTIONAL MATCH (m)-[r]-(related)
        WHERE (related:Target OR related:Organism)
        WITH m, collect(DISTINCT {
            id: toString(elementId(related)),
            name: related.name,
            type: labels(related)[0],
            relationship_type: type(r),
            activity_type: r.activity_type,
            activity_value: r.activity_value,
            activity_unit: r.activity_unit,
            confidence_score: r.confidence_score,
            created_at: toString(r.created_at),
            updated_at: toString(r.updated_at)
        }) as relationships
        RETURN {
            id: toString(elementId(m)),
            name: m.name,
            formula: m.formula,
            molecular_weight: m.molecular_weight,
            smiles: m.smiles,
            inchi: m.inchi,
            inchikey: m.inchikey,
            pubchem_cid: m.pubchem_cid,
            chembl_id: m.chembl_id,
            drugbank_id: m.drugbank_id,
            logp: m.logp,
            polar_surface_area: m.polar_surface_area,
            relationships: relationships
        } as molecule
        """

        result = graph.run(cypher_query, molecule_id=molecule_id).data()
        if not result:
            return jsonify({"error": "Molecule not found"}), 404

        molecule_data = result[0]["molecule"]
        return jsonify(molecule_data)
    except Exception as e:
        logger.error(f"Error getting molecule: {str(e)}")
        return jsonify({"error": str(e)}), 500


@main.route("/api/molecules/<molecule_id>/related", methods=["GET"])
def get_molecule_related(molecule_id):
    """Get related nodes for a molecule."""
    try:
        if not molecule_service:
            return jsonify({"error": "Database service unavailable"}), 503

        related = molecule_service.get_molecule_related(molecule_id)
        return jsonify(related)
    except Exception as e:
        logger.error(f"Error getting related nodes: {str(e)}")
        return jsonify({"error": str(e)}), 500


@main.route("/api/molecules", methods=["POST"])
def create_molecule():
    """Create a new molecule."""
    try:
        if not molecule_service:
            return jsonify({"error": "Database service unavailable"}), 503

        data = request.get_json()
        molecule = Molecule(**data)
        created_molecule = molecule_service.create_molecule(molecule)
        return jsonify(created_molecule.model_dump()), 201
    except Exception as e:
        logger.error(f"Error creating molecule: {str(e)}")
        return jsonify({"error": str(e)}), 500


@main.route("/api/molecules/<molecule_id>", methods=["PUT"])
def update_molecule(molecule_id):
    """Update an existing molecule."""
    try:
        if not molecule_service:
            return jsonify({"error": "Database service unavailable"}), 503

        data = request.get_json()
        molecule = Molecule(**data)
        updated_molecule = molecule_service.update_molecule(molecule_id, molecule)
        if updated_molecule:
            return jsonify(updated_molecule.model_dump())
        return jsonify({"error": "Molecule not found"}), 404
    except Exception as e:
        logger.error(f"Error updating molecule: {str(e)}")
        return jsonify({"error": str(e)}), 500


@main.route("/api/molecules/<molecule_id>", methods=["DELETE"])
def delete_molecule(molecule_id):
    """Delete a molecule."""
    try:
        if not molecule_service:
            return jsonify({"error": "Database service unavailable"}), 503

        if molecule_service.delete_molecule(molecule_id):
            return "", 204
        return jsonify({"error": "Molecule not found"}), 404
    except Exception as e:
        logger.error(f"Error deleting molecule: {str(e)}")
        return jsonify({"error": str(e)}), 500


@main.route("/api/molecules/cas/<cas_number>", methods=["POST"])
def create_molecule_by_cas(cas_number):
    """Create a new molecule using its CAS number."""
    try:
        molecule = molecule_service.create_molecule_from_cas(cas_number)
        if molecule:
            return jsonify(molecule.model_dump()), 201
        return jsonify({"error": "Molecule not found or already exists"}), 404
    except Exception as e:
        logger.error(f"Error creating molecule from CAS {cas_number}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@main.route("/api/molecules/add", methods=["POST"])
def add_molecule():
    """Add a molecule using a database identifier."""
    try:
        data = request.get_json()
        db_type = data.get("type")
        identifier = data.get("identifier")

        if not db_type or not identifier:
            return jsonify({"error": "Missing type or identifier"}), 400

        # Create molecule based on database type
        if db_type == "cas":
            molecule = molecule_service.create_molecule_from_cas(identifier)
        elif db_type == "pubchem":
            molecule = molecule_service.create_molecule_from_pubchem(identifier)
        elif db_type == "chembl":
            molecule = molecule_service.create_molecule_from_chembl(identifier)
        elif db_type == "drugbank":
            molecule = DrugBankService(
                api_key=current_app.config["DRUGBANK_API_KEY"], graph=graph
            ).get_molecule_by_drugbank_id(identifier)
            if not molecule:
                return jsonify({"error": "Molecule not found"}), 404
        elif db_type == "coconut":
            molecule = molecule_service.create_molecule_from_coconut(identifier)
        else:
            return jsonify({"error": "Invalid database type"}), 400

        if molecule:
            return jsonify(molecule.model_dump()), 201
        return jsonify({"error": "Molecule not found or already exists"}), 404
    except Exception as e:
        logger.error(f"Error adding molecule: {str(e)}")
        return jsonify({"error": str(e)}), 500


@main.route("/api/molecules", methods=["GET", "POST", "OPTIONS"])
@cors_enabled
def molecules_api():
    """Handle molecule operations."""
    if request.method == "GET":
        return get_molecules()
    elif request.method == "POST":
        return create_molecule()
    return "", 204


@main.route("/api/molecules/<molecule_id>", methods=["GET", "PUT", "DELETE", "OPTIONS"])
@cors_enabled
def molecule(molecule_id):
    """Handle operations on a specific molecule."""
    if request.method == "GET":
        return get_molecule(molecule_id)
    elif request.method == "PUT":
        return update_molecule(molecule_id)
    elif request.method == "DELETE":
        return delete_molecule(molecule_id)
    return "", 204


@main.route("/api/molecules/search/<database>/<identifier>", methods=["GET", "OPTIONS"])
@cors_enabled
def search_molecule(database, identifier):
    """Search for a molecule in external databases."""
    try:
        if not molecule_service:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Database service unavailable",
                        "error_type": "service_unavailable",
                    }
                ),
                503,
            )

        if database == "drugbank":
            if not molecule_service.drugbank_service:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "DrugBank service unavailable - missing API key",
                            "error_type": "service_unavailable",
                        }
                    ),
                    503,
                )

            try:
                molecule = molecule_service.get_molecule_from_drugbank(identifier)
                if not molecule:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "Molecule not found in DrugBank",
                                "error_type": "not_found",
                            }
                        ),
                        404,
                    )
                return jsonify({"status": "success", "data": molecule})
            except Exception as e:
                logger.error(f"Error searching DrugBank: {str(e)}")
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": f"Error searching DrugBank: {str(e)}",
                            "error_type": "search_error",
                        }
                    ),
                    500,
                )

        elif database == "pubchem":
            if not pubchem_api:
                return (
                    jsonify(
                        {"status": "error", "message": "PubChem service unavailable"}
                    ),
                    503,
                )

            try:
                # Determine the type of identifier and search accordingly
                if identifier.isdigit():
                    molecule = pubchem_api.get_molecule_by_cid(int(identifier))
                elif identifier.startswith("C") and identifier[1:].isdigit():
                    molecule = pubchem_api.get_molecule_by_cid(int(identifier[1:]))
                elif all(c in "CN()O123456789" for c in identifier):
                    molecule = pubchem_api.search_molecule_by_smiles(identifier)
                else:
                    molecules = pubchem_api.search_molecule_by_name(identifier)
                    molecule = molecules[0] if molecules else None

                if not molecule:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "Molecule not found in PubChem",
                            }
                        ),
                        404,
                    )
                return jsonify({"status": "success", "data": molecule.model_dump()})
            except Exception as e:
                logger.error(f"Error searching PubChem: {str(e)}")
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": f"Error searching PubChem: {str(e)}",
                        }
                    ),
                    500,
                )

        elif database == "chembl":
            if not molecule_service.chembl_service:
                return (
                    jsonify(
                        {"status": "error", "message": "ChEMBL service unavailable"}
                    ),
                    503,
                )

            try:
                molecule = molecule_service.chembl_service.get_molecule_by_chembl_id(
                    identifier
                )
                if not molecule:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "Molecule not found in ChEMBL",
                            }
                        ),
                        404,
                    )
                return jsonify({"status": "success", "data": molecule.model_dump()})
            except Exception as e:
                logger.error(f"Error searching ChEMBL: {str(e)}")
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": f"Error searching ChEMBL: {str(e)}",
                        }
                    ),
                    500,
                )

        else:
            return (
                jsonify(
                    {"status": "error", "message": f"Unsupported database: {database}"}
                ),
                400,
            )

    except Exception as e:
        logger.error(f"Error in search_molecule: {str(e)}")
        return (
            jsonify({"status": "error", "message": f"Internal server error: {str(e)}"}),
            500,
        )


@main.route("/api/db-status")
def get_db_status():
    """Get database status and statistics."""
    try:
        status = molecule_service.check_database_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting database status: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main.route("/api/targets", methods=["GET"])
@handle_db_error
def get_targets():
    """Get all targets or search for targets."""
    try:
        graph = get_neo4j_connection()
        if not graph:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Database connection unavailable",
                        "targets": [],
                    }
                ),
                503,
            )

        target_service = TargetService(graph)
        query = request.args.get("q", "").strip()

        if query:
            targets = target_service.search_targets(query)
        else:
            targets = target_service.get_all_targets()

        return jsonify({"status": "success", "targets": targets or []})
    except Exception as e:
        logger.error(f"Error in get_targets: {str(e)}")
        return jsonify({"status": "error", "message": str(e), "targets": []}), 500


@main.route("/api/targets/<target_id>", methods=["GET"])
@handle_db_error
def get_target(target_id):
    """Get a specific target by ID."""
    try:
        graph = get_neo4j_connection()
        if not graph:
            return (
                jsonify(
                    {"status": "error", "message": "Database connection unavailable"}
                ),
                503,
            )

        target_service = TargetService(graph)
        target = target_service.get_target(target_id)

        if not target:
            return jsonify({"status": "error", "message": "Target not found"}), 404

        # Get associated molecules
        molecules = target_service.get_target_molecules(target_id)
        target["molecules"] = molecules

        return jsonify({"status": "success", "target": target})
    except Exception as e:
        logger.error(f"Error in get_target: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@main.route("/api/targets/<target_id>", methods=["PUT"])
def update_target(target_id):
    """Update a target."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        graph = get_neo4j_connection()
        target_service = TargetService(graph)
        success = target_service.update_target(target_id, data)

        if not success:
            return (
                jsonify({"status": "error", "message": "Failed to update target"}),
                500,
            )

        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error in update_target: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@main.route("/api/molecules/<molecule_id>/update_targets", methods=["POST"])
def update_molecule_targets(molecule_id):
    """Update targets for a specific molecule."""
    try:
        success = molecule_service.update_molecule_targets(molecule_id)
        if success:
            return jsonify({"message": "Successfully updated molecule targets"})
        return jsonify({"error": "Failed to update molecule targets"}), 400
    except Exception as e:
        logger.error(f"Error updating molecule targets: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main.route("/api/molecules/update_all_targets", methods=["POST"])
def update_all_molecule_targets():
    """Update targets for all molecules."""
    try:
        success = molecule_service.update_all_molecule_targets()
        if success:
            return jsonify({"message": "Successfully updated all molecule targets"})
        return jsonify({"error": "Failed to update molecule targets"}), 400
    except Exception as e:
        logger.error(f"Error updating all molecule targets: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main.route("/api/molecules/<molecule_id>/enrich", methods=["POST"])
def enrich_molecule(molecule_id):
    """Enrich a molecule with data from external databases."""
    try:
        data = request.get_json()
        if not data or "type" not in data or "identifier" not in data:
            return jsonify({"error": "Missing type or identifier"}), 400

        # Get the molecule from our database
        molecule = molecule_service.get_molecule(molecule_id)
        if not molecule:
            return jsonify({"error": "Molecule not found"}), 404

        enrichment_results = []
        updated_data = molecule.copy()  # Start with existing data

        # Try to enrich from the specified database
        if data["type"] == "pubchem":
            pubchem_molecule = pubchem_api.get_molecule_by_cid(int(data["identifier"]))
            if pubchem_molecule:
                pubchem_data = pubchem_molecule.model_dump()
                for key, value in pubchem_data.items():
                    if value and (key not in updated_data or not updated_data[key]):
                        updated_data[key] = value
                enrichment_results.append("Successfully enriched molecule from PubChem")
        elif data["type"] == "chembl":
            chembl_molecule = ChEMBLService(graph).get_molecule_by_chembl_id(
                data["identifier"]
            )
            if chembl_molecule:
                chembl_data = chembl_molecule.model_dump()
                for key, value in chembl_data.items():
                    if value and (key not in updated_data or not updated_data[key]):
                        updated_data[key] = value
                enrichment_results.append("Successfully enriched molecule from ChEMBL")
        elif data["type"] == "drugbank":
            drugbank_molecule = DrugBankService(
                api_key=current_app.config["DRUGBANK_API_KEY"], graph=graph
            ).get_molecule_by_drugbank_id(data["identifier"])
            if drugbank_molecule:
                drugbank_data = drugbank_molecule.model_dump()
                for key, value in drugbank_data.items():
                    if value and (key not in updated_data or not updated_data[key]):
                        updated_data[key] = value
                enrichment_results.append(
                    "Successfully enriched molecule from DrugBank"
                )

        # Update the molecule in the database
        if enrichment_results:
            molecule_service.update_molecule(molecule_id, updated_data)
            return jsonify(
                {"message": " | ".join(enrichment_results), "data": updated_data}
            )
        else:
            return jsonify({"error": "No enrichment data found"}), 404

    except Exception as e:
        logger.error(f"Error enriching molecule {molecule_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@main.route("/api/molecules/enrich_all", methods=["POST"])
def enrich_all_molecules():
    """Enrich all molecules with PubChem and ChEMBL data."""
    try:
        success = molecule_service.enrich_all_molecules()
        if success:
            return jsonify({"message": "Successfully enriched all molecules"})
        return jsonify({"error": "Failed to enrich molecules"}), 400
    except Exception as e:
        logger.error(f"Error enriching all molecules: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main.route("/api/nodes/<node_id>", methods=["GET"])
@cors_enabled
def get_node_details(node_id):
    """Get details for any node type (Molecule, Target, or Organism)."""
    try:
        # Extract the numeric ID from the full element ID format
        # Format is database:uuid:number, we want the number
        numeric_id = node_id.split(":")[-1]

        # Query that works for any node type
        cypher_query = """
        MATCH (n)
        WHERE split(toString(elementId(n)), ':')[-1] = $numeric_id
        OPTIONAL MATCH (n)-[r]-(related)
        WITH n, collect(DISTINCT {
            id: toString(elementId(related)),
            name: related.name,
            type: labels(related)[0],
            relationship: type(r),
            activity: CASE 
                WHEN r.activity_value IS NOT NULL 
                THEN r.activity_value + ' ' + coalesce(r.activity_units, '')
                ELSE null 
            END
        }) as related_nodes
        RETURN toString(elementId(n)) as id,
               n.name as name,
               labels(n)[0] as type,
               n.smiles as smiles,
               n.description as description,
               n.molecular_weight as molecular_weight,
               n.formula as formula,
               n.organism as organism,
               n.confidence_score as confidence_score,
               n.pubchem_cid as pubchem_cid,
               n.chembl_id as chembl_id,
               related_nodes
        """
        # Use the graph object instead of db.run()
        result = graph.run(cypher_query, numeric_id=numeric_id).data()
        if not result:
            return jsonify({"error": "Node not found"}), 404

        # Convert record to dictionary - note that graph.run().data() returns a list of dicts
        record = result[0]
        node_data = {
            "id": record["id"],
            "name": record["name"],
            "type": record["type"],
            "smiles": record.get("smiles"),
            "description": record.get("description"),
            "molecular_weight": record.get("molecular_weight"),
            "formula": record.get("formula"),
            "organism": record.get("organism"),
            "confidence_score": record.get("confidence_score"),
            "pubchem_cid": record.get("pubchem_cid"),
            "chembl_id": record.get("chembl_id"),
            "related_nodes": record["related_nodes"],
        }
        return jsonify(node_data)

    except Exception as e:
        logger.error(f"Error fetching node details: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# Target routes
@main.route("/api/targets/search")
def search_targets():
    """Search for targets in ChEMBL database."""
    query = request.args.get("query")
    limit = request.args.get("limit", 10, type=int)

    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    if not 1 <= limit <= 100:
        return jsonify({"error": "Limit must be between 1 and 100"}), 400

    chembl = ChEMBLService()
    targets = chembl.search_targets(query, limit)
    return jsonify(targets)


@main.route("/api/targets/<string:chembl_id>/details")
def get_target_details(chembl_id):
    """Get detailed information about a specific target."""
    chembl = ChEMBLService()
    details = chembl.get_target_details(chembl_id)

    if not details:
        return jsonify({"error": "Target not found"}), 404

    return jsonify(details)


@main.route("/api/targets/<string:chembl_id>/bioactivities")
def get_target_bioactivities(chembl_id):
    """Get bioactivity data for a specific target."""
    limit = request.args.get("limit", 100, type=int)

    if not 1 <= limit <= 1000:
        return jsonify({"error": "Limit must be between 1 and 1000"}), 400

    chembl = ChEMBLService()
    activities = chembl.get_target_bioactivities(chembl_id, limit)
    return jsonify(activities)


@main.route("/organisms")
def organisms_page():
    """Render the organisms list page."""
    return render_template("organisms.html", item_type="Organism", now=datetime.now())


@main.route("/api/organisms", methods=["GET"])
def get_organisms():
    """Get a list of organisms, optionally filtered by search query."""
    try:
        query = request.args.get("q", "").strip()
        search_pattern = f"(?i).*{query}.*"

        # Get organisms from the database
        cypher_query = """
        MATCH (o:Organism)
        WHERE o.name IS NOT NULL
        AND (
            $query = '' OR 
            o.name =~ $search_pattern OR
            o.scientific_name =~ $search_pattern OR
            o.description =~ $search_pattern
        )
        RETURN {
            id: toString(elementId(o)),
            name: o.name,
            scientific_name: o.scientific_name,
            description: o.description
        } as organism
        ORDER BY organism.name
        """

        result = graph.run(cypher_query, query=query, search_pattern=search_pattern)
        organisms = [dict(record["organism"]) for record in result]

        return jsonify({"items": organisms if organisms else []})
    except Exception as e:
        logger.error(f"Error getting organisms: {str(e)}", exc_info=True)
        return jsonify({"error": str(e), "items": []}), 500


@main.route("/api/organisms/search/<database>/<identifier>")
def search_organism(database, identifier):
    """Search for an organism in an external database."""
    try:
        # Use the appropriate service based on the database
        if database == "ncbi":
            result = organism_service.search_ncbi(identifier)
        elif database == "gbif":
            result = organism_service.search_gbif(identifier)
        elif database == "itis":
            result = organism_service.search_itis(identifier)
        else:
            return jsonify({"error": "Unsupported database"}), 400

        if result:
            return jsonify(result)
        return jsonify({"error": "Organism not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route("/favicon.ico")
def favicon():
    """Serve the favicon."""
    return "", 204  # Return empty response with "No Content" status


@main.route("/effects")
def effects_page():
    """Render the effects list page."""
    return render_template("effects.html", item_type="Effect", now=datetime.now())


@main.route("/api/effects", methods=["GET"])
@cors_enabled
def get_effects():
    """Get a list of effects, optionally filtered by search query."""
    try:
        query = request.args.get("q", "").strip()
        search_pattern = f"(?i).*{query}.*"

        # Get effects from the database
        cypher_query = """
        MATCH (e:Effect)
        WHERE e.name IS NOT NULL
        AND (
            $query = '' OR 
            e.name =~ $search_pattern OR
            e.description =~ $search_pattern
        )
        WITH e
        OPTIONAL MATCH (e)<-[r]-(m:Molecule)
        WITH e, count(m) as molecule_count
        RETURN {
            id: toString(elementId(e)),
            name: e.name,
            description: e.description,
            molecule_count: molecule_count
        } as effect
        ORDER BY effect.name
        """

        results = graph.run(cypher_query, query=query, search_pattern=search_pattern)
        effects = [dict(record["effect"]) for record in results]

        return jsonify(effects)
    except Exception as e:
        logger.error(f"Error in get_effects endpoint: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main.route("/api/effects/<effect_id>", methods=["GET"])
@cors_enabled
def get_effect(effect_id):
    """Get details for a specific effect."""
    try:
        # Get effect details from the database
        cypher_query = """
        MATCH (e:Effect)
        WHERE elementId(e) = $effect_id
        OPTIONAL MATCH (e)<-[r]-(m:Molecule)
        WITH e, collect({
            id: toString(elementId(m)),
            name: m.name,
            smiles: m.smiles,
            relationship: type(r)
        }) as molecules
        RETURN {
            id: toString(elementId(e)),
            name: e.name,
            description: e.description,
            molecules: molecules
        } as effect
        """

        result = graph.run(cypher_query, effect_id=int(effect_id)).data()
        if not result:
            return jsonify({"error": "Effect not found"}), 404

        return jsonify(result[0]["effect"])
    except Exception as e:
        logger.error(f"Error in get_effect endpoint: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main.route("/api/db/cleanup", methods=["POST"])
def cleanup_database():
    """Clean up the database by fixing source nodes."""
    try:
        db.cleanup_source_nodes()
        return jsonify({"message": "Database cleanup completed successfully"})
    except Exception as e:
        logger.error(f"Error during database cleanup: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main.route("/api/targets/<target_id>/enrich", methods=["POST"])
def enrich_target(target_id):
    """Enrich a target with data from external databases."""
    try:
        # Get the target from our database
        target = molecule_service.target_service.get_target(target_id)
        if not target:
            return jsonify({"error": "Target not found"}), 404

        enrichment_results = []
        updated_data = target.copy()  # Start with existing data

        # Get enrichment parameters from request
        data = request.get_json()
        database = data.get("database")
        identifier = data.get("identifier")

        if not database or not identifier:
            return jsonify({"error": "Missing database or identifier"}), 400

        # Try to enrich from ChEMBL
        if database == "chembl":
            chembl_target = molecule_service.chembl_service.get_target_details(
                identifier
            )
            if chembl_target:
                # Merge ChEMBL data with existing data
                for key, value in chembl_target.items():
                    if value and (key not in updated_data or not updated_data[key]):
                        updated_data[key] = value
                if "chembl_id" not in updated_data:
                    updated_data["chembl_id"] = identifier
                enrichment_results.append("Successfully enriched target from ChEMBL")

                # Get and store bioactivity data
                bioactivities = (
                    molecule_service.chembl_service.get_target_bioactivities(identifier)
                )
                if bioactivities:
                    enrichment_results.append(
                        f"Added {len(bioactivities)} bioactivity records from ChEMBL"
                    )

        # Try to enrich from UniProt
        elif database == "uniprot":
            uniprot_target = molecule_service.uniprot_service.get_target_details(
                identifier
            )
            if uniprot_target:
                # Merge UniProt data with existing data
                for key, value in uniprot_target.items():
                    if value and (key not in updated_data or not updated_data[key]):
                        updated_data[key] = value
                if "uniprot_id" not in updated_data:
                    updated_data["uniprot_id"] = identifier
                enrichment_results.append("Successfully enriched target from UniProt")

        # Update the target with merged data
        if enrichment_results:
            success = molecule_service.target_service.update_target(
                target_id, updated_data
            )
            if success:
                return jsonify({"message": enrichment_results})

        return jsonify({"error": "No additional data found in external databases"}), 404

    except Exception as e:
        logger.error(f"Error enriching target: {str(e)}")
        return jsonify({"error": str(e)}), 500


@main.route("/api/uniprot/test")
def test_uniprot():
    """Test the UniProt service functionality."""
    try:
        # Initialize UniProt service
        uniprot_service = UniProtService()

        # Test protein search
        search_results = uniprot_service.search_protein("insulin")

        # Test getting specific protein details
        protein_details = None
        if search_results:
            first_result_id = search_results[0].get("primaryAccession")
            if first_result_id:
                protein_details = uniprot_service.get_protein(first_result_id)

                # Test getting protein sequence
                sequence = uniprot_service.get_protein_sequence(first_result_id)
                if sequence:
                    protein_details["sequence"] = sequence

        return jsonify(
            {
                "status": "success",
                "search_results": (
                    search_results[:2] if search_results else []
                ),  # Limit to first 2 results
                "protein_details": protein_details,
            }
        )

    except Exception as e:
        logger.error(f"Error testing UniProt service: {str(e)}")
        return jsonify({"error": str(e)}), 500


@main.route("/api/targets/search/uniprot/<uniprot_id>")
def search_target_by_uniprot(uniprot_id):
    """Search for a target by UniProt ID."""
    try:
        graph = get_neo4j_connection()
        if not graph:
            return (
                jsonify(
                    {"status": "error", "message": "Database connection unavailable"}
                ),
                503,
            )

        target_service = TargetService(graph)
        targets = target_service.search_targets(uniprot_id)

        if not targets:
            # If target not found in database, try to fetch from UniProt
            uniprot_service = UniProtService()
            protein_data = uniprot_service.get_protein(uniprot_id)

            if protein_data:
                # Format data for target creation
                target_data = {
                    "uniprot_id": uniprot_id,
                    "protein_name": protein_data.get("protein_name", ""),
                    "organism": protein_data.get("organism", ""),
                    "function": protein_data.get("function", ""),
                    "ec_numbers": protein_data.get("ec_numbers", []),
                    "pathways": protein_data.get("pathways", []),
                    "diseases": protein_data.get("diseases", []),
                }

                # Create the target
                target = target_service.create_target(target_data)
                if target:
                    targets = [target]

        if not targets:
            return jsonify({"status": "error", "message": "Target not found"}), 404

        return jsonify({"status": "success", "targets": targets})

    except Exception as e:
        logger.error(f"Error searching target by UniProt ID: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@main.route("/api/targets/add", methods=["POST"])
@handle_db_error
def add_target():
    """Add a new target to the database."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        graph = get_neo4j_connection()
        if not graph:
            return (
                jsonify(
                    {"status": "error", "message": "Database connection unavailable"}
                ),
                503,
            )

        target_service = TargetService(graph)
        target = target_service.create_target(data)

        if not target:
            return (
                jsonify({"status": "error", "message": "Failed to create target"}),
                500,
            )

        # Check for DrugBank associations if we have a UniProt ID
        if "uniprot_id" in data:
            drugbank_ids = target_service.check_drugbank_associations(
                data["uniprot_id"]
            )
            if drugbank_ids:
                target_service.create_target_associations(target["id"], drugbank_ids)
                target["drugbank_associations"] = drugbank_ids

        return jsonify({"status": "success", "target": target})

    except Exception as e:
        logger.error(f"Error adding target: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@main.route("/api/health")
def health_check():
    """Check the health status of the application and its services."""
    try:
        # Check if molecule service has DrugBank service initialized
        drugbank_available = (
            molecule_service and molecule_service.drugbank_service is not None
        )

        status = {
            "status": "healthy" if graph and molecule_service else "degraded",
            "database": "connected" if graph else "disconnected",
            "services": {
                "molecule_service": "available" if molecule_service else "unavailable",
                "pubchem_api": "available" if pubchem_api else "unavailable",
                "chembl_service": "available" if chembl_service else "unavailable",
                "target_service": "available" if target_service else "unavailable",
                "drugbank_service": (
                    "available" if drugbank_available else "unavailable"
                ),
            },
            "timestamp": datetime.now().isoformat(),
        }

        # Try to execute a simple query to verify database connection
        if graph:
            try:
                graph.run("MATCH (n) RETURN count(n) as count LIMIT 1")
                status["database_query"] = "success"
            except Exception as e:
                status["database_query"] = "failed"
                status["database_error"] = str(e)
                status["status"] = "degraded"

        # Add DrugBank API key status
        status["services"]["drugbank_api_key"] = (
            "configured" if current_app.config.get("DRUGBANK_API_KEY") else "missing"
        )

        return jsonify(status), 200 if status["status"] == "healthy" else 503
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        return (
            jsonify(
                {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@main.route("/api/relationships", methods=["GET"])
@cors_enabled
def get_relationships():
    """Get all relationships between molecules, targets, and organisms."""
    try:
        cypher_query = """
        MATCH (n)-[r]-(m)
        WHERE (n:Molecule OR n:Target OR n:Organism)
        AND (m:Molecule OR m:Target OR m:Organism)
        RETURN {
            source_id: toString(elementId(n)),
            source_name: n.name,
            source_type: labels(n)[0],
            target_id: toString(elementId(m)),
            target_name: m.name,
            target_type: labels(m)[0],
            relationship_type: type(r),
            activity_type: r.activity_type,
            activity_value: r.activity_value,
            activity_unit: r.activity_unit,
            confidence_score: r.confidence_score
        } as relationship
        """

        result = graph.run(cypher_query).data()
        relationships = [record["relationship"] for record in result]
        return jsonify({"status": "success", "relationships": relationships})
    except Exception as e:
        logger.error(f"Error getting relationships: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@main.route("/api/relationships", methods=["POST"])
@cors_enabled
def create_relationship():
    """Create a new relationship between nodes."""
    try:
        data = request.get_json()
        required_fields = ["source_id", "target_id", "relationship_type"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        # Validate relationship type
        valid_types = ["INTERACTS_WITH", "CONTAINS", "FOUND_IN"]
        relationship_type = data["relationship_type"]
        if relationship_type not in valid_types:
            return (
                jsonify(
                    {
                        "error": f"Invalid relationship type. Must be one of: {valid_types}"
                    }
                ),
                400,
            )

        # Validate activity type if provided
        if relationship_type == "INTERACTS_WITH" and "activity_type" in data:
            valid_activities = [
                "agonist",
                "antagonist",
                "partial_agonist",
                "inverse_agonist",
                "inhibitor",
                "activator",
                "unknown",
            ]
            if data["activity_type"] not in valid_activities:
                return (
                    jsonify(
                        {
                            "error": f"Invalid activity type. Must be one of: {valid_activities}"
                        }
                    ),
                    400,
                )

        # Parse activity value and unit if provided
        activity_value = None
        activity_unit = None
        if "activity_value" in data and data["activity_value"]:
            try:
                # Extract value and unit from string like "Ki = 302.8 nM"
                value_str = data["activity_value"]
                if "=" in value_str:
                    value_str = value_str.split("=")[1].strip()
                parts = value_str.split()
                if len(parts) >= 1:
                    activity_value = float(parts[0])
                if len(parts) >= 2:
                    activity_unit = parts[1]
            except (ValueError, IndexError) as e:
                return (
                    jsonify({"error": f"Invalid activity value format: {str(e)}"}),
                    400,
                )

        # Create the relationship based on type
        if relationship_type == "INTERACTS_WITH":
            cypher_query = """
            MATCH (source), (target)
            WHERE toString(elementId(source)) = $source_id 
            AND toString(elementId(target)) = $target_id
            CREATE (source)-[r:INTERACTS_WITH {
                activity_type: $activity_type,
                activity_value: $activity_value,
                activity_unit: $activity_unit,
                confidence_score: $confidence_score,
                created_at: datetime()
            }]->(target)
            RETURN {
                id: toString(elementId(target)),
                name: target.name,
                target_name: target.name,
                relationship_type: type(r),
                activity_type: r.activity_type,
                activity_value: r.activity_value,
                activity_unit: r.activity_unit,
                confidence_score: r.confidence_score
            } as relationship
            """
        else:
            cypher_query = """
            MATCH (source), (target)
            WHERE toString(elementId(source)) = $source_id 
            AND toString(elementId(target)) = $target_id
            CREATE (source)-[r:$relationship_type {
                confidence_score: $confidence_score,
                created_at: datetime()
            }]->(target)
            RETURN {
                id: toString(elementId(target)),
                name: target.name,
                target_name: target.name,
                relationship_type: type(r),
                confidence_score: r.confidence_score
            } as relationship
            """

        result = graph.run(
            cypher_query,
            source_id=data["source_id"],
            target_id=data["target_id"],
            relationship_type=relationship_type,
            activity_type=data.get("activity_type", "unknown"),
            activity_value=activity_value,
            activity_unit=activity_unit,
            confidence_score=data.get("confidence_score", 0.5),
        ).data()

        if not result:
            return jsonify({"error": "Failed to create relationship"}), 500

        return (
            jsonify({"status": "success", "relationship": result[0]["relationship"]}),
            201,
        )

    except Exception as e:
        logger.error(f"Error creating relationship: {str(e)}")
        return jsonify({"error": str(e)}), 500


@main.route("/api/relationships/<source_id>/<target_id>", methods=["DELETE"])
@cors_enabled
def delete_relationship(source_id, target_id):
    """Delete a relationship between two nodes."""
    try:
        if not source_id or not target_id or target_id == "undefined":
            return jsonify({"error": "Invalid source or target ID"}), 400

        cypher_query = """
        MATCH (source)-[r]-(target)
        WHERE toString(elementId(source)) = $source_id 
        AND toString(elementId(target)) = $target_id
        DELETE r
        RETURN count(r) as deleted_count
        """

        result = graph.run(
            cypher_query, source_id=source_id, target_id=target_id
        ).data()

        if not result or result[0]["deleted_count"] == 0:
            return jsonify({"error": "Relationship not found"}), 404

        return "", 204

    except Exception as e:
        logger.error(f"Error deleting relationship: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@main.route("/api/relationships/<source_id>/<target_id>", methods=["PUT"])
@cors_enabled
def update_relationship(source_id, target_id):
    """Update a relationship's properties."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate activity type if provided
        if "activity_type" in data:
            valid_activities = [
                "agonist",
                "antagonist",
                "partial_agonist",
                "inverse_agonist",
                "inhibitor",
                "activator",
                "unknown",
            ]
            if data["activity_type"] not in valid_activities:
                return (
                    jsonify(
                        {
                            "error": f"Invalid activity type. Must be one of: {valid_activities}"
                        }
                    ),
                    400,
                )

        # Update the relationship properties
        cypher_query = """
        MATCH (source)-[r]-(target)
        WHERE toString(elementId(source)) = $source_id 
        AND toString(elementId(target)) = $target_id
        SET r += $properties,
            r.updated_at = datetime()
        RETURN {
            source_id: toString(elementId(source)),
            source_name: source.name,
            source_type: labels(source)[0],
            target_id: toString(elementId(target)),
            target_name: target.name,
            target_type: labels(target)[0],
            relationship_type: type(r),
            activity_type: r.activity_type,
            activity_value: r.activity_value,
            activity_unit: r.activity_unit,
            confidence_score: r.confidence_score
        } as relationship
        """

        properties = {
            "activity_type": data.get("activity_type"),
            "activity_value": data.get("activity_value"),
            "activity_unit": data.get("activity_unit"),
            "confidence_score": data.get("confidence_score"),
        }

        result = graph.run(
            cypher_query,
            source_id=source_id,
            target_id=target_id,
            properties={k: v for k, v in properties.items() if v is not None},
        ).data()

        if not result:
            return jsonify({"error": "Relationship not found"}), 404

        return jsonify({"status": "success", "relationship": result[0]["relationship"]})

    except Exception as e:
        logger.error(f"Error updating relationship: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
