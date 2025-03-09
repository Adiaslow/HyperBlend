"""Service for querying targets from the internal database."""

import logging
from typing import List, Optional, Dict, Any
from py2neo import Graph, NodeMatcher
from .base_service import BaseInternalService
from ..external.uniprot_service import UniProtService

logger = logging.getLogger(__name__)


class TargetService(BaseInternalService):
    """Service for querying targets from the database."""

    def __init__(self, graph: Graph):
        """Initialize the target service.

        Args:
            graph: Neo4j graph database connection
        """
        super().__init__(graph)
        self.matcher = NodeMatcher(graph)
        self.uniprot_service = UniProtService()

    def get_all_targets(self) -> List[Dict[str, Any]]:
        """Get all targets from the database.

        Returns:
            List of target dictionaries
        """
        query = """
        MATCH (t:Target)
        OPTIONAL MATCH (t)-[:HAS_MOLECULE]-(m:Molecule)
        WITH t, count(m) as compound_count
        RETURN {
            id: toString(elementId(t)),
            name: t.name,
            type: t.type,
            organism: t.organism,
            description: t.description,
            compound_count: compound_count
        } as target
        ORDER BY target.name
        """
        try:
            result = self.graph.run(query)
            return [dict(record["target"]) for record in result]
        except Exception as e:
            logger.error(f"Error getting all targets: {str(e)}")
            return []

    def search_targets(self, query: str) -> List[Dict[str, Any]]:
        """Search for targets by name, description, or UniProt ID.

        Args:
            query: Search term

        Returns:
            List of matching target dictionaries
        """
        # First try to find existing targets
        search_pattern = f"(?i).*{query}.*"
        cypher_query = """
        MATCH (t:Target)
        WHERE t.name =~ $pattern 
           OR t.description =~ $pattern
           OR t.uniprot_id =~ $pattern
           OR t.uniprot_id = $exact_query
        OPTIONAL MATCH (t)-[:HAS_MOLECULE]-(m:Molecule)
        WITH t, count(m) as compound_count
        RETURN {
            id: toString(elementId(t)),
            name: t.name,
            type: t.type,
            organism: t.organism,
            description: t.description,
            uniprot_id: t.uniprot_id,
            compound_count: compound_count
        } as target
        ORDER BY target.name
        """
        try:
            result = self.graph.run(
                cypher_query, pattern=search_pattern, exact_query=query
            )
            targets = [dict(record["target"]) for record in result]

            # If no results and query looks like a UniProt ID, try to fetch from UniProt
            if not targets and query.startswith("P") and query[1:].isdigit():
                target = self.fetch_and_store_uniprot_target(query)
                if target:
                    targets = [target]

            return targets
        except Exception as e:
            logger.error(f"Error searching targets: {str(e)}")
            return []

    def get_target(self, target_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific target by ID.

        Args:
            target_id: Target ID

        Returns:
            Target dictionary or None if not found
        """
        query = """
        MATCH (t:Target)
        WHERE toString(elementId(t)) = $target_id
        RETURN {
            id: toString(elementId(t)),
            name: t.name,
            type: t.type,
            organism: t.organism,
            description: t.description,
            sequence: t.sequence,
            uniprot_id: t.uniprot_id,
            chembl_id: t.chembl_id
        } as target
        """
        try:
            result = self.graph.run(query, target_id=target_id).data()
            return result[0]["target"] if result else None
        except Exception as e:
            logger.error(f"Error getting target {target_id}: {str(e)}")
            return None

    def get_target_molecules(self, target_id: str) -> List[Dict[str, Any]]:
        """Get molecules associated with a target.

        Args:
            target_id: Target ID

        Returns:
            List of molecule dictionaries
        """
        query = """
        MATCH (t:Target)-[r:HAS_MOLECULE]-(m:Molecule)
        WHERE toString(elementId(t)) = $target_id
        RETURN {
            id: toString(elementId(m)),
            name: m.name,
            smiles: m.smiles,
            activity: r.activity_value + ' ' + coalesce(r.activity_units, '')
        } as molecule
        """
        try:
            result = self.graph.run(query, target_id=target_id)
            return [dict(record["molecule"]) for record in result]
        except Exception as e:
            logger.error(f"Error getting target molecules for {target_id}: {str(e)}")
            return []

    def update_target(self, target_id: str, target_data: Dict[str, Any]) -> bool:
        """Update a target with new data.

        Args:
            target_id: Target ID
            target_data: New target data

        Returns:
            True if successful, False otherwise
        """
        query = """
        MATCH (t:Target)
        WHERE toString(elementId(t)) = $target_id
        SET t += $target_data
        RETURN t
        """
        try:
            result = self.graph.run(query, target_id=target_id, target_data=target_data)
            return bool(result)
        except Exception as e:
            logger.error(f"Error updating target {target_id}: {str(e)}")
            return False

    def find_by_name(self, name: str, exact: bool = False) -> List[Dict[str, Any]]:
        """
        Find targets by name.

        Args:
            name: Name to search for
            exact: Whether to perform exact match (default: False)

        Returns:
            List[Dict[str, Any]]: List of targets found
        """
        if exact:
            query = """
            MATCH (t:Target {name: $name})
            OPTIONAL MATCH (t)-[:HAS_SYNONYM]->(s:Synonym)
            OPTIONAL MATCH (t)-[:FROM_SOURCE]->(src:Source)
            OPTIONAL MATCH (t)-[:HAS_ACTIVITY]-(m:Molecule)
            RETURN t, collect(DISTINCT s.name) as synonyms, 
                   collect(DISTINCT src.name) as sources,
                   count(DISTINCT m) as molecule_count
            """
        else:
            query = """
            MATCH (t:Target)
            WHERE t.name =~ $pattern
            OPTIONAL MATCH (t)-[:HAS_SYNONYM]->(s:Synonym)
            OPTIONAL MATCH (t)-[:FROM_SOURCE]->(src:Source)
            OPTIONAL MATCH (t)-[:HAS_ACTIVITY]-(m:Molecule)
            RETURN t, collect(DISTINCT s.name) as synonyms, 
                   collect(DISTINCT src.name) as sources,
                   count(DISTINCT m) as molecule_count
            """

        try:
            pattern = f"(?i).*{name}.*"  # Case-insensitive pattern
            results = self.graph.run(
                query, parameters={"name": name, "pattern": pattern}
            ).data()
            return [self._format_target_result(result) for result in results]
        except Exception as e:
            self.logger.error(f"Error finding targets by name: {str(e)}")
            return []

    def find_by_type(self, target_type: str) -> List[Dict[str, Any]]:
        """
        Find targets by type (e.g., 'protein', 'enzyme', 'receptor').

        Args:
            target_type: Type of target to filter by

        Returns:
            List[Dict[str, Any]]: List of targets found
        """
        query = """
        MATCH (t:Target {type: $type})
        OPTIONAL MATCH (t)-[:HAS_SYNONYM]->(s:Synonym)
        OPTIONAL MATCH (t)-[:FROM_SOURCE]->(src:Source)
        OPTIONAL MATCH (t)-[:HAS_ACTIVITY]-(m:Molecule)
        RETURN t, collect(DISTINCT s.name) as synonyms, 
               collect(DISTINCT src.name) as sources,
               count(DISTINCT m) as molecule_count
        """

        try:
            results = self.graph.run(query, parameters={"type": target_type}).data()
            return [self._format_target_result(result) for result in results]
        except Exception as e:
            self.logger.error(f"Error finding targets by type: {str(e)}")
            return []

    def find_by_source(self, source: str) -> List[Dict[str, Any]]:
        """
        Find targets from a specific source.

        Args:
            source: Source name to filter by

        Returns:
            List[Dict[str, Any]]: List of targets found
        """
        query = """
        MATCH (t:Target)-[:FROM_SOURCE]->(src:Source {name: $source})
        OPTIONAL MATCH (t)-[:HAS_SYNONYM]->(s:Synonym)
        OPTIONAL MATCH (t)-[:FROM_SOURCE]->(other_src:Source)
        OPTIONAL MATCH (t)-[:HAS_ACTIVITY]-(m:Molecule)
        RETURN t, collect(DISTINCT s.name) as synonyms, 
               collect(DISTINCT other_src.name) as sources,
               count(DISTINCT m) as molecule_count
        """

        try:
            results = self.graph.run(query, parameters={"source": source}).data()
            return [self._format_target_result(result) for result in results]
        except Exception as e:
            self.logger.error(f"Error finding targets by source: {str(e)}")
            return []

    def get_target_molecules(
        self, name: str, activity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get molecules with activity against a target.

        Args:
            name: Target name
            activity_type: Optional activity type filter (e.g., 'inhibitor', 'agonist')

        Returns:
            List[Dict[str, Any]]: List of molecules with their activity data
        """
        if activity_type:
            query = """
            MATCH (t:Target {name: $name})-[a:HAS_ACTIVITY {type: $activity_type}]-(m:Molecule)
            OPTIONAL MATCH (m)-[:HAS_SYNONYM]->(s:Synonym)
            OPTIONAL MATCH (m)-[:FROM_SOURCE]->(src:Source)
            RETURN m, collect(DISTINCT s.name) as synonyms, 
                   collect(DISTINCT src.name) as sources,
                   a.value as activity_value,
                   a.unit as activity_unit,
                   a.type as activity_type
            """
            params = {"name": name, "activity_type": activity_type}
        else:
            query = """
            MATCH (t:Target {name: $name})-[a:HAS_ACTIVITY]-(m:Molecule)
            OPTIONAL MATCH (m)-[:HAS_SYNONYM]->(s:Synonym)
            OPTIONAL MATCH (m)-[:FROM_SOURCE]->(src:Source)
            RETURN m, collect(DISTINCT s.name) as synonyms, 
                   collect(DISTINCT src.name) as sources,
                   a.value as activity_value,
                   a.unit as activity_unit,
                   a.type as activity_type
            """
            params = {"name": name}

        try:
            results = self.graph.run(query, parameters=params).data()
            return [
                self._format_molecule_result(result, include_activity=True)
                for result in results
            ]
        except Exception as e:
            self.logger.error(f"Error getting target molecules: {str(e)}")
            return []

    def link_molecule_to_target(
        self,
        target_name: str,
        molecule_id: str,
        activity_type: str,
        activity_value: float,
        activity_unit: str,
        source: str,
    ) -> bool:
        """
        Create a HAS_ACTIVITY relationship between a target and a molecule.

        Args:
            target_name: Name of the target
            molecule_id: ID of the molecule
            activity_type: Type of activity (e.g., 'IC50', 'Ki', 'EC50')
            activity_value: Numerical value of the activity
            activity_unit: Unit of the activity value (e.g., 'nM', 'µM')
            source: Source of the activity data

        Returns:
            bool: True if relationship was created successfully
        """
        query = """
        MATCH (t:Target {name: $target_name})
        MATCH (m:Molecule {id: $molecule_id})
        MERGE (t)-[a:HAS_ACTIVITY {
            type: $activity_type,
            value: $activity_value,
            unit: $activity_unit,
            source: $source
        }]-(m)
        RETURN t, m
        """

        try:
            result = self.graph.run(
                query,
                parameters={
                    "target_name": target_name,
                    "molecule_id": molecule_id,
                    "activity_type": activity_type,
                    "activity_value": activity_value,
                    "activity_unit": activity_unit,
                    "source": source,
                },
            ).data()
            success = len(result) > 0
            if success:
                self.logger.info(
                    f"Linked molecule {molecule_id} to target {target_name} "
                    f"with {activity_type} = {activity_value} {activity_unit}"
                )
            else:
                self.logger.warning(
                    f"Failed to link molecule {molecule_id} to target {target_name}"
                )
            return success
        except Exception as e:
            self.logger.error(f"Error linking molecule to target: {str(e)}")
            return False

    def _ensure_target_exists(
        self,
        name: str,
        target_type: str,
        source: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Ensure a target node exists in the database.

        Args:
            name: Name of the target
            target_type: Type of target (e.g., 'protein', 'enzyme')
            source: Source of the target data
            properties: Optional dictionary of additional target properties

        Returns:
            bool: True if target exists or was created
        """
        # Start with required properties
        target_props = {"name": name, "type": target_type, "source": source}

        # Add optional properties if provided
        if properties:
            target_props.update(properties)

        query = """
        MERGE (t:Target {name: $name})
        SET t += $properties
        WITH t
        MATCH (s:Source {name: $source})
        MERGE (t)-[:FROM_SOURCE]->(s)
        RETURN t
        """

        try:
            result = self.graph.run(
                query,
                parameters={
                    "name": name,
                    "properties": target_props,
                    "source": source,
                },
            ).data()
            return len(result) > 0
        except Exception as e:
            self.logger.error(f"Error ensuring target exists: {str(e)}")
            return False

    def _format_target_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format target query result.

        Args:
            result: Raw query result

        Returns:
            Dict[str, Any]: Formatted target data
        """
        if not result:
            return {}

        target = result["t"]
        return {
            "name": target.get("name", ""),
            "type": target.get("type", ""),
            "organism": target.get("organism", ""),
            "uniprot_id": target.get("uniprot_id", ""),
            "chembl_id": target.get("chembl_id", ""),
            "description": target.get("description", ""),
            "sequence": target.get("sequence", ""),
            "molecule_count": result.get("molecule_count", 0),
            "synonyms": result.get("synonyms", []),
            "sources": result.get("sources", []),
        }

    def _format_molecule_result(
        self, result: Dict[str, Any], include_activity: bool = False
    ) -> Dict[str, Any]:
        """
        Format molecule query result.

        Args:
            result: Raw query result
            include_activity: Whether to include activity data

        Returns:
            Dict[str, Any]: Formatted molecule data
        """
        if not result:
            return {}

        molecule = result["m"]
        formatted = {
            "id": molecule.get("id", ""),
            "name": molecule.get("name", ""),
            "formula": molecule.get("formula", ""),
            "molecular_weight": molecule.get("molecular_weight", 0.0),
            "smiles": molecule.get("smiles", ""),
            "inchi": molecule.get("inchi", ""),
            "inchikey": molecule.get("inchikey", ""),
            "pubchem_cid": molecule.get("pubchem_cid"),
            "chembl_id": molecule.get("chembl_id"),
            "logp": molecule.get("logp", 0.0),
            "polar_surface_area": molecule.get("polar_surface_area", 0.0),
            "synonyms": result.get("synonyms", []),
            "sources": result.get("sources", []),
        }

        if include_activity:
            formatted.update(
                {
                    "activity_value": result.get("activity_value"),
                    "activity_unit": result.get("activity_unit"),
                    "activity_type": result.get("activity_type"),
                }
            )

        return formatted

    def fetch_and_store_uniprot_target(
        self, uniprot_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch target information from UniProt and store it in the database.

        Args:
            uniprot_id: UniProt ID of the target

        Returns:
            Target dictionary if successful, None otherwise
        """
        try:
            # Get protein details from UniProt
            protein = self.uniprot_service.get_protein(uniprot_id)
            if not protein:
                logger.error(f"No protein found for UniProt ID: {uniprot_id}")
                return None

            # Get protein sequence
            sequence = self.uniprot_service.get_protein_sequence(uniprot_id)

            # Prepare data for Neo4j (only primitive types)
            target_data = {
                "uniprot_id": uniprot_id,
                "name": str(protein.get("protein_name", "")),
                "description": str(protein.get("function", "")),
                "organism": str(protein.get("organism", "")),
                "sequence": str(sequence) if sequence else "",
                "type": "protein",
                "gene_names": ",".join(protein.get("gene_names", [])),
                "ec_numbers": ",".join(protein.get("ec_numbers", [])),
                "pathways": ",".join(protein.get("pathways", [])),
                "diseases": ",".join(protein.get("diseases", [])),
                "chembl_ids": ",".join(protein.get("chembl_ids", [])),
                "pdb_ids": ",".join(protein.get("pdb_ids", [])),
            }

            # Store in Neo4j
            query = """
            MERGE (t:Target {uniprot_id: $uniprot_id})
            SET t += $properties
            RETURN {
                id: toString(elementId(t)),
                name: t.name,
                type: t.type,
                organism: t.organism,
                description: t.description,
                uniprot_id: t.uniprot_id,
                sequence: t.sequence,
                gene_names: t.gene_names,
                ec_numbers: t.ec_numbers,
                pathways: t.pathways,
                diseases: t.diseases,
                chembl_ids: t.chembl_ids,
                pdb_ids: t.pdb_ids
            } as target
            """
            result = self.graph.run(
                query, uniprot_id=uniprot_id, properties=target_data
            ).data()

            if result:
                target = result[0]["target"]
                # Convert comma-separated strings back to lists for the response
                target["gene_names"] = (
                    target["gene_names"].split(",") if target["gene_names"] else []
                )
                target["ec_numbers"] = (
                    target["ec_numbers"].split(",") if target["ec_numbers"] else []
                )
                target["pathways"] = (
                    target["pathways"].split(",") if target["pathways"] else []
                )
                target["diseases"] = (
                    target["diseases"].split(",") if target["diseases"] else []
                )
                target["chembl_ids"] = (
                    target["chembl_ids"].split(",") if target["chembl_ids"] else []
                )
                target["pdb_ids"] = (
                    target["pdb_ids"].split(",") if target["pdb_ids"] else []
                )
                return target

            return None

        except Exception as e:
            logger.error(
                f"Error fetching and storing UniProt target {uniprot_id}: {str(e)}"
            )
            return None

    def create_target(self, target_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new target in the database.

        Args:
            target_data: Dictionary containing target information

        Returns:
            Created target data if successful, None otherwise
        """
        try:
            # Validate required fields
            required_fields = ["uniprot_id", "protein_name", "organism"]
            if not all(field in target_data for field in required_fields):
                logger.error(f"Missing required fields: {required_fields}")
                return None

            # Create target node with properties
            query = """
            MERGE (t:Target {uniprot_id: $uniprot_id})
            ON CREATE SET 
                t.name = $protein_name,
                t.type = 'protein',
                t.organism = $organism,
                t.function = $function,
                t.created_at = datetime(),
                t.updated_at = datetime()
            ON MATCH SET 
                t.name = $protein_name,
                t.type = 'protein',
                t.organism = $organism,
                t.function = $function,
                t.updated_at = datetime()
            RETURN t
            """

            result = self.graph.run(
                query,
                uniprot_id=target_data["uniprot_id"],
                protein_name=target_data["protein_name"],
                organism=target_data["organism"],
                function=target_data.get("function", ""),
            ).data()

            if not result:
                logger.error("Failed to create target")
                return None

            # Create relationships for additional data
            if target_data.get("ec_numbers"):
                self._create_ec_number_relationships(
                    target_data["uniprot_id"], target_data["ec_numbers"]
                )

            if target_data.get("pathways"):
                self._create_pathway_relationships(
                    target_data["uniprot_id"], target_data["pathways"]
                )

            if target_data.get("diseases"):
                self._create_disease_relationships(
                    target_data["uniprot_id"], target_data["diseases"]
                )

            return {
                "id": target_data["uniprot_id"],
                "name": target_data["protein_name"],
                "type": "protein",
                "organism": target_data["organism"],
                "function": target_data.get("function", ""),
                "ec_numbers": target_data.get("ec_numbers", []),
                "pathways": target_data.get("pathways", []),
                "diseases": target_data.get("diseases", []),
            }

        except Exception as e:
            logger.error(f"Error creating target: {str(e)}")
            return None

    def _create_ec_number_relationships(
        self, uniprot_id: str, ec_numbers: List[str]
    ) -> None:
        """Create relationships between a target and its EC numbers.

        Args:
            uniprot_id: UniProt ID of the target
            ec_numbers: List of EC numbers
        """
        query = """
        MATCH (t:Target {uniprot_id: $uniprot_id})
        UNWIND $ec_numbers as ec
        MERGE (e:ECNumber {number: ec})
        MERGE (t)-[:HAS_EC_NUMBER]->(e)
        """
        self.graph.run(query, uniprot_id=uniprot_id, ec_numbers=ec_numbers)

    def _create_pathway_relationships(
        self, uniprot_id: str, pathways: List[str]
    ) -> None:
        """Create relationships between a target and its pathways.

        Args:
            uniprot_id: UniProt ID of the target
            pathways: List of pathway names
        """
        query = """
        MATCH (t:Target {uniprot_id: $uniprot_id})
        UNWIND $pathways as pathway
        MERGE (p:Pathway {name: pathway})
        MERGE (t)-[:INVOLVED_IN]->(p)
        """
        self.graph.run(query, uniprot_id=uniprot_id, pathways=pathways)

    def _create_disease_relationships(
        self, uniprot_id: str, diseases: List[str]
    ) -> None:
        """Create relationships between a target and its associated diseases.

        Args:
            uniprot_id: UniProt ID of the target
            diseases: List of disease names
        """
        query = """
        MATCH (t:Target {uniprot_id: $uniprot_id})
        UNWIND $diseases as disease
        MERGE (d:Disease {name: disease})
        MERGE (t)-[:ASSOCIATED_WITH]->(d)
        """
        self.graph.run(query, uniprot_id=uniprot_id, diseases=diseases)

    def check_drugbank_associations(self, uniprot_id: str) -> List[str]:
        """
        Check for DrugBank associations in the Chemistry section of UniProt.

        Args:
            uniprot_id: UniProt ID of the target

        Returns:
            List[str]: List of DrugBank IDs associated with this target
        """
        try:
            # Query to find molecules with DrugBank IDs
            query = """
            MATCH (m:Molecule)
            WHERE m.drugbank_id IS NOT NULL
            RETURN m.drugbank_id as drugbank_id
            """

            result = self.graph.run(query).data()
            drugbank_ids = [r["drugbank_id"] for r in result if r["drugbank_id"]]

            if not drugbank_ids:
                return []

            # Get UniProt data for the target
            uniprot_service = UniProtService()
            target_data = uniprot_service.get_protein(uniprot_id)

            if not target_data or "chemistry" not in target_data:
                return []

            # Extract DrugBank IDs from chemistry section that match our molecules
            chemistry = target_data["chemistry"]
            matching_drugbank_ids = []

            for entry in chemistry:
                if "drugbank_id" in entry and entry["drugbank_id"] in drugbank_ids:
                    matching_drugbank_ids.append(entry["drugbank_id"])

            return matching_drugbank_ids

        except Exception as e:
            self.logger.error(f"Error checking DrugBank associations: {str(e)}")
            return []

    def create_target_associations(
        self, target_id: str, drugbank_ids: List[str]
    ) -> bool:
        """
        Create associations between a target and molecules based on DrugBank IDs.

        Args:
            target_id: ID of the target
            drugbank_ids: List of DrugBank IDs to associate with

        Returns:
            bool: True if associations were created successfully
        """
        try:
            # Create relationships for each matching DrugBank ID
            query = """
            MATCH (t:Target)
            WHERE toString(elementId(t)) ENDS WITH $target_id
            WITH t
            UNWIND $drugbank_ids as drugbank_id
            MATCH (m:Molecule {drugbank_id: drugbank_id})
            MERGE (m)-[r:INTERACTS_WITH]->(t)
            SET r.source = 'DrugBank',
                r.confidence_score = 0.9
            RETURN count(r) as rel_count
            """

            result = self.graph.run(
                query, target_id=target_id, drugbank_ids=drugbank_ids
            ).data()
            return len(result) > 0 and result[0]["rel_count"] > 0

        except Exception as e:
            self.logger.error(f"Error creating target associations: {str(e)}")
            return False
