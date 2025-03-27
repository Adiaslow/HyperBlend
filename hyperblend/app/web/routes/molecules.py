# hyperblend/app/web/routes/molecules.py

from flask import Blueprint, jsonify, request
from hyperblend.app.web.core.decorators import (
    handle_db_error,
    cors_enabled,
    validate_json,
    requires_admin,
)
from hyperblend.app.web.core.exceptions import ResourceNotFoundError
from hyperblend.services.internal.molecule_service import MoleculeService
from hyperblend.models.molecule import Molecule
from hyperblend.database import get_graph
import logging
import random
from flask import current_app
from hyperblend.utils.db_utils import DatabaseUtils

molecules = Blueprint("molecules", __name__)


@molecules.route("/api/molecules", methods=["GET"])
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
    query = request.args.get("q", "").strip()

    try:
        if query:
            molecules = molecule_service.search_molecules(query)
        else:
            molecules = molecule_service.get_all_molecules()
        return jsonify({"status": "success", "molecules": molecules})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 503


@molecules.route("/api/molecules/<molecule_id>", methods=["GET"])
@cors_enabled
@handle_db_error
def get_molecule(molecule_id: str):
    """
    Get a specific molecule by ID.

    Args:
        molecule_id: The ID of the molecule to retrieve

    Returns:
        JSON response with the molecule details
    """
    logger = logging.getLogger(__name__)
    try:
        graph = get_graph()
        molecule_service = MoleculeService(graph)

        # Log incoming ID for debugging
        logger.debug(f"Received request for molecule ID: {molecule_id}")

        # Get the molecule
        molecule = molecule_service.get_molecule(molecule_id)

        if not molecule:
            logger.warning(f"Molecule not found with ID: {molecule_id}")

            # If molecule ID is in MOL_PUBCHEM_XXXX format, try to find by pubchem_cid
            if molecule_id.startswith("MOL_PUBCHEM_"):
                pubchem_id = molecule_id[12:]  # Extract the ID part
                logger.info(f"Trying to find molecule by PubChem ID: {pubchem_id}")

                # Look up molecule by PubChem ID
                query = """
                MATCH (m:Molecule)
                WHERE m.pubchem_cid = $pubchem_id
                RETURN m
                """
                result = graph.run(query, pubchem_id=pubchem_id).data()

                if result and len(result) > 0:
                    # Found by PubChem ID, format and return
                    molecule = molecule_service._format_molecule(result[0]["m"], [], [])
                    logger.info(
                        f"Found molecule by PubChem ID: {molecule.get('name', 'Unknown')}"
                    )

                    # Store original ID for reference
                    if molecule and not molecule.get("original_id"):
                        molecule["original_id"] = molecule_id

                    return jsonify(molecule)

            return jsonify({"error": "Molecule not found"}), 404

        # If molecule has 'id' but not 'original_id', and it differs from requested ID,
        # add the requested ID as 'original_id'
        if (
            molecule.get("id")
            and molecule.get("id") != molecule_id
            and (
                not molecule.get("original_id")
                or molecule.get("original_id") != molecule_id
            )
        ):
            logger.debug(
                f"Adding original_id {molecule_id} to molecule with ID {molecule.get('id')}"
            )
            molecule["original_id"] = molecule_id

            # Update the molecule in the database to store this original_id
            try:
                molecule_service.update_molecule_properties(
                    molecule.get("id"), {"original_id": molecule_id}
                )
                logger.debug(f"Updated molecule with original_id {molecule_id}")
            except Exception as e:
                logger.warning(f"Could not update molecule with original_id: {str(e)}")

        logger.debug(f"Found molecule: {molecule.get('name', 'Unknown')}")
        return jsonify(molecule)

    except Exception as e:
        logger.error(f"Error retrieving molecule {molecule_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@molecules.route("/api/molecules", methods=["POST"])
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
        return jsonify({"error": str(e)}), 400


@molecules.route("/api/molecules/<molecule_id>", methods=["PUT"])
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
            raise ResourceNotFoundError("Molecule not found")
        return jsonify(updated_molecule)
    except ResourceNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@molecules.route("/api/molecules/<molecule_id>", methods=["DELETE"])
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
            return "", 204
        raise ResourceNotFoundError("Molecule not found")
    except ResourceNotFoundError as e:
        return jsonify({"error": str(e)}), 404


@molecules.route("/api/molecules/<molecule_id>/enrich", methods=["POST"])
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
            "identifiers": [
                {"type": "inchi_key", "value": "..."},
                {"type": "smiles", "value": "..."},
                {"type": "name", "value": "..."}
            ]
        }

    Returns:
        JSON response with enrichment results
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Enrichment request for molecule ID: {molecule_id}")

    try:
        # Get molecule service
        molecule_service = MoleculeService(get_graph())

        # Check if molecule exists
        molecule = molecule_service.get_molecule(molecule_id)

        # If not found and ID is numeric, try with M-x format
        if not molecule and molecule_id.isdigit():
            new_id = f"M-{molecule_id}"
            logger.info(
                f"Molecule with ID {molecule_id} not found, trying with new format: {new_id}"
            )
            molecule = molecule_service.get_molecule(new_id)
            if molecule:
                logger.info(f"Found molecule with new ID format: {new_id}")
                # Use the new ID for the rest of the processing
                molecule_id = new_id

        if not molecule:
            logger.warning(f"Molecule with ID {molecule_id} not found")
            return jsonify({"error": f"Molecule with ID {molecule_id} not found"}), 404

        # Extract request data
        data = request.get_json() or {}
        identifiers = data.get("identifiers", {})
        original_id = data.get("original_id")
        logger.info(f"Received identifiers: {identifiers}")
        if original_id:
            logger.info(f"Original ID from client: {original_id}")

        if not identifiers:
            logger.warning("No identifiers provided for enrichment")
            return jsonify({"error": "No identifiers provided for enrichment"}), 400

        try:
            # Try enrichment with PubChem
            enriched_data = None
            sources = []

            # Try each external service until we get data
            if molecule_service.pubchem_service:
                try:
                    logger.info("Attempting PubChem enrichment")
                    enriched_data = molecule_service.pubchem_service.enrich_molecule(
                        identifiers
                    )
                    if enriched_data:
                        sources.append(
                            {
                                "name": "PubChem",
                                "url": "https://pubchem.ncbi.nlm.nih.gov/",
                            }
                        )
                        logger.info("PubChem enrichment successful")
                except Exception as e:
                    logger.error(f"PubChem enrichment failed: {str(e)}")

            # Try ChEMBL if PubChem failed or returned limited data
            if molecule_service.chembl_service and (
                not enriched_data or len(enriched_data.get("properties", {})) < 3
            ):
                try:
                    logger.info("Attempting ChEMBL enrichment")
                    chembl_data = molecule_service.chembl_service.enrich_molecule(
                        identifiers
                    )
                    if chembl_data:
                        if not enriched_data:
                            enriched_data = chembl_data
                        else:
                            # Merge data, prioritizing what we already have
                            for key, value in chembl_data.get("properties", {}).items():
                                if key not in enriched_data.get("properties", {}):
                                    if "properties" not in enriched_data:
                                        enriched_data["properties"] = {}
                                    enriched_data["properties"][key] = value

                            for key, value in chembl_data.get(
                                "identifiers", {}
                            ).items():
                                if key not in enriched_data.get("identifiers", {}):
                                    if "identifiers" not in enriched_data:
                                        enriched_data["identifiers"] = {}
                                    enriched_data["identifiers"][key] = value

                        sources.append(
                            {"name": "ChEMBL", "url": "https://www.ebi.ac.uk/chembl/"}
                        )
                        logger.info("ChEMBL enrichment successful")
                except Exception as e:
                    logger.error(f"ChEMBL enrichment failed: {str(e)}")

            # If we still don't have data, try DrugBank
            if molecule_service.drugbank_service and (
                not enriched_data or len(enriched_data.get("properties", {})) < 3
            ):
                try:
                    logger.info("Attempting DrugBank enrichment")
                    drugbank_data = molecule_service.drugbank_service.enrich_molecule(
                        identifiers
                    )
                    if drugbank_data:
                        if not enriched_data:
                            enriched_data = drugbank_data
                        else:
                            # Merge data
                            for key, value in drugbank_data.get(
                                "properties", {}
                            ).items():
                                if key not in enriched_data.get("properties", {}):
                                    if "properties" not in enriched_data:
                                        enriched_data["properties"] = {}
                                    enriched_data["properties"][key] = value

                            for key, value in drugbank_data.get(
                                "identifiers", {}
                            ).items():
                                if key not in enriched_data.get("identifiers", {}):
                                    if "identifiers" not in enriched_data:
                                        enriched_data["identifiers"] = {}
                                    enriched_data["identifiers"][key] = value

                        sources.append(
                            {"name": "DrugBank", "url": "https://go.drugbank.com/"}
                        )
                        logger.info("DrugBank enrichment successful")
                except Exception as e:
                    logger.error(f"DrugBank enrichment failed: {str(e)}")

            # If no enrichment data was found from any source, use mock data
            if not enriched_data:
                logger.warning(
                    "No enrichment data found from any source, using mock data"
                )
                enriched_data = _generate_mock_enrichment_data(molecule)
                sources.append({"name": "Mock Data", "url": None})

            # Make sure we have containers for properties and identifiers
            if "properties" not in enriched_data:
                enriched_data["properties"] = {}
            if "identifiers" not in enriched_data:
                enriched_data["identifiers"] = {}

            # Add sources to the enriched data
            enriched_data["sources"] = sources

            # Get standardized ID for client-side use
            clean_id = molecule_service.standardize_id(molecule_id)
            enriched_data["identifiers"]["Internal ID"] = clean_id

            # Always include the original ID in identifiers to ensure the frontend can find it
            if original_id:
                enriched_data["identifiers"]["Original ID"] = original_id

            # Update molecule properties in database
            if enriched_data and enriched_data.get("properties"):
                logger.info(f"Updating molecule {molecule_id} with new properties")
                molecule_service.update_molecule_properties(
                    molecule_id, enriched_data["properties"]
                )
                logger.info("Database update successful")

            return jsonify(enriched_data)

        except Exception as e:
            logger.error(f"Error during enrichment process: {str(e)}")
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        logger.error(f"Unexpected error in enrich_molecule: {str(e)}")
        return jsonify({"error": str(e)}), 500


def _generate_mock_enrichment_data(molecule):
    """Generate mock enrichment data for testing when external services fail."""
    logger = current_app.logger
    logger.info("Generating mock enrichment data")

    # Extract molecule name
    name = molecule.get("name", "Unknown Compound")

    # Generate random properties
    properties = {
        "LogP": round(random.uniform(-2, 5), 2),
        "Molecular Weight": round(random.uniform(100, 500), 2),
        "Hydrogen Bond Donors": random.randint(0, 5),
        "Hydrogen Bond Acceptors": random.randint(1, 10),
        "Rotatable Bonds": random.randint(0, 12),
        "Polar Surface Area": round(random.uniform(20, 140), 2),
        "Molecular Formula": f"C{random.randint(5, 20)}H{random.randint(5, 30)}N{random.randint(0, 5)}O{random.randint(0, 5)}",
    }

    # Generate mock identifiers
    identifiers = {
        "PubChem CID": f"CID{random.randint(10000, 999999)}",
        "ChEMBL ID": f"CHEMBL{random.randint(1000, 9999)}",
        "DrugBank ID": f"DB{random.randint(10000, 99999)}",
    }

    # Add SMILES and InChI Key if available from original molecule
    if molecule.get("smiles"):
        identifiers["SMILES"] = molecule["smiles"]
    if molecule.get("inchikey") or molecule.get("inchi_key"):
        identifiers["InChI Key"] = molecule.get("inchikey") or molecule.get("inchi_key")

    # Add a mock description
    description = f"This is mock data for {name}. In a production environment, this would contain real data from external chemical databases."
    properties["Description"] = description

    return {
        "properties": properties,
        "identifiers": identifiers,
        "sources": [{"name": "Mock Data (Development Only)", "url": None}],
    }


@molecules.route("/api/molecules/create_or_update", methods=["POST"])
@cors_enabled
@handle_db_error
@validate_json
def create_or_update_molecule():
    """
    Create a new molecule or update an existing one based on identifiers.

    Request Body:
        JSON object containing molecule identifiers:
        {
            "name": "Optional name",
            "cas_number": "Optional CAS number",
            "pubchem_cid": "Optional PubChem CID",
            "inchikey": "Optional InChI Key",
            "smiles": "Optional SMILES",
            "chembl_id": "Optional ChEMBL ID"
        }

    At least one identifier should be provided.

    Returns:
        JSON response with created/updated molecule and status information
    """
    logger = current_app.logger
    logger.info("Create or update molecule request received")

    molecule_service = MoleculeService(get_graph())
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Check if we have at least one valid identifier
    valid_identifiers = {
        "name",
        "cas_number",
        "pubchem_cid",
        "inchikey",
        "smiles",
        "chembl_id",
    }
    provided_identifiers = {
        k: v for k, v in data.items() if k in valid_identifiers and v
    }

    if not provided_identifiers:
        return jsonify({"error": "At least one valid identifier must be provided"}), 400

    logger.info(
        f"Searching for existing molecule with identifiers: {provided_identifiers}"
    )

    # Try to find an existing molecule by any of the provided identifiers
    existing_molecule = None

    # First try structured identifiers (more reliable)
    for id_type in ["inchikey", "pubchem_cid", "cas_number", "chembl_id"]:
        if id_type in provided_identifiers and provided_identifiers[id_type]:
            if id_type == "inchikey":
                # Use specific method for inchikey
                query_result = molecule_service.find_by_inchikey(
                    provided_identifiers[id_type]
                )
                if query_result:
                    query_result = [
                        query_result
                    ]  # Convert to list for consistent handling
            else:
                # For other properties, use find_by_property from BaseRepository
                query_result = molecule_service.molecule_repository.find_by_property(
                    id_type, provided_identifiers[id_type]
                )
            if query_result and len(query_result) > 0:
                existing_molecule = query_result[0]  # Use the first match
                logger.info(
                    f"Found existing molecule by {id_type}: {existing_molecule.get('name', 'Unknown')}"
                )
                break

    # If not found by structured IDs, try SMILES
    if (
        not existing_molecule
        and "smiles" in provided_identifiers
        and provided_identifiers["smiles"]
    ):
        # For SMILES, use find_by_property from BaseRepository
        query_result = molecule_service.molecule_repository.find_by_property(
            "smiles", provided_identifiers["smiles"]
        )
        if query_result and len(query_result) > 0:
            existing_molecule = query_result[0]
            logger.info(
                f"Found existing molecule by SMILES: {existing_molecule.get('name', 'Unknown')}"
            )

    # Lastly, try by name (least reliable)
    if (
        not existing_molecule
        and "name" in provided_identifiers
        and provided_identifiers["name"]
    ):
        query_result = molecule_service.search_molecules(provided_identifiers["name"])
        if query_result and len(query_result) > 0:
            # For name searches, choose exact matches only
            for molecule in query_result:
                if (
                    molecule.get("name", "").lower()
                    == provided_identifiers["name"].lower()
                ):
                    existing_molecule = molecule
                    logger.info(
                        f"Found existing molecule by name: {existing_molecule.get('name', 'Unknown')}"
                    )
                    break

    # Prepare enrichment identifiers
    enrichment_identifiers = {k: v for k, v in provided_identifiers.items()}

    # Create or update the molecule
    created = False

    try:
        if existing_molecule:
            # Update the existing molecule
            molecule_id = existing_molecule.get("id")
            if not molecule_id:
                logger.warning("Existing molecule missing ID, generating a new ID")
                # Generate a standardized ID for this molecule
                try:
                    db_utils = DatabaseUtils(molecule_service.graph)
                    new_id = db_utils.get_next_available_id("Molecule")

                    # Try to find the molecule by properties we know it has
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

                    # Get the first property to use for identification
                    prop_name = list(query_props.keys())[0]
                    prop_value = query_props[prop_name]

                    # Update the molecule with the new ID
                    update_query = f"""
                    MATCH (m:Molecule)
                    WHERE m.{prop_name} = $prop_value
                    SET m.id = $new_id
                    RETURN m
                    """

                    db_utils.run_query(
                        update_query, {"prop_value": prop_value, "new_id": new_id}
                    )

                    # Set the ID for further processing
                    existing_molecule["id"] = new_id
                    molecule_id = new_id
                    logger.info(f"Successfully assigned ID {new_id} to molecule")
                except Exception as e:
                    logger.error(f"Failed to assign new ID: {str(e)}")
                    return (
                        jsonify({"error": f"Failed to update molecule: {str(e)}"}),
                        500,
                    )

            logger.info(f"Updating existing molecule with ID: {molecule_id}")

            # Merge existing data with new data
            update_data = {**existing_molecule, **data}

            # Remove the ID from the update data to avoid conflicts
            if "id" in update_data:
                del update_data["id"]

            # Update the molecule
            molecule = molecule_service.update_molecule(molecule_id, update_data, "API")
            if not molecule:
                raise ValueError(f"Failed to update molecule with ID {molecule_id}")

            logger.info(
                f"Successfully updated molecule: {molecule.get('name', 'Unknown')}"
            )
        else:
            # Create a new molecule
            logger.info("Creating new molecule")

            # Ensure we have a name for the molecule
            if "name" not in data or not data["name"]:
                if "inchikey" in data:
                    data["name"] = f"Molecule {data['inchikey']}"
                elif "smiles" in data:
                    data["name"] = f"Molecule {data['smiles'][:15]}..."
                else:
                    data["name"] = f"New Molecule {data.get('pubchem_cid', '')}"

            molecule = molecule_service.create_molecule(data, "API")
            if not molecule:
                raise ValueError("Failed to create new molecule")

            created = True
            logger.info(
                f"Successfully created molecule: {molecule.get('name', 'Unknown')}"
            )

        # Ensure we have a valid molecule object
        if not isinstance(molecule, dict):
            raise ValueError(f"Invalid molecule object type: {type(molecule)}")

        if "id" not in molecule:
            raise ValueError("Molecule missing required 'id' field")

        # Make sure we're using the standardized M-x format ID in the response
        molecule_id = molecule.get("id", "")
        # If the ID doesn't follow M-x format, standardize it
        if not (molecule_id and molecule_id.startswith("M-")):
            original_id = molecule_id
            standardized_id = molecule_service.standardize_id(molecule_id)
            logger.info(
                f"Standardizing ID format from {original_id} to {standardized_id}"
            )
            molecule["id"] = standardized_id

        # Enrich the molecule with additional data
        if enrichment_identifiers:
            try:
                logger.info(
                    f"Enriching molecule with identifiers: {enrichment_identifiers}"
                )

                # First try with PubChem
                enriched_data = None
                if molecule_service.pubchem_service:
                    try:
                        enriched_data = (
                            molecule_service.pubchem_service.enrich_molecule(
                                enrichment_identifiers
                            )
                        )
                    except Exception as e:
                        logger.error(f"Error enriching with PubChem: {str(e)}")

                # Then try with ChEMBL if needed
                if (
                    not enriched_data or len(enriched_data.get("properties", {})) < 3
                ) and molecule_service.chembl_service:
                    try:
                        chembl_data = molecule_service.chembl_service.enrich_molecule(
                            enrichment_identifiers
                        )
                        if chembl_data:
                            if not enriched_data:
                                enriched_data = chembl_data
                            else:
                                # Merge properties
                                for key, value in chembl_data.get(
                                    "properties", {}
                                ).items():
                                    if key not in enriched_data.get("properties", {}):
                                        if "properties" not in enriched_data:
                                            enriched_data["properties"] = {}
                                        enriched_data["properties"][key] = value
                    except Exception as e:
                        logger.error(f"Error enriching with ChEMBL: {str(e)}")

                # If we got enriched data, update the molecule
                if enriched_data and enriched_data.get("properties"):
                    logger.info("Updating molecule with enriched properties")
                    updated_molecule = molecule_service.update_molecule_properties(
                        molecule["id"], enriched_data["properties"]
                    )

                    # Get the updated molecule
                    if updated_molecule:
                        molecule = updated_molecule
                    else:
                        # If update_molecule_properties failed, get the molecule again
                        updated_from_db = molecule_service.get_molecule(molecule["id"])
                        if updated_from_db:
                            molecule = updated_from_db

            except Exception as e:
                logger.warning(f"Error during enrichment: {str(e)}")
                # Continue even if enrichment fails

        # Return response with created/updated molecule
        # Ensure we have a valid dictionary with the required fields
        response_data = {
            "id": molecule.get("id", ""),
            "name": molecule.get("name", "Unknown Compound"),
            "created": created,
            "updated": not created,
        }

        # Add the full molecule object if available
        if molecule:
            response_data["molecule"] = molecule

            # If the molecule's ID doesn't match our expected standardized format (M-x)
            if molecule.get("id") and not molecule.get("id").startswith("M-"):
                # Store the original ID for reference
                original_id = molecule.get("id")
                # Get or create standardized ID
                standardized_id = molecule_service.standardize_id(original_id)
                logger.info(
                    f"Converting response ID from {original_id} to {standardized_id}"
                )

                # Update both the top-level ID and the molecule's ID
                response_data["id"] = standardized_id
                response_data["molecule"]["id"] = standardized_id

                # Preserve the original ID as a separate field
                response_data["original_id"] = original_id
                response_data["molecule"]["original_id"] = original_id

            # Handle case where ID is in MOL_PUBCHEM_XXXX format specifically
            elif molecule.get("id") and molecule.get("id").startswith("MOL_PUBCHEM_"):
                original_id = molecule.get("id")
                standardized_id = molecule_service.standardize_id(original_id)
                logger.info(
                    f"Converting PubChem ID format from {original_id} to {standardized_id}"
                )

                # Update both the top-level ID and the molecule's ID
                response_data["id"] = standardized_id
                response_data["molecule"]["id"] = standardized_id

                # Preserve the original ID as a separate field
                response_data["original_id"] = original_id
                response_data["molecule"]["original_id"] = original_id

        return jsonify(response_data)

    except ValueError as e:
        # Handle specific value errors
        logger.error(f"Value error in create_or_update_molecule: {str(e)}")
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        # Handle all other errors
        logger.error(f"Error in create_or_update_molecule: {str(e)}")
        return jsonify({"error": str(e)}), 500


@molecules.route("/api/molecules/migrate_ids", methods=["POST", "OPTIONS"])
@cors_enabled
@handle_db_error
@requires_admin
def migrate_molecule_ids():
    """
    Migrate molecules to the new ID format (M-x).

    This is a one-time operation that should be run after updating to
    the new ID format. It will assign M-x style IDs to all molecules
    that don't already have an ID property.

    Returns:
        JSON response with migration statistics
    """
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({"status": "success"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add(
            "Access-Control-Allow-Headers", "Content-Type,Authorization"
        )
        response.headers.add("Access-Control-Allow-Methods", "POST,OPTIONS")
        return response

    logger = current_app.logger
    logger.info("Starting migration of molecule IDs to new format")

    try:
        molecule_service = MoleculeService(get_graph())
        result = molecule_service.migrate_to_new_id_format()

        logger.info(f"Migration result: {result}")
        return jsonify(
            {
                "status": "success",
                "message": f"Successfully migrated {result.get('migrated', 0)} molecules to new ID format",
                "statistics": result,
            }
        )
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        return (
            jsonify(
                {"status": "error", "message": f"Error during migration: {str(e)}"}
            ),
            500,
        )


@molecules.route("/api/molecules/debug_ids", methods=["GET"])
@cors_enabled
@handle_db_error
def debug_molecule_ids():
    """
    Debug endpoint to check molecule IDs in the database.

    Returns:
        JSON response with detailed molecule ID information
    """
    logger = current_app.logger
    logger.info("Debug request for molecule IDs")

    try:
        graph = get_graph()

        # Run a Cypher query to get detailed information about molecule IDs
        query = """
        MATCH (m:Molecule)
        RETURN 
            ID(m) as neo4j_id,
            m.id as id,
            m.original_id as original_id,
            m.name as name,
            m.inchikey as inchikey,
            m.smiles as smiles,
            LABELS(m) as labels
        """

        result = graph.run(query).data()

        # Process results to ensure they're JSON serializable
        processed_results = []
        for item in result:
            processed_item = {}
            for key, value in item.items():
                if value is not None:
                    processed_item[key] = value
            processed_results.append(processed_item)

        return jsonify(
            {
                "status": "success",
                "molecules": processed_results,
                "count": len(processed_results),
            }
        )

    except Exception as e:
        logger.error(f"Error in debug_molecule_ids: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
