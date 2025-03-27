# hyperblend/app/web/routes/api.py

from flask import Blueprint, jsonify, request, g, send_file, Response
from hyperblend.database import get_graph
import logging
import json
from flask_cors import CORS
from functools import wraps
from hyperblend.app.web.core.decorators import (
    handle_db_error,
    requires_admin,
    cors_enabled,
)
from hyperblend.app.web.utils import get_molecule_repository, get_target_repository
from hyperblend.utils.job_queue import queue_job, get_job_status, get_job_history
from io import BytesIO
import base64
from rdkit import Chem
from rdkit.Chem import Draw

api = Blueprint("api", __name__)

logger = logging.getLogger(__name__)

# CORS configuration
cors = CORS()


# Middleware functions
def cors_enabled(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        response = f(*args, **kwargs)
        if request.method == "OPTIONS":
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    return wrapper


def handle_db_error(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            return jsonify({"error": "Database error", "details": str(e)}), 503

    return wrapper


def requires_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Implementation of admin check
        # This is a placeholder and should be replaced with actual implementation
        if not hasattr(g, "is_admin") or not g.is_admin:
            return jsonify({"error": "Access denied"}), 403
        return f(*args, **kwargs)

    return wrapper


@api.route("/api/molecules", methods=["GET"])
def list_molecules():
    """Get all molecules or search for molecules."""
    try:
        query = request.args.get("q", "").strip()

        # Debug logging for troubleshooting
        logger.debug(f"Processing /api/molecules request with query: '{query}'")

        # Use the molecule_repository from Flask g object (set in app before_request)
        if hasattr(g, "molecule_repository"):
            logger.debug("Using molecule_repository for request")
            try:
                if query:
                    logger.debug(f"Searching molecules by name: {query}")
                    molecules = g.molecule_repository.find_by_name(
                        query, exact_match=False
                    )
                else:
                    logger.debug("Fetching all molecules")
                    molecules = g.molecule_repository.find_all(limit=100)

                logger.debug(f"Found {len(molecules)} molecules")

                # Format the response
                formatted_molecules = []
                for molecule in molecules:
                    formatted_molecule = {
                        "id": molecule.get("id"),
                        "name": molecule.get("name", "Unnamed"),
                        "formula": molecule.get("formula"),
                        "molecular_weight": molecule.get("molecular_weight"),
                        "smiles": molecule.get("smiles"),
                        "description": molecule.get("description"),
                    }
                    formatted_molecules.append(formatted_molecule)

                return jsonify(formatted_molecules)
            except Exception as e:
                logger.error(f"Error using molecule_repository: {str(e)}")
                # Fall through to direct query approach

        # Fallback to direct database query if repository is not available
        logger.debug("Falling back to direct database query")
        try:
            db = get_graph()
            if not db:
                logger.error("Could not get database connection")
                return jsonify({"error": "Database connection error"}), 503

            search_pattern = f"(?i).*{query}.*" if query else None

            cypher_query = """
            MATCH (m:Molecule)
            WHERE m.name IS NOT NULL
            AND ($query = '' OR m.name =~ $search_pattern)
            RETURN {
                id: toString(elementId(m)),
                name: m.name,
                formula: m.formula,
                molecular_weight: m.molecular_weight,
                smiles: m.smiles,
                description: m.description
            } as molecule
            ORDER BY molecule.name
            LIMIT 100
            """

            results = db.run(
                cypher_query, query=query or "", search_pattern=search_pattern
            )
            molecules = [dict(record["molecule"]) for record in results]
            return jsonify(molecules)
        except Exception as e:
            logger.error(f"Error in direct database query: {str(e)}")
            return jsonify({"error": f"Database error: {str(e)}"}), 503
    except Exception as e:
        import traceback

        logger.error(f"Unexpected error in list_molecules: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error", "details": str(e)}), 503


@api.route("/api/molecules/<molecule_id>", methods=["GET"])
@cors_enabled
@handle_db_error
def get_molecule(molecule_id):
    """
    Get molecule details by ID.

    Args:
        molecule_id: The ID of the molecule

    Returns:
        JSON with molecule details
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Fetching molecule details for ID: {molecule_id}")

    try:
        # Get molecule repository
        molecule_repository = get_molecule_repository()

        # Fetch the molecule using the repository
        molecule = molecule_repository.find_by_id(molecule_id)

        if not molecule:
            logger.warning(f"Molecule with ID {molecule_id} not found")
            return jsonify({"error": "Molecule not found"}), 404

        # Get molecule targets
        targets = molecule_repository.get_molecule_targets(molecule_id)

        # Include targets in response if available
        if targets:
            molecule["targets"] = targets

        logger.info(
            f"Successfully retrieved molecule: {molecule.get('name', 'Unknown')}"
        )
        return jsonify(molecule)
    except Exception as e:
        logger.error(f"Error retrieving molecule: {str(e)}")
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@api.route("/api/targets", methods=["GET"])
def list_targets():
    """Get all targets or search for targets."""
    try:
        db = get_graph()
        query = request.args.get("q", "").strip()
        search_pattern = f"(?i).*{query}.*" if query else None

        cypher_query = """
        MATCH (t:Target)
        WHERE t.name IS NOT NULL
        AND ($query = '' OR t.name =~ $search_pattern)
        OPTIONAL MATCH (t)-[r]-(m:Molecule)
        WITH t, count(DISTINCT m) as molecule_count
        RETURN {
            id: toString(elementId(t)),
            name: t.name,
            description: t.description,
            molecule_count: molecule_count
        } as target
        ORDER BY target.name
        """

        results = db.run(cypher_query, query=query or "", search_pattern=search_pattern)
        targets = [dict(record["target"]) for record in results]
        return jsonify(targets)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/api/targets/<target_id>", methods=["GET"])
def get_target(target_id):
    """Get a specific target by ID."""
    try:
        db = get_graph()
        cypher_query = """
        MATCH (t:Target)
        WHERE toString(elementId(t)) = $target_id
        OPTIONAL MATCH (t)-[r]-(m:Molecule)
        WITH t, collect(DISTINCT {
            id: toString(elementId(m)),
            name: m.name,
            smiles: m.smiles,
            relationship_type: type(r),
            activity_type: r.activity_type,
            activity_value: r.activity_value,
            activity_unit: r.activity_unit,
            confidence_score: r.confidence_score
        }) as molecules
        RETURN {
            id: toString(elementId(t)),
            name: t.name,
            description: t.description,
            type: t.type,
            organism: t.organism,
            external_id: t.external_id,
            molecule_count: size(molecules),
            molecules: molecules
        } as target
        """

        result = db.run(cypher_query, target_id=target_id).data()
        if not result:
            return jsonify({"error": "Target not found"}), 404

        return jsonify(result[0]["target"])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/api/organisms", methods=["GET"])
def list_organisms():
    """Get all organisms or search for organisms."""
    try:
        db = get_graph()
        query = request.args.get("q", "").strip()
        search_pattern = f"(?i).*{query}.*" if query else None

        cypher_query = """
        MATCH (o:Organism)
        WHERE o.name IS NOT NULL
        AND ($query = '' OR o.name =~ $search_pattern)
        OPTIONAL MATCH (o)-[r]-(m:Molecule)
        WITH o, count(DISTINCT m) as molecule_count
        RETURN {
            id: toString(elementId(o)),
            name: o.name,
            description: o.description,
            molecule_count: molecule_count
        } as organism
        ORDER BY organism.name
        """

        results = db.run(cypher_query, query=query or "", search_pattern=search_pattern)
        organisms = [dict(record["organism"]) for record in results]
        return jsonify(organisms)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/api/organisms/<organism_id>", methods=["GET"])
def get_organism(organism_id):
    """Get a specific organism by ID."""
    try:
        db = get_graph()
        cypher_query = """
        MATCH (o:Organism)
        WHERE toString(elementId(o)) = $organism_id
        OPTIONAL MATCH (o)-[r]-(m:Molecule)
        WITH o, collect(DISTINCT {
            id: toString(elementId(m)),
            name: m.name,
            smiles: m.smiles,
            relationship_type: type(r)
        }) as molecules
        RETURN {
            id: toString(elementId(o)),
            name: o.name,
            description: o.description,
            taxonomy: o.taxonomy,
            common_name: o.common_name,
            external_id: o.external_id,
            molecule_count: size(molecules),
            molecules: molecules
        } as organism
        """

        result = db.run(cypher_query, organism_id=organism_id).data()
        if not result:
            return jsonify({"error": "Organism not found"}), 404

        return jsonify(result[0]["organism"])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/api/effects", methods=["GET"])
def list_effects():
    """Get all effects or search for effects."""
    try:
        db = get_graph()
        query = request.args.get("q", "").strip()
        search_pattern = f"(?i).*{query}.*" if query else None

        cypher_query = """
        MATCH (e:Effect)
        WHERE e.name IS NOT NULL
        AND ($query = '' OR e.name =~ $search_pattern)
        OPTIONAL MATCH (e)-[r]-(m:Molecule)
        WITH e, count(DISTINCT m) as molecule_count
        RETURN {
            id: toString(elementId(e)),
            name: e.name,
            description: e.description,
            molecule_count: molecule_count
        } as effect
        ORDER BY effect.name
        """

        results = db.run(cypher_query, query=query or "", search_pattern=search_pattern)
        effects = [dict(record["effect"]) for record in results]
        return jsonify(effects)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/api/effects/<effect_id>", methods=["GET"])
def get_effect(effect_id):
    """Get a specific effect by ID."""
    try:
        db = get_graph()
        cypher_query = """
        MATCH (e:Effect)
        WHERE toString(elementId(e)) = $effect_id
        OPTIONAL MATCH (e)-[r]-(m:Molecule)
        WITH e, collect(DISTINCT {
            id: toString(elementId(m)),
            name: m.name,
            smiles: m.smiles,
            relationship_type: type(r)
        }) as molecules
        RETURN {
            id: toString(elementId(e)),
            name: e.name,
            description: e.description,
            molecule_count: size(molecules),
            molecules: molecules
        } as effect
        """

        result = db.run(cypher_query, effect_id=effect_id).data()
        if not result:
            return jsonify({"error": "Effect not found"}), 404

        return jsonify(result[0]["effect"])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/api/statistics", methods=["GET"])
def get_statistics():
    """Get counts of different node types."""
    try:
        db = get_graph()
        cypher_query = """
        MATCH (n)
        WHERE n:Molecule OR n:Target OR n:Organism OR n:Effect
        WITH labels(n) as labels
        UNWIND labels as label
        WITH label, count(*) as count
        WHERE label IN ['Molecule', 'Target', 'Organism', 'Effect']
        RETURN collect({label: label, count: count}) as stats
        """

        result = db.run(cypher_query).data()[0]
        stats = {item["label"].lower(): item["count"] for item in result["stats"]}
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/api/molecules/create_or_update", methods=["POST"])
def create_or_update_molecule():
    """Create a new molecule or update an existing one based on identifiers."""
    try:
        # Log request details for debugging
        logger.info(
            f"Request received: Method={request.method}, Content-Type={request.content_type}"
        )
        logger.info(f"Request data: {request.data}")

        # Try different ways to get JSON data
        if request.is_json:
            data = request.get_json()
            logger.info(f"Data from get_json(): {data}")
        else:
            logger.warning("Request is not JSON")
            try:
                # Try to parse data manually
                data = (
                    json.loads(request.data.decode("utf-8")) if request.data else None
                )
                logger.info(f"Data from manual parsing: {data}")
            except Exception as e:
                logger.error(f"Error parsing request data: {str(e)}")
                data = None

            # Check form data as fallback
            if not data and request.form:
                data = {k: v for k, v in request.form.items()}
                logger.info(f"Data from form: {data}")

        if not data:
            logger.error("No data provided in request")
            return jsonify({"error": "No data provided"}), 400

        # Log the request
        logger.info(f"Create or update molecule request received with data: {data}")

        # Use MoleculeRepository if available
        if hasattr(g, "molecule_repository"):
            try:
                logger.debug("Using molecule_repository")
                repository = g.molecule_repository

                # Check if we have at least one valid identifier
                valid_identifiers = {
                    "name",
                    "cas_number",
                    "pubchem_cid",
                    "inchikey",
                    "smiles",
                    "chembl_id",
                    "formula",
                }
                provided_identifiers = {
                    k: v for k, v in data.items() if k in valid_identifiers and v
                }

                logger.info(f"Provided identifiers: {provided_identifiers}")

                if not provided_identifiers:
                    return (
                        jsonify(
                            {"error": "At least one valid identifier must be provided"}
                        ),
                        400,
                    )

                # Try to find existing molecule first
                existing_molecule = None

                # Check by most reliable identifiers first
                for id_type in ["inchikey", "pubchem_cid", "cas_number", "chembl_id"]:
                    try:
                        if id_type in provided_identifiers:
                            logger.debug(
                                f"Searching by {id_type}: {provided_identifiers[id_type]}"
                            )
                            if id_type == "inchikey":
                                # Use specific method for inchikey
                                molecule = repository.find_by_inchikey(
                                    provided_identifiers[id_type]
                                )
                                molecules = [molecule] if molecule else []
                            else:
                                # Use generic method for other properties
                                molecules = repository.find_by_property(
                                    id_type, provided_identifiers[id_type]
                                )
                            logger.debug(f"Search result: {molecules}")
                            if molecules and len(molecules) > 0 and molecules[0]:
                                existing_molecule = molecules[0]
                                logger.info(
                                    f"Found existing molecule by {id_type}: {existing_molecule.get('name', 'Unknown')}"
                                )
                                break
                    except Exception as e:
                        logger.warning(f"Error searching by {id_type}: {str(e)}")
                        logger.exception(e)

                # Create or update
                created = False
                try:
                    if existing_molecule:
                        # Update existing molecule
                        molecule_id = existing_molecule.get("id")
                        if not molecule_id:
                            logger.warning(
                                "Existing molecule missing ID, generating a new ID"
                            )
                            # Generate a standardized ID for this molecule
                            from hyperblend.utils.db_utils import DatabaseUtils

                            new_id = DatabaseUtils(
                                repository.graph
                            ).get_next_available_id("Molecule")

                            # Update the molecule with the new ID
                            logger.info(
                                f"Assigning new ID {new_id} to existing molecule"
                            )

                            # Try to find the molecule by the properties we know it has
                            query_props = {}
                            for key in [
                                "pubchem_cid",
                                "inchikey",
                                "smiles",
                                "chembl_id",
                                "cas_number",
                            ]:
                                if key in existing_molecule and existing_molecule[key]:
                                    query_props[key] = existing_molecule[key]
                                    break

                            if not query_props:
                                logger.error(
                                    "Cannot find a unique property to identify the molecule"
                                )
                                return (
                                    jsonify(
                                        {
                                            "error": "Cannot update molecule without a unique identifier"
                                        }
                                    ),
                                    400,
                                )

                            # Get the first query property
                            prop_name = list(query_props.keys())[0]
                            prop_value = query_props[prop_name]

                            # Update the molecule with the new ID
                            update_query = f"""
                            MATCH (m:Molecule)
                            WHERE m.{prop_name} = $prop_value
                            SET m.id = $new_id
                            RETURN m
                            """

                            try:
                                repository.db_utils.run_query(
                                    update_query,
                                    {"prop_value": prop_value, "new_id": new_id},
                                )

                                # Set the ID for further processing
                                existing_molecule["id"] = new_id
                                molecule_id = new_id
                                logger.info(
                                    f"Successfully assigned ID {new_id} to molecule"
                                )
                            except Exception as e:
                                logger.error(f"Failed to assign new ID: {str(e)}")
                                return (
                                    jsonify(
                                        {
                                            "error": f"Failed to update molecule: {str(e)}"
                                        }
                                    ),
                                    500,
                                )

                        logger.info(
                            f"Updating existing molecule with ID: {molecule_id}"
                        )

                        # Merge existing data with new data, prioritizing new data
                        update_data = {**existing_molecule, **data}

                        # Remove ID from update data
                        if "id" in update_data:
                            del update_data["id"]

                        # Update molecule
                        logger.debug(
                            f"Calling update_molecule with ID {molecule_id} and data: {update_data}"
                        )
                        molecule = repository.update_molecule(
                            molecule_id, update_data, source="API"
                        )
                        created = False
                    else:
                        # Create new molecule
                        logger.info("Creating new molecule")

                        # Ensure molecule has a name
                        if "name" not in data or not data["name"]:
                            if "inchikey" in data:
                                data["name"] = f"Molecule {data['inchikey']}"
                            elif "smiles" in data:
                                data["name"] = f"Molecule {data['smiles'][:15]}..."
                            else:
                                data["name"] = (
                                    f"New Molecule {data.get('pubchem_cid', '')}"
                                )

                        # Create molecule
                        logger.debug(f"Calling create_molecule with data: {data}")
                        molecule = repository.create_molecule(data, source="API")
                        created = True

                    if not molecule:
                        logger.error("Failed to create/update molecule")
                        return (
                            jsonify({"error": "Failed to create/update molecule"}),
                            500,
                        )

                    # Return response
                    logger.info(
                        f"Successfully {'created' if created else 'updated'} molecule: {molecule.get('name', 'Unknown')}"
                    )
                    return jsonify(
                        {
                            "id": molecule.get("id", ""),
                            "name": molecule.get("name", "Unknown"),
                            "created": created,
                            "updated": not created,
                            "molecule": molecule,
                        }
                    )

                except Exception as e:
                    logger.error(f"Error in create/update operation: {str(e)}")
                    logger.exception(e)
                    return (
                        jsonify(
                            {"error": f"Failed to create/update molecule: {str(e)}"}
                        ),
                        500,
                    )
            except Exception as e:
                logger.error(f"Error in repository operations: {str(e)}")
                logger.exception(e)
                return jsonify({"error": f"Server error: {str(e)}"}), 500
        else:
            # Fallback to using MoleculeService directly
            try:
                graph = get_graph()
                if not graph:
                    return jsonify({"error": "Database connection error"}), 503

                from hyperblend.services.internal.molecule_service import (
                    MoleculeService,
                )

                logger.info(f"Searching for existing molecule with identifiers: {data}")
                molecule_service = MoleculeService(graph)

                # Forward the request to the molecule service
                if "inchikey" in data and data["inchikey"]:
                    # Try to find by InChIKey first
                    existing = molecule_service.find_by_inchikey(data["inchikey"])
                    if existing:
                        # Update existing
                        updated = molecule_service.update_molecule(
                            existing["id"], data, "API"
                        )
                        return jsonify(
                            {
                                "id": updated.get("id"),
                                "name": updated.get("name"),
                                "created": False,
                                "updated": True,
                                "molecule": updated,
                            }
                        )
                # If no existing molecule found by inchikey, check by name
                elif "name" in data and data["name"]:
                    # Try to find by name
                    existing_list = molecule_service.find_by_name(
                        data["name"], exact=True
                    )
                    if existing_list and len(existing_list) > 0:
                        existing = existing_list[0]
                        # Update existing
                        updated = molecule_service.update_molecule(
                            existing["id"], data, "API"
                        )
                        return jsonify(
                            {
                                "id": updated.get("id"),
                                "name": updated.get("name"),
                                "created": False,
                                "updated": True,
                                "molecule": updated,
                            }
                        )

                # Create new
                created = molecule_service.create_molecule(data, "API")
                return jsonify(
                    {
                        "id": created.get("id"),
                        "name": created.get("name"),
                        "created": True,
                        "updated": False,
                        "molecule": created,
                    }
                )
            except Exception as e:
                logger.error(f"Error in MoleculeService fallback: {str(e)}")
                logger.exception(e)
                return jsonify({"error": f"Service error: {str(e)}"}), 500
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in create_or_update_molecule: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@api.route("/api/molecules/merge_duplicates", methods=["POST", "OPTIONS"])
@cors_enabled
@handle_db_error
@requires_admin
def merge_duplicate_molecules():
    """
    Merge duplicate molecules based on common identifiers.

    This endpoint triggers a process to find and merge molecules with the same
    identifiers (pubchem_cid, chembl_id, cas_number, inchikey). Molecules are
    merged into a single entity, with data combined to create the most complete
    record.

    Only admins can access this endpoint.
    """
    try:
        # Get the molecule repository
        repository = get_molecule_repository()
        if not repository:
            return jsonify({"error": "Database connection error"}), 503

        # Queue the merge process as a background job
        logger.info("Queueing molecule duplicate merging process")
        job_info = queue_job(
            job_type="merge_molecules", function=repository.merge_duplicate_molecules
        )

        # Return the job information
        return jsonify(
            {
                "success": True,
                "message": "Duplicate molecule merging job has been queued",
                "job_id": job_info["id"],
                "status": job_info["status"],
            }
        )
    except Exception as e:
        logger.error(f"Error in merge_duplicate_molecules: {str(e)}")
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@api.route("/api/molecules/enrich/<string:molecule_id>", methods=["POST", "OPTIONS"])
@cors_enabled
@handle_db_error
def enrich_molecule(molecule_id):
    """
    Enrich a specific molecule with data from external databases.

    Args:
        molecule_id: ID of the molecule to enrich
    """
    try:
        # Get the molecule repository
        repository = get_molecule_repository()
        if not repository:
            return jsonify({"error": "Database connection error"}), 503

        # Find the molecule
        molecule = repository.find_by_id(molecule_id)
        if not molecule:
            return jsonify({"error": f"Molecule not found with ID: {molecule_id}"}), 404

        # Queue the enrichment process as a background job
        logger.info(f"Queueing enrichment process for molecule {molecule_id}")
        job_info = queue_job(
            job_type="enrich_molecule",
            function=repository.enrich_molecule_data,
            molecule=molecule,
        )

        # Return the job information
        return jsonify(
            {
                "success": True,
                "message": f"Molecule enrichment job has been queued for {molecule_id}",
                "job_id": job_info["id"],
                "status": job_info["status"],
                "molecule_id": molecule_id,
            }
        )
    except Exception as e:
        logger.error(f"Error enriching molecule {molecule_id}: {str(e)}")
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@api.route("/api/jobs/<string:job_id>", methods=["GET"])
@cors_enabled
def get_job(job_id):
    """
    Get the status of a background job.

    Args:
        job_id: ID of the job to check
    """
    try:
        job_info = get_job_status(job_id)
        if not job_info:
            return jsonify({"error": f"Job not found with ID: {job_id}"}), 404

        return jsonify({"success": True, "job": job_info})
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@api.route("/api/jobs", methods=["GET"])
@cors_enabled
@requires_admin
def list_jobs():
    """List all background jobs."""
    try:
        job_history = get_job_history()
        return jsonify({"success": True, "jobs": job_history})
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@api.route("/molecules/<molecule_id>/structure", methods=["GET"])
def get_molecule_structure(molecule_id):
    """Generate and return a molecular structure image based on SMILES"""
    try:
        # Get the molecule repository
        molecule_repo = get_molecule_repository()

        # Fetch the molecule by ID
        molecule = molecule_repo.find_by_id(molecule_id)
        if not molecule:
            return jsonify({"error": "Molecule not found"}), 404

        # Check if molecule has SMILES data
        smiles = molecule.get("smiles")
        if not smiles:
            return jsonify({"error": "No SMILES data available for this molecule"}), 400

        # Generate molecule image using RDKit
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return jsonify({"error": "Could not parse SMILES data"}), 400

        # Set image size and options
        img = Draw.MolToImage(mol, size=(400, 300), kekulize=True, wedgeBonds=True)

        # Convert image to bytes
        img_io = BytesIO()
        img.save(img_io, "PNG")
        img_io.seek(0)

        # Return image as response
        return send_file(img_io, mimetype="image/png")

    except Exception as e:
        logger.error(f"Error generating molecule structure: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@api.route("/molecules/<molecule_id>/structure_base64", methods=["GET"])
def get_molecule_structure_base64(molecule_id):
    """Generate and return a molecular structure image as base64 encoded string"""
    try:
        # Get the molecule repository
        molecule_repo = get_molecule_repository()

        # Fetch the molecule by ID
        molecule = molecule_repo.find_by_id(molecule_id)
        if not molecule:
            return jsonify({"error": "Molecule not found"}), 404

        # Check if molecule has SMILES data
        smiles = molecule.get("smiles")
        if not smiles:
            return jsonify({"error": "No SMILES data available for this molecule"}), 400

        # Generate molecule image using RDKit
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return jsonify({"error": "Could not parse SMILES data"}), 400

        # Set image size and options
        img = Draw.MolToImage(mol, size=(400, 300), kekulize=True, wedgeBonds=True)

        # Convert image to base64
        img_io = BytesIO()
        img.save(img_io, "PNG")
        img_io.seek(0)
        img_base64 = base64.b64encode(img_io.getvalue()).decode("utf-8")

        # Return base64 string
        return jsonify(
            {
                "image": f"data:image/png;base64,{img_base64}",
                "molecule_id": molecule_id,
                "smiles": smiles,
            }
        )

    except Exception as e:
        logger.error(
            f"Error generating molecule structure as base64: {str(e)}", exc_info=True
        )
        return jsonify({"error": str(e)}), 500
