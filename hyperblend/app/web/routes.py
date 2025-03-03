# hyperblend/app/web/routes.py

from flask import (
    Blueprint,
    render_template,
    jsonify,
    request,
    make_response,
    send_from_directory,
    current_app,
)
from functools import wraps
from hyperblend.services.compound_service import CompoundService
from hyperblend.models.domain import Compound
from ..utils.external_apis import PubChemAPI
import os
import logging

# Create blueprint
main = Blueprint("main", __name__)
compound_service = CompoundService()
pubchem_api = PubChemAPI()
logger = logging.getLogger(__name__)


def add_cors_headers(response):
    """Add CORS headers to the response."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def cors_enabled(f):
    """Decorator to enable CORS for routes."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == "OPTIONS":
            response = make_response()
            add_cors_headers(response)
            return response

        response = make_response(f(*args, **kwargs))
        add_cors_headers(response)
        return response

    return decorated_function


@main.route("/")
def index():
    """Render the main page."""
    try:
        return render_template("index.html")
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

        # Verify database connection
        if not compound_service.db.driver:
            logger.error("Database connection not established")
            return jsonify({"error": "Database connection not established"}), 500

        # Get nodes with labels
        with compound_service.db.driver.session() as session:
            cypher_query = """
            MATCH (n)
            WHERE n.name IS NOT NULL
            AND (CASE WHEN $search_query <> ''
                 THEN toLower(n.name) CONTAINS toLower($search_query)
                 ELSE true END)
            AND (n:Compound OR n:Source OR n:Target)
            WITH n
            OPTIONAL MATCH (n)-[r]-(m)
            WHERE m.name IS NOT NULL
            AND (m:Compound OR m:Source OR m:Target)
            WITH n, collect(DISTINCT m) as neighbors
            RETURN DISTINCT elementId(n) as id, 
                   n.name as name,
                   labels(n)[0] as type,
                   n.smiles as smiles,
                   n.description as description,
                   size(neighbors) as degree
            ORDER BY degree DESC
            LIMIT 100
            """
            result = session.run(cypher_query, search_query=search_query)
            nodes = []
            node_map = {}  # Map to store nodes by ID
            for record in result:
                try:
                    node = {
                        "id": record["id"],
                        "name": record["name"],
                        "type": record["type"],
                        "smiles": record.get("smiles"),
                        "description": record.get("description"),
                        "width": 30,  # Node size for WebCola
                        "height": 30,
                        "fixed": False,  # Whether node position is fixed
                        "x": 0,  # Initial position
                        "y": 0,
                    }
                    nodes.append(node)
                    node_map[record["id"]] = node
                except Exception as e:
                    logger.error(
                        f"Error processing node record: {str(e)}", exc_info=True
                    )
                    continue

            logger.info(f"Successfully fetched {len(nodes)} nodes")
            if not nodes:
                logger.warning("No nodes found in the database")
                return jsonify(
                    {"nodes": [], "links": [], "constraints": [], "groups": []}
                )

        try:
            # Get relationships between nodes we have
            with compound_service.db.driver.session() as session:
                cypher_query = """
                MATCH (source)-[r]-(target)
                WHERE source.name IS NOT NULL 
                AND target.name IS NOT NULL
                AND elementId(source) IN $node_ids
                AND elementId(target) IN $node_ids
                AND (CASE WHEN $search_query <> ''
                     THEN toLower(source.name) CONTAINS toLower($search_query)
                     OR toLower(target.name) CONTAINS toLower($search_query)
                     ELSE true END)
                AND (
                    (source:Compound AND (target:Source OR target:Target)) OR
                    ((source:Source OR source:Target) AND target:Compound)
                )
                RETURN DISTINCT elementId(source) as source,
                       elementId(target) as target,
                       type(r) as type
                """
                node_ids = [node["id"] for node in nodes]  # Use elementId directly
                result = session.run(
                    cypher_query, search_query=search_query, node_ids=node_ids
                )
                relationships = []
                for record in result:
                    try:
                        source_id = record["source"]
                        target_id = record["target"]

                        # Only create relationship if both nodes exist
                        if source_id in node_map and target_id in node_map:
                            rel = {
                                "source": source_id,  # Use node IDs for WebCola
                                "target": target_id,
                                "type": record["type"],
                                "weight": 1,  # Edge weight for WebCola
                            }
                            relationships.append(rel)
                    except Exception as e:
                        logger.error(
                            f"Error processing relationship record: {str(e)}",
                            exc_info=True,
                        )
                        continue

                logger.info(f"Successfully fetched {len(relationships)} relationships")
                if not relationships:
                    logger.warning("No relationships found between the selected nodes")

        except Exception as e:
            logger.error(f"Error fetching relationships: {str(e)}", exc_info=True)
            return jsonify({"error": f"Error fetching relationships: {str(e)}"}), 500

        # Validate data format
        if not isinstance(nodes, list) or not isinstance(relationships, list):
            logger.error("Invalid data format returned from database")
            return jsonify({"error": "Invalid data format"}), 500

        response_data = {
            "nodes": nodes,
            "links": relationships,
            "constraints": [],  # WebCola constraints
            "groups": [],  # WebCola groups
        }
        logger.info(
            f"Successfully prepared graph data with {len(nodes)} nodes and {len(relationships)} relationships"
        )
        logger.debug(f"Response data: {response_data}")  # Log the actual response data

        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error in get_graph endpoint: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main.route("/compounds")
def compounds_page():
    """Render the compounds page."""
    return render_template("compounds.html")


@main.route("/sources")
def sources_page():
    """Render the sources page."""
    return render_template("sources.html")


@main.route("/targets")
def targets_page():
    """Render the targets page."""
    return render_template("targets.html")


@main.route("/api/compounds", methods=["GET"])
def get_compounds():
    """Get all compounds or search for compounds."""
    try:
        query = request.args.get("q", "")
        if query:
            compounds = compound_service.search_compounds(query)
        else:
            compounds = compound_service.get_all_compounds()
        return jsonify([compound.model_dump() for compound in compounds])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route("/api/compounds/<compound_id>", methods=["GET"])
def get_compound(compound_id):
    """Get a specific compound by ID."""
    try:
        compound = compound_service.get_compound(compound_id)
        if compound:
            return jsonify(compound.model_dump())
        return jsonify({"error": "Compound not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route("/api/compounds/<compound_id>/related", methods=["GET"])
def get_compound_related(compound_id):
    """Get related nodes for a compound."""
    try:
        related = compound_service.get_compound_related(compound_id)
        return jsonify(related)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route("/api/compounds", methods=["POST"])
def create_compound():
    """Create a new compound."""
    try:
        data = request.get_json()
        compound = Compound(**data)
        created_compound = compound_service.create_compound(compound)
        return jsonify(created_compound.model_dump()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@main.route("/api/compounds/<compound_id>", methods=["PUT"])
def update_compound(compound_id):
    """Update an existing compound."""
    try:
        data = request.get_json()
        compound = Compound(**data)
        updated_compound = compound_service.update_compound(compound_id, compound)
        if updated_compound:
            return jsonify(updated_compound.model_dump())
        return jsonify({"error": "Compound not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@main.route("/api/compounds/<compound_id>", methods=["DELETE"])
def delete_compound(compound_id):
    """Delete a compound."""
    try:
        if compound_service.delete_compound(compound_id):
            return "", 204
        return jsonify({"error": "Compound not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route("/api/compounds/cas/<cas_number>", methods=["POST"])
async def create_compound_by_cas(cas_number):
    """Create a new compound using its CAS number."""
    try:
        compound = await compound_service.create_compound_from_cas(cas_number)
        if compound:
            return jsonify(compound.model_dump()), 201
        return jsonify({"error": "Compound not found or already exists"}), 404
    except Exception as e:
        logger.error(f"Error creating compound from CAS {cas_number}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@main.route("/api/compounds/add", methods=["POST"])
async def add_compound():
    """Add a compound using a database identifier."""
    try:
        data = request.get_json()
        database = data.get("database")
        identifier = data.get("identifier")

        if not database or not identifier:
            return jsonify({"error": "Database and identifier are required"}), 400

        # Create compound based on database type
        if database == "cas":
            compound = await compound_service.create_compound_from_cas(identifier)
        elif database == "pubchem":
            compound = await compound_service.create_compound_from_pubchem(identifier)
        elif database == "chembl":
            compound = await compound_service.create_compound_from_chembl(identifier)
        elif database == "drugbank":
            compound = await compound_service.create_compound_from_drugbank(identifier)
        elif database == "chebi":
            compound = await compound_service.create_compound_from_chebi(identifier)
        else:
            return jsonify({"error": "Unsupported database"}), 400

        if compound:
            return jsonify(compound.model_dump()), 201
        return jsonify({"error": "Compound not found or already exists"}), 404
    except Exception as e:
        logger.error(
            f"Error creating compound from {database} ID {identifier}: {str(e)}"
        )
        return jsonify({"error": str(e)}), 500


@main.route("/api/compounds", methods=["GET", "POST", "OPTIONS"])
@cors_enabled
def compounds():
    """Handle compound operations."""
    if request.method == "GET":
        return get_compounds()
    elif request.method == "POST":
        return create_compound()
    return "", 204


@main.route("/api/compounds/<compound_id>", methods=["GET", "PUT", "DELETE", "OPTIONS"])
@cors_enabled
def compound(compound_id):
    """Handle operations on a specific compound."""
    if request.method == "GET":
        return get_compound(compound_id)
    elif request.method == "PUT":
        return update_compound(compound_id)
    elif request.method == "DELETE":
        return delete_compound(compound_id)
    return "", 204


@main.route("/api/compounds/<compound_id>/related", methods=["GET", "OPTIONS"])
@cors_enabled
def compound_related(compound_id):
    """Get related nodes for a compound."""
    return get_compound_related(compound_id)


@main.route("/api/statistics", methods=["GET", "OPTIONS"])
@cors_enabled
def statistics():
    """Get statistics about the database."""
    return get_statistics()


@main.after_request
def after_request(response):
    """Add CORS headers to all responses."""
    return add_cors_headers(response)


@main.route("/api/statistics")
def get_statistics():
    """Get statistics about the database."""
    try:
        with compound_service.db.driver.session() as session:
            # Count compounds
            result = session.run("MATCH (c:Compound) RETURN count(c) as count")
            compounds_count = result.single()["count"]

            # Count sources
            result = session.run("MATCH (s:Source) RETURN count(s) as count")
            sources_count = result.single()["count"]

            # Count targets
            result = session.run("MATCH (t:Target) RETURN count(t) as count")
            targets_count = result.single()["count"]

            return jsonify(
                {
                    "compounds": compounds_count,
                    "sources": sources_count,
                    "targets": targets_count,
                }
            )
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        return jsonify({"error": str(e)}), 500


@main.route("/api/compounds/search/<database>/<identifier>", methods=["GET", "OPTIONS"])
@cors_enabled
async def search_compound(database, identifier):
    """Search for a compound in external databases."""
    try:
        # Search based on database type
        if database == "cas":
            # Search PubChem using CAS number
            compound_data = await pubchem_api.get_compound_by_cas(identifier)
            if not compound_data:
                return jsonify({"error": "Compound not found"}), 404
            return jsonify(compound_data)
        elif database == "pubchem":
            # Search PubChem using CID
            compound_data = await pubchem_api.get_compound_by_cid(identifier)
            if not compound_data:
                return jsonify({"error": "Compound not found"}), 404
            return jsonify(compound_data)
        # Add other database searches here (ChEMBL, DrugBank, ChEBI)
        else:
            return jsonify({"error": "Unsupported database"}), 400
    except Exception as e:
        logger.error(
            f"Error searching compound from {database} ID {identifier}: {str(e)}"
        )
        return jsonify({"error": str(e)}), 500


@main.route("/api/db-status")
def get_db_status():
    """Get database status and statistics."""
    try:
        status = compound_service.check_database_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting database status: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500
