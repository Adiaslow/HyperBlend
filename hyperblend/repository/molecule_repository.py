"""Repository for molecule database operations."""

import logging
from typing import List, Optional, Dict, Any, Union
from py2neo import Graph
from hyperblend.models.molecule import Molecule
from hyperblend.repository.base_repository import BaseRepository
import time


class MoleculeRepository(BaseRepository):
    """Repository for molecule-related database operations."""

    def __init__(self, graph: Optional[Graph] = None):
        """Initialize the repository with a database connection.

        Args:
            graph: Neo4j graph database connection
        """
        super().__init__(graph=graph, label="Molecule")
        self.logger = logging.getLogger(__name__)

    def find_by_id(self, id_value: str) -> Optional[Dict[str, Any]]:
        """Find a molecule by ID, handling both string IDs and Neo4j element IDs.

        Args:
            id_value: ID of the molecule (could be a string ID or Neo4j element ID)

        Returns:
            Molecule data or None if not found
        """
        try:
            # Try direct lookup based on id property first
            query = """
            MATCH (m:Molecule)
            WHERE m.id = $id
            RETURN m
            """
            results = self.db_utils.run_query(query, {"id": id_value})

            # If found by ID property, return it
            if results and results[0].get("m"):
                return dict(results[0]["m"])

            # If not found, try looking up by Neo4j element ID
            try:
                # Convert to integer for Neo4j elementId
                element_id = int(id_value)
                query = """
                MATCH (m:Molecule)
                WHERE elementId(m) = $element_id
                RETURN m
                """
                results = self.db_utils.run_query(query, {"element_id": element_id})
                if results and results[0].get("m"):
                    return dict(results[0]["m"])
            except (ValueError, TypeError):
                self.logger.debug(f"ID {id_value} is not a valid Neo4j element ID")

            # Not found by either method
            return None
        except Exception as e:
            self.logger.error(f"Error finding molecule by ID {id_value}: {str(e)}")
            return None

    def find_by_name(
        self, name: str, exact_match: bool = False
    ) -> List[Dict[str, Any]]:
        """Find molecules by name.

        Args:
            name: Name to search for
            exact_match: Whether to perform exact match (True) or pattern match (False)

        Returns:
            List of molecules matching the name
        """
        try:
            if exact_match:
                return self.find_by_property("name", name)
            else:
                query = """
                MATCH (m:Molecule)
                WHERE m.name =~ $pattern OR 
                      any(synonym IN m.synonyms WHERE synonym =~ $pattern)
                RETURN m
                """
                pattern = f"(?i).*{name}.*"
                results = self.db_utils.run_query(query, {"pattern": pattern})
                return [dict(record["m"]) for record in results]
        except Exception as e:
            self.logger.error(f"Error finding molecules by name: {str(e)}")
            return []

    def find_by_inchikey(self, inchikey: str) -> Optional[Dict[str, Any]]:
        """Find a molecule by its InChIKey.

        Args:
            inchikey: InChIKey to search for

        Returns:
            Molecule data or None if not found
        """
        try:
            molecules = self.find_by_property("inchikey", inchikey)
            return molecules[0] if molecules else None
        except Exception as e:
            self.logger.error(f"Error finding molecule by InChIKey: {str(e)}")
            return None

    def find_by_source(self, source: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Find molecules from a specific source.

        Args:
            source: Source to filter by
            limit: Maximum number of results to return

        Returns:
            List of molecules from the specified source
        """
        try:
            query = """
            MATCH (m:Molecule)
            WHERE $source in m.sources
            RETURN m
            LIMIT $limit
            """
            results = self.db_utils.run_query(query, {"source": source, "limit": limit})
            return [dict(record["m"]) for record in results]
        except Exception as e:
            self.logger.error(f"Error finding molecules by source: {str(e)}")
            return []

    def find_similar_molecules(
        self, molecule_id: str, similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Find molecules similar to the given molecule.

        Args:
            molecule_id: ID of the reference molecule
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of similar molecules
        """
        try:
            # First get the reference molecule
            ref_molecule = self.find_by_id(molecule_id)
            if not ref_molecule:
                return []

            # Extract properties for comparison
            ref_weight = ref_molecule.get("molecular_weight", 0)
            ref_logp = ref_molecule.get("logp", 0)

            # Find similar molecules based on molecular properties
            query = """
            MATCH (m:Molecule)
            WHERE ID(m) <> toInteger($id)
            AND abs(m.molecular_weight - $weight) / $weight < 0.1
            AND abs(m.logp - $logp) < 1.0
            RETURN m
            LIMIT 50
            """

            params = {
                "id": molecule_id,
                "weight": ref_weight if ref_weight > 0 else 1,  # Avoid division by zero
                "logp": ref_logp,
            }

            results = self.db_utils.run_query(query, params)
            return [dict(record["m"]) for record in results]
        except Exception as e:
            self.logger.error(f"Error finding similar molecules: {str(e)}")
            return []

    def get_molecule_targets(self, molecule_id: str) -> List[Dict[str, Any]]:
        """Get targets associated with a molecule.

        Args:
            molecule_id: ID of the molecule

        Returns:
            List of targets associated with the molecule
        """
        try:
            self.logger.debug(f"Getting targets for molecule ID: {molecule_id}")

            # First try to find the molecule using find_by_id to normalize the ID lookup
            molecule = self.find_by_id(molecule_id)

            # If we found the molecule, use its ID for the relationship lookup
            if molecule:
                self.logger.debug(f"Found molecule with ID {molecule_id}")
                actual_id = molecule.get("id", molecule_id)

                # Comprehensive query that tries multiple ways to match the molecule
                query = """
                MATCH (m:Molecule)
                WHERE m.id = $id OR toString(elementId(m)) = $id OR elementId(m) = toInteger($id_as_int)
                MATCH (m)-[r]->(t:Target)
                RETURN 
                    t {
                        .*, 
                        id: CASE 
                            WHEN t.id IS NOT NULL THEN t.id 
                            ELSE toString(elementId(t)) 
                        END
                    } as t,
                    type(r) as relationship_type,
                    r {.*} as relationship_data
                """

                # Try to convert ID to integer for element ID comparison
                try:
                    id_as_int = int(molecule_id)
                except (ValueError, TypeError):
                    id_as_int = -1  # Use invalid ID if conversion fails

                results = self.db_utils.run_query(
                    query, {"id": actual_id, "id_as_int": id_as_int}
                )

                # Format results
                formatted_targets = []
                for record in results:
                    if not record.get("t"):
                        continue

                    target = record["t"]
                    rel_data = record.get("relationship_data", {})

                    target_data = {
                        "id": target.get("id"),
                        "name": target.get("name", "Unknown Target"),
                        "type": "Target",
                        "relationship_type": record.get(
                            "relationship_type", "INTERACTS_WITH"
                        ),
                        "activity_type": rel_data.get(
                            "activity_type", rel_data.get("affinity_type")
                        ),
                        "activity_value": rel_data.get(
                            "activity_value", rel_data.get("affinity")
                        ),
                        "activity_unit": rel_data.get("activity_unit", ""),
                        "confidence_score": rel_data.get("confidence_score"),
                    }
                    formatted_targets.append(target_data)

                self.logger.debug(
                    f"Found {len(formatted_targets)} targets for molecule {actual_id}"
                )
                return formatted_targets
            else:
                self.logger.warning(f"Molecule with ID {molecule_id} not found")
                return []
        except Exception as e:
            self.logger.error(f"Error getting molecule targets: {str(e)}")
            import traceback

            self.logger.error(traceback.format_exc())
            return []

    def create_molecule(
        self, properties: Dict[str, Any], source: str = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new molecule with the given properties.

        Args:
            properties: Molecule properties
            source: Optional source to associate with the molecule

        Returns:
            Created molecule data or None if creation failed
        """
        try:
            # Check if molecule with same name already exists (case insensitive)
            if "name" in properties and properties["name"]:
                name = properties["name"]
                self.logger.info(
                    f"Checking if molecule with name '{name}' already exists"
                )
                existing_by_name = self.find_by_name(name, exact_match=True)
                if existing_by_name and len(existing_by_name) > 0:
                    self.logger.info(
                        f"Found existing molecule with name '{name}', updating instead of creating new"
                    )
                    return self.update_molecule(
                        existing_by_name[0]["id"], properties, source
                    )

            # Check if molecule with same InChIKey already exists
            if "inchikey" in properties and properties["inchikey"]:
                existing = self.find_by_inchikey(properties["inchikey"])
                if existing:
                    self.logger.info(
                        f"Found existing molecule with InChIKey '{properties['inchikey']}', updating"
                    )
                    return self.update_molecule(existing["id"], properties, source)

            # Check if molecule with same PubChem CID already exists
            if "pubchem_cid" in properties and properties["pubchem_cid"]:
                existing = self.find_by_property(
                    "pubchem_cid", properties["pubchem_cid"]
                )
                if existing and len(existing) > 0:
                    self.logger.info(
                        f"Found existing molecule with PubChem CID '{properties['pubchem_cid']}', updating"
                    )
                    return self.update_molecule(existing[0]["id"], properties, source)

            # Check if molecule with same ChEMBL ID already exists
            if "chembl_id" in properties and properties["chembl_id"]:
                existing = self.find_by_property("chembl_id", properties["chembl_id"])
                if existing and len(existing) > 0:
                    self.logger.info(
                        f"Found existing molecule with ChEMBL ID '{properties['chembl_id']}', updating"
                    )
                    return self.update_molecule(existing[0]["id"], properties, source)

            # Check if molecule with same CAS number already exists
            if "cas_number" in properties and properties["cas_number"]:
                existing = self.find_by_property("cas_number", properties["cas_number"])
                if existing and len(existing) > 0:
                    self.logger.info(
                        f"Found existing molecule with CAS number '{properties['cas_number']}', updating"
                    )
                    return self.update_molecule(existing[0]["id"], properties, source)

            # Ensure name is present
            if "name" not in properties or not properties["name"]:
                if "inchikey" in properties and properties["inchikey"]:
                    properties["name"] = f"Molecule {properties['inchikey'][:10]}"
                elif "smiles" in properties and properties["smiles"]:
                    properties["name"] = f"Molecule {properties['smiles'][:10]}"
                else:
                    properties["name"] = f"New Molecule {int(time.time())}"

            # Generate a standardized ID if not provided
            if "id" not in properties or not properties["id"]:
                properties["id"] = self.db_utils.get_next_available_id("Molecule")

            # Create the molecule
            molecule = self.create(properties)

            if not molecule:
                self.logger.error("Failed to create molecule in database")
                return None

            # Validate the created molecule has an ID
            if "id" not in molecule or not molecule["id"]:
                self.logger.warning("Created molecule missing ID, assigning one")
                molecule["id"] = self.db_utils.get_next_available_id("Molecule")

                # Update the node with the new ID
                self.update(molecule.get("_neo4j_id", ""), {"id": molecule["id"]})

            # Add source relationship if provided
            if source and molecule and "id" in molecule:
                self._create_source_relationship(molecule["id"], source)

            # Enrich the molecule with external data
            return self.enrich_molecule_data(molecule)
        except Exception as e:
            self.logger.error(f"Error creating molecule: {str(e)}")
            import traceback

            self.logger.error(traceback.format_exc())
            return None

    def enrich_molecule_data(self, molecule: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich molecule data from external databases.

        Args:
            molecule: Molecule data dictionary

        Returns:
            Enhanced molecule data
        """
        if not molecule or "id" not in molecule:
            self.logger.error("Cannot enrich molecule: Invalid molecule data")
            return molecule

        try:
            molecule_id = molecule["id"]
            self.logger.info(f"Enriching molecule {molecule_id} with external data")

            # 1. Try to query external databases using identifiers
            enriched_data = None

            # Create a dictionary of identifiers to use for enrichment
            identifiers = {}
            for key in [
                "inchikey",
                "pubchem_cid",
                "smiles",
                "chembl_id",
                "cas_number",
                "name",
            ]:
                if key in molecule and molecule[key]:
                    identifiers[key] = molecule[key]

            if not identifiers:
                self.logger.warning(
                    f"No suitable identifiers found to enrich molecule {molecule_id}"
                )
                return molecule

            # Try to enrich with PubChem (if available)
            try:
                from hyperblend.services.external.pubchem_service import PubChemService

                pubchem_service = PubChemService(self.graph)
                self.logger.info(f"Querying PubChem for molecule {molecule_id}")
                pubchem_data = pubchem_service.enrich_molecule(identifiers)

                if pubchem_data and "properties" in pubchem_data:
                    enriched_data = pubchem_data
                    self.logger.info(
                        f"Successfully enriched molecule {molecule_id} with PubChem data"
                    )
            except Exception as e:
                self.logger.warning(f"Error enriching with PubChem: {str(e)}")

            # Try to enrich with ChEMBL (if available)
            if not enriched_data or len(enriched_data.get("properties", {})) < 5:
                try:
                    from hyperblend.services.external.chembl_service import (
                        ChEMBLService,
                    )

                    chembl_service = ChEMBLService(self.graph)
                    self.logger.info(f"Querying ChEMBL for molecule {molecule_id}")
                    chembl_data = chembl_service.enrich_molecule(identifiers)

                    if chembl_data and "properties" in chembl_data:
                        if not enriched_data:
                            enriched_data = chembl_data
                            self.logger.info(
                                f"Successfully enriched molecule {molecule_id} with ChEMBL data"
                            )
                        else:
                            # Merge properties from ChEMBL
                            for key, value in chembl_data.get("properties", {}).items():
                                if (
                                    key not in enriched_data.get("properties", {})
                                    or not enriched_data["properties"][key]
                                ):
                                    if "properties" not in enriched_data:
                                        enriched_data["properties"] = {}
                                    enriched_data["properties"][key] = value
                            self.logger.info(
                                f"Added additional data from ChEMBL to molecule {molecule_id}"
                            )
                except Exception as e:
                    self.logger.warning(f"Error enriching with ChEMBL: {str(e)}")

            # Try to enrich with DrugBank (if available)
            if "drugbank_id" in identifiers or "cas_number" in identifiers:
                try:
                    # Check if DrugBank API key is available in settings
                    from hyperblend.app.config.settings import settings

                    if (
                        hasattr(settings, "DRUGBANK_API_KEY")
                        and settings.DRUGBANK_API_KEY
                    ):
                        from hyperblend.services.external.drugbank_service import (
                            DrugBankService,
                        )

                        drugbank_service = DrugBankService(
                            api_key=settings.DRUGBANK_API_KEY, graph=self.graph
                        )
                        self.logger.info(
                            f"Querying DrugBank for molecule {molecule_id}"
                        )
                        drugbank_data = drugbank_service.enrich_molecule(identifiers)

                        if drugbank_data and "properties" in drugbank_data:
                            if not enriched_data:
                                enriched_data = drugbank_data
                                self.logger.info(
                                    f"Successfully enriched molecule {molecule_id} with DrugBank data"
                                )
                            else:
                                # Merge properties from DrugBank
                                for key, value in drugbank_data.get(
                                    "properties", {}
                                ).items():
                                    if (
                                        key not in enriched_data.get("properties", {})
                                        or not enriched_data["properties"][key]
                                    ):
                                        if "properties" not in enriched_data:
                                            enriched_data["properties"] = {}
                                        enriched_data["properties"][key] = value
                                self.logger.info(
                                    f"Added additional data from DrugBank to molecule {molecule_id}"
                                )
                except Exception as e:
                    self.logger.warning(f"Error enriching with DrugBank: {str(e)}")

            # 2. If we got enriched data, update the molecule
            if enriched_data and enriched_data.get("properties"):
                # Update the molecule with the enriched properties
                updated_props = {}

                # Copy existing properties
                for key, value in molecule.items():
                    updated_props[key] = value

                # Add new properties from enrichment
                for key, value in enriched_data.get("properties", {}).items():
                    if key not in updated_props or not updated_props[key]:
                        updated_props[key] = value

                # Update the molecule
                updated_molecule = self.update(molecule_id, updated_props)
                if updated_molecule:
                    self.logger.info(
                        f"Updated molecule {molecule_id} with enriched data"
                    )
                    return updated_molecule

            return molecule
        except Exception as e:
            self.logger.error(f"Error enriching molecule data: {str(e)}")
            import traceback

            self.logger.error(traceback.format_exc())
            return molecule

    def update_molecule(
        self, molecule_id: str, properties: Dict[str, Any], source: str = None
    ) -> Optional[Dict[str, Any]]:
        """Update an existing molecule.

        Args:
            molecule_id: ID of the molecule to update
            properties: Updated properties
            source: Optional source to associate with the molecule

        Returns:
            Updated molecule data or None if update failed
        """
        try:
            if not molecule_id:
                raise ValueError("Molecule ID is required for update")

            # Validate and standardize the ID
            if not molecule_id.startswith("M-"):
                self.logger.info(f"Standardizing molecule ID: {molecule_id}")
                # Try to find the molecule first to ensure it exists
                existing = self.find_by_id(molecule_id)
                if not existing:
                    self.logger.error(f"Cannot find molecule with ID: {molecule_id}")
                    return None

                # Generate a new standardized ID
                new_id = self.db_utils.get_next_available_id("Molecule")
                self.logger.info(
                    f"Generated new ID: {new_id} for molecule: {molecule_id}"
                )

                # Update the molecule with the new ID
                properties["id"] = new_id

                # Keep track of the original ID to find the node
                original_id = molecule_id
                molecule_id = new_id

                # Use a query that can find the node by various ID formats
                query = """
                MATCH (m:Molecule)
                WHERE m.id = $original_id OR 
                      toString(elementId(m)) = $original_id OR 
                      elementId(m) = $original_id_int
                SET m.id = $new_id
                RETURN m
                """

                # Try to convert ID to integer for element ID comparison
                try:
                    original_id_int = int(original_id)
                except (ValueError, TypeError):
                    original_id_int = -1

                results = self.db_utils.run_query(
                    query,
                    {
                        "original_id": original_id,
                        "original_id_int": original_id_int,
                        "new_id": new_id,
                    },
                )

                if not results or not results[0].get("m"):
                    self.logger.error(
                        f"Failed to update molecule ID from {original_id} to {new_id}"
                    )
                    return None

            # Remove ID from properties to avoid conflicts during update
            if "id" in properties:
                del properties["id"]

            # Update the molecule
            molecule = self.update(molecule_id, properties)

            if not molecule:
                self.logger.error(f"Failed to update molecule with ID: {molecule_id}")
                return None

            # Add source relationship if provided
            if source and molecule and "id" in molecule:
                self._create_source_relationship(molecule["id"], source)

            return molecule
        except Exception as e:
            self.logger.error(f"Error updating molecule: {str(e)}")
            import traceback

            self.logger.error(traceback.format_exc())
            return None

    def _create_source_relationship(self, molecule_id: str, source_name: str) -> bool:
        """Add a source property to the molecule instead of creating a separate Source node.

        Args:
            molecule_id: ID of the molecule
            source_name: Name of the source

        Returns:
            True if successful, False otherwise
        """
        try:
            # Log inputs for debugging
            self.logger.debug(
                f"Adding source '{source_name}' to molecule ID: {molecule_id}"
            )

            # Add source as a property to the molecule
            query = """
            MATCH (m:Molecule)
            WHERE m.id = $id OR 
                 (m.id IS NULL AND toString(elementId(m)) = $id) OR
                 (m.id IS NULL AND elementId(m) = toInteger($id_as_int))
            SET m.sources = CASE 
                WHEN m.sources IS NOT NULL 
                THEN CASE 
                    WHEN $source IN m.sources THEN m.sources 
                    ELSE m.sources + $source 
                END
                ELSE [$source]
            END
            RETURN m
            """

            # Try to convert ID to integer for element ID comparison
            try:
                id_as_int = int(molecule_id)
            except (ValueError, TypeError):
                id_as_int = -1  # Use invalid ID if conversion fails

            result = self.db_utils.run_query(
                query,
                {"id": molecule_id, "id_as_int": id_as_int, "source": source_name},
            )

            # Check if the update was successful
            if result and len(result) > 0:
                self.logger.debug(
                    f"Source property added for molecule ID: {molecule_id}"
                )
                return True
            else:
                self.logger.warning(
                    f"Could not find molecule with ID: {molecule_id} to add source"
                )
                return False
        except Exception as e:
            self.logger.error(f"Error adding source property: {str(e)}")
            import traceback

            self.logger.error(traceback.format_exc())
            return False

    # Alias for compatibility with service layer
    def find_molecules_by_source(
        self, source: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Alias for find_by_source to maintain compatibility with service layer.

        Args:
            source: Source to filter by
            limit: Maximum number of results to return

        Returns:
            List of molecules from the specified source
        """
        return self.find_by_source(source, limit)

    # Alias for compatibility with service layer
    def find_molecule_by_id(self, id_value: str) -> Optional[Dict[str, Any]]:
        """Alias for find_by_id to maintain compatibility with service layer.

        Args:
            id_value: ID of the molecule to find

        Returns:
            Molecule data or None if not found
        """
        return self.find_by_id(id_value)

    # Alias for compatibility with service layer
    def find_molecules_by_name(
        self, name: str, exact: bool = False
    ) -> List[Dict[str, Any]]:
        """Alias for find_by_name to maintain compatibility with service layer.

        Args:
            name: Name to search for
            exact: Whether to perform exact match (True) or pattern match (False)

        Returns:
            List of molecules matching the name
        """
        return self.find_by_name(name, exact_match=exact)

    # Alias for compatibility with service layer
    def find_molecule_by_inchikey(self, inchikey: str) -> Optional[Dict[str, Any]]:
        """Alias for find_by_inchikey to maintain compatibility with service layer.

        Args:
            inchikey: InChIKey to search for

        Returns:
            Molecule data or None if not found
        """
        return self.find_by_inchikey(inchikey)

    def merge_duplicate_molecules(self) -> Dict[str, int]:
        """
        Find and merge molecules with the same identifiers.

        This method looks for molecules with identical pubchem_cid, chembl_id, or cas_number
        and merges them, keeping the most complete data.

        Returns:
            Dict with statistics about merges performed
        """
        stats = {
            "total_checked": 0,
            "duplicates_found": 0,
            "merged_successfully": 0,
            "merge_failed": 0,
        }

        try:
            # Check for duplicates by pubchem_cid (non-null)
            self.logger.info("Looking for molecules with duplicate PubChem CIDs...")
            query = """
            MATCH (m1:Molecule), (m2:Molecule)
            WHERE m1.pubchem_cid IS NOT NULL AND m1.pubchem_cid = m2.pubchem_cid
            AND id(m1) < id(m2)
            RETURN m1, m2
            """
            duplicate_pairs = self.db_utils.run_query(query)
            stats["total_checked"] += len(duplicate_pairs)

            # Process PubChem CID duplicates
            for pair in duplicate_pairs:
                stats["duplicates_found"] += 1
                m1 = dict(pair["m1"])
                m2 = dict(pair["m2"])
                self.logger.info(
                    f"Found duplicate molecules with PubChem CID {m1.get('pubchem_cid')}: {m1.get('id')}, {m2.get('id')}"
                )

                try:
                    self._merge_molecule_pair(m1, m2)
                    stats["merged_successfully"] += 1
                except Exception as e:
                    self.logger.error(f"Failed to merge molecules: {str(e)}")
                    stats["merge_failed"] += 1

            # Check for duplicates by ChEMBL ID (non-null)
            self.logger.info("Looking for molecules with duplicate ChEMBL IDs...")
            query = """
            MATCH (m1:Molecule), (m2:Molecule)
            WHERE m1.chembl_id IS NOT NULL AND m1.chembl_id = m2.chembl_id
            AND id(m1) < id(m2)
            RETURN m1, m2
            """
            duplicate_pairs = self.db_utils.run_query(query)
            stats["total_checked"] += len(duplicate_pairs)

            # Process ChEMBL ID duplicates
            for pair in duplicate_pairs:
                stats["duplicates_found"] += 1
                m1 = dict(pair["m1"])
                m2 = dict(pair["m2"])
                self.logger.info(
                    f"Found duplicate molecules with ChEMBL ID {m1.get('chembl_id')}: {m1.get('id')}, {m2.get('id')}"
                )

                try:
                    self._merge_molecule_pair(m1, m2)
                    stats["merged_successfully"] += 1
                except Exception as e:
                    self.logger.error(f"Failed to merge molecules: {str(e)}")
                    stats["merge_failed"] += 1

            # Check for duplicates by CAS number (non-null)
            self.logger.info("Looking for molecules with duplicate CAS numbers...")
            query = """
            MATCH (m1:Molecule), (m2:Molecule)
            WHERE m1.cas_number IS NOT NULL AND m1.cas_number = m2.cas_number
            AND id(m1) < id(m2)
            RETURN m1, m2
            """
            duplicate_pairs = self.db_utils.run_query(query)
            stats["total_checked"] += len(duplicate_pairs)

            # Process CAS number duplicates
            for pair in duplicate_pairs:
                stats["duplicates_found"] += 1
                m1 = dict(pair["m1"])
                m2 = dict(pair["m2"])
                self.logger.info(
                    f"Found duplicate molecules with CAS number {m1.get('cas_number')}: {m1.get('id')}, {m2.get('id')}"
                )

                try:
                    self._merge_molecule_pair(m1, m2)
                    stats["merged_successfully"] += 1
                except Exception as e:
                    self.logger.error(f"Failed to merge molecules: {str(e)}")
                    stats["merge_failed"] += 1

            # Check for duplicates by InChIKey (most reliable)
            self.logger.info("Looking for molecules with duplicate InChIKeys...")
            query = """
            MATCH (m1:Molecule), (m2:Molecule)
            WHERE m1.inchikey IS NOT NULL AND m1.inchikey = m2.inchikey
            AND id(m1) < id(m2)
            RETURN m1, m2
            """
            duplicate_pairs = self.db_utils.run_query(query)
            stats["total_checked"] += len(duplicate_pairs)

            # Process InChIKey duplicates
            for pair in duplicate_pairs:
                stats["duplicates_found"] += 1
                m1 = dict(pair["m1"])
                m2 = dict(pair["m2"])
                self.logger.info(
                    f"Found duplicate molecules with InChIKey {m1.get('inchikey')}: {m1.get('id')}, {m2.get('id')}"
                )

                try:
                    self._merge_molecule_pair(m1, m2)
                    stats["merged_successfully"] += 1
                except Exception as e:
                    self.logger.error(f"Failed to merge molecules: {str(e)}")
                    stats["merge_failed"] += 1

            self.logger.info(
                f"Molecule merge completed: {stats['merged_successfully']} merged, {stats['merge_failed']} failed"
            )
            return stats
        except Exception as e:
            self.logger.error(f"Error in merge_duplicate_molecules: {str(e)}")
            import traceback

            self.logger.error(traceback.format_exc())
            return stats

    def _merge_molecule_pair(self, m1: Dict[str, Any], m2: Dict[str, Any]) -> str:
        """
        Merge two molecule entities, keeping the most complete data.

        Args:
            m1: First molecule data
            m2: Second molecule data

        Returns:
            ID of the surviving molecule
        """
        # Get the molecule IDs
        m1_id = m1.get("id")
        m2_id = m2.get("id")

        if not m1_id or not m2_id:
            raise ValueError("Both molecules must have an ID to merge")

        # Always keep the molecule with the lower numbered ID (assuming M-x format)
        # This ensures consistent merging behavior
        keep_m1 = True
        if m1_id.startswith("M-") and m2_id.startswith("M-"):
            try:
                m1_num = int(m1_id.split("-")[1])
                m2_num = int(m2_id.split("-")[1])
                keep_m1 = m1_num <= m2_num
            except (ValueError, IndexError):
                # If we can't parse the IDs, default to keeping m1
                pass

        # Determine which molecule to keep and which to merge
        keep_id = m1_id if keep_m1 else m2_id
        merge_id = m2_id if keep_m1 else m1_id

        keep_mol = m1 if keep_m1 else m2
        merge_mol = m2 if keep_m1 else m1

        self.logger.info(f"Merging molecule {merge_id} into {keep_id}")

        # 1. Merge all properties from both molecules, preferring non-null values
        merged_props = {}
        for k in set(keep_mol.keys()) | set(merge_mol.keys()):
            if k == "id":
                merged_props[k] = keep_id
                continue

            # Take the value from keep_mol if it exists, otherwise from merge_mol
            if k in keep_mol and keep_mol[k] is not None:
                merged_props[k] = keep_mol[k]
            elif k in merge_mol and merge_mol[k] is not None:
                merged_props[k] = merge_mol[k]

        # 2. Transfer all relationships from the molecule being merged
        query = """
        MATCH (m1:Molecule {id: $keep_id})
        MATCH (m2:Molecule {id: $merge_id})
        
        // Get all relationships from m2
        OPTIONAL MATCH (m2)-[r]->(target)
        WHERE NOT target:Molecule  // Avoid self-relationships
        WITH m1, m2, collect({rel: type(r), target: target, props: properties(r)}) AS outRels
        
        // Get all relationships to m2
        OPTIONAL MATCH (source)-[r]->(m2)
        WHERE NOT source:Molecule  // Avoid self-relationships
        WITH m1, m2, outRels, collect({rel: type(r), source: source, props: properties(r)}) AS inRels
        
        // Create outgoing relationships from m1
        FOREACH (rel IN outRels |
          FOREACH (t IN CASE WHEN rel.target IS NOT NULL THEN [rel.target] ELSE [] END |
            MERGE (m1)-[r:${rel.rel}]->(t)
            SET r += rel.props
          )
        )
        
        // Create incoming relationships to m1
        FOREACH (rel IN inRels |
          FOREACH (s IN CASE WHEN rel.source IS NOT NULL THEN [rel.source] ELSE [] END |
            MERGE (s)-[r:${rel.rel}]->(m1)
            SET r += rel.props
          )
        )
        
        // Delete m2
        DETACH DELETE m2
        
        RETURN m1
        """

        # Run a modified query that properly handles dynamic relationship types
        # Due to how Cypher works, we need to do this in multiple steps

        # Step 1: Get all outgoing relationships from m2
        query_out = """
        MATCH (m2:Molecule {id: $merge_id})-[r]->(target)
        WHERE NOT target:Molecule
        RETURN type(r) AS rel_type, target, properties(r) AS props
        """
        out_rels = self.db_utils.run_query(query_out, {"merge_id": merge_id})

        # Step 2: Get all incoming relationships to m2
        query_in = """
        MATCH (source)-[r]->(m2:Molecule {id: $merge_id})
        WHERE NOT source:Molecule
        RETURN type(r) AS rel_type, source, properties(r) AS props
        """
        in_rels = self.db_utils.run_query(query_in, {"merge_id": merge_id})

        # Step 3: Create each outgoing relationship from m1
        for rel in out_rels:
            create_query = f"""
            MATCH (m1:Molecule {{id: $keep_id}})
            MATCH (target)
            WHERE elementId(target) = $target_id
            MERGE (m1)-[r:{rel['rel_type']}]->(target)
            SET r += $props
            """
            self.db_utils.run_query(
                create_query,
                {
                    "keep_id": keep_id,
                    "target_id": rel["target"]._id,
                    "props": rel["props"],
                },
            )

        # Step 4: Create each incoming relationship to m1
        for rel in in_rels:
            create_query = f"""
            MATCH (source)
            WHERE elementId(source) = $source_id
            MATCH (m1:Molecule {{id: $keep_id}})
            MERGE (source)-[r:{rel['rel_type']}]->(m1)
            SET r += $props
            """
            self.db_utils.run_query(
                create_query,
                {
                    "keep_id": keep_id,
                    "source_id": rel["source"]._id,
                    "props": rel["props"],
                },
            )

        # Step 5: Update the properties of the merged molecule
        self.update(keep_id, merged_props)

        # Step 6: Delete the merged molecule
        delete_query = """
        MATCH (m:Molecule {id: $merge_id})
        DETACH DELETE m
        """
        self.db_utils.run_query(delete_query, {"merge_id": merge_id})

        self.logger.info(f"Successfully merged molecule {merge_id} into {keep_id}")
        return keep_id
