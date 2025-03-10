"""Service for querying molecules from the internal database."""

import logging
from typing import List, Optional, Dict, Any
from py2neo import Graph, NodeMatcher
from hyperblend.app.web.core.exceptions import ResourceNotFoundError
from .base_service import BaseService

from hyperblend.models.molecule import Molecule
from hyperblend.services.external.pubchem_service import PubChemService
from hyperblend.services.external.chembl_service import ChEMBLService
from hyperblend.services.external.drugbank_service import DrugBankService

logger = logging.getLogger(__name__)

class MoleculeService(BaseService):
    """Service for querying molecules from the database."""

    def __init__(self, graph: Graph, drugbank_api_key: Optional[str] = None):
        """
        Initialize the molecule service.

        Args:
            graph: Neo4j graph database connection
            drugbank_api_key: Optional DrugBank API key
        """
        super().__init__(graph)
        self.matcher = NodeMatcher(graph)
        self.pubchem_service = PubChemService(graph)
        self.chembl_service = ChEMBLService(graph)
        self.drugbank_service = (
            DrugBankService(api_key=drugbank_api_key, graph=graph)
            if drugbank_api_key
            else None
        )

    def find_by_name(self, name: str, exact: bool = False) -> List[Dict[str, Any]]:
        """
        Find molecules by name.

        Args:
            name: Name to search for
            exact: Whether to perform exact match (default: False)

        Returns:
            List[Dict[str, Any]]: List of molecules found
        """
        if exact:
            query = """
            MATCH (m:Molecule {name: $name})
            OPTIONAL MATCH (m)-[:HAS_SYNONYM]->(s:Synonym)
            OPTIONAL MATCH (m)-[:FROM_SOURCE]->(src:Source)
            RETURN m, collect(DISTINCT s.name) as synonyms, collect(DISTINCT src.name) as sources
            """
        else:
            query = """
            MATCH (m:Molecule)
            WHERE m.name =~ $pattern
            OPTIONAL MATCH (m)-[:HAS_SYNONYM]->(s:Synonym)
            OPTIONAL MATCH (m)-[:FROM_SOURCE]->(src:Source)
            RETURN m, collect(DISTINCT s.name) as synonyms, collect(DISTINCT src.name) as sources
            """

        try:
            pattern = f"(?i).*{name}.*"  # Case-insensitive pattern
            results = self.graph.run(
                query, parameters={"name": name, "pattern": pattern}
            ).data()

            return [self._format_molecule_result(result) for result in results]
        except Exception as e:
            self.logger.error(f"Error finding molecules by name: {str(e)}")
            return []

    def find_by_inchikey(self, inchikey: str) -> Optional[Dict[str, Any]]:
        """
        Find molecule by InChIKey.

        Args:
            inchikey: InChIKey to search for

        Returns:
            Optional[Dict[str, Any]]: Molecule if found, None otherwise
        """
        query = """
        MATCH (m:Molecule {inchikey: $inchikey})
        OPTIONAL MATCH (m)-[:HAS_SYNONYM]->(s:Synonym)
        OPTIONAL MATCH (m)-[:FROM_SOURCE]->(src:Source)
        RETURN m, collect(DISTINCT s.name) as synonyms, collect(DISTINCT src.name) as sources
        """

        try:
            result = self.graph.run(query, parameters={"inchikey": inchikey}).data()
            return self._format_molecule_result(result[0]) if result else None
        except Exception as e:
            self.logger.error(f"Error finding molecule by InChIKey: {str(e)}")
            return None

    def find_by_source(self, source: str) -> List[Dict[str, Any]]:
        """
        Find molecules from a specific source.

        Args:
            source: Source name to filter by

        Returns:
            List[Dict[str, Any]]: List of molecules found
        """
        query = """
        MATCH (m:Molecule)-[:FROM_SOURCE]->(src:Source {name: $source})
        OPTIONAL MATCH (m)-[:HAS_SYNONYM]->(s:Synonym)
        OPTIONAL MATCH (m)-[:FROM_SOURCE]->(other_src:Source)
        RETURN m, collect(DISTINCT s.name) as synonyms, collect(DISTINCT other_src.name) as sources
        """

        try:
            results = self.graph.run(query, parameters={"source": source}).data()
            return [self._format_molecule_result(result) for result in results]
        except Exception as e:
            self.logger.error(f"Error finding molecules by source: {str(e)}")
            return []

    def find_similar_molecules(
        self, inchikey: str, threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Find molecules similar to the given one based on properties.

        Args:
            inchikey: InChIKey of the reference molecule
            threshold: Similarity threshold (0-1, default: 0.7)

        Returns:
            List[Dict[str, Any]]: List of similar molecules
        """
        query = """
        MATCH (ref:Molecule {inchikey: $inchikey})
        MATCH (m:Molecule)
        WHERE m.inchikey <> ref.inchikey
        WITH ref, m,
             (
                CASE WHEN ref.molecular_weight > 0 AND m.molecular_weight > 0
                THEN 1 - abs(ref.molecular_weight - m.molecular_weight) / (ref.molecular_weight + m.molecular_weight)
                ELSE 0 END +
                CASE WHEN ref.logp IS NOT NULL AND m.logp IS NOT NULL
                THEN 1 - abs(ref.logp - m.logp) / (abs(ref.logp) + abs(m.logp) + 1)
                ELSE 0 END +
                CASE WHEN ref.polar_surface_area > 0 AND m.polar_surface_area > 0
                THEN 1 - abs(ref.polar_surface_area - m.polar_surface_area) / (ref.polar_surface_area + m.polar_surface_area)
                ELSE 0 END
             ) / 3.0 as similarity
        WHERE similarity >= $threshold
        OPTIONAL MATCH (m)-[:HAS_SYNONYM]->(s:Synonym)
        OPTIONAL MATCH (m)-[:FROM_SOURCE]->(src:Source)
        RETURN m, collect(DISTINCT s.name) as synonyms, collect(DISTINCT src.name) as sources, similarity
        ORDER BY similarity DESC
        """

        try:
            results = self.graph.run(
                query, parameters={"inchikey": inchikey, "threshold": threshold}
            ).data()
            return [
                self._format_molecule_result(result, include_similarity=True)
                for result in results
            ]
        except Exception as e:
            self.logger.error(f"Error finding similar molecules: {str(e)}")
            return []

    def _format_molecule_result(
        self, result: Dict[str, Any], include_similarity: bool = False
    ) -> Dict[str, Any]:
        """
        Format molecule query result.

        Args:
            result: Raw query result
            include_similarity: Whether to include similarity score

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

        if include_similarity:
            formatted["similarity"] = result.get("similarity", 0.0)

        return formatted

    def get_molecule(self, molecule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific molecule by ID.

        Args:
            molecule_id: The ID of the molecule to retrieve

        Returns:
            Dictionary containing molecule details and relationships
        """
        try:
            cypher_query = """
            MATCH (m:Molecule)
            WHERE elementId(m) = $molecule_id
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
                confidence_score: r.confidence_score
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
            result = self.run_query(cypher_query, {"molecule_id": self._validate_id(molecule_id)})
            return result[0]["molecule"] if result else None
        except Exception as e:
            self._handle_db_error(e, f"getting molecule {molecule_id}")

    def get_all_molecules(self) -> List[Dict[str, Any]]:
        """
        Get all molecules.

        Returns:
            List of dictionaries containing molecule details
        """
        try:
            cypher_query = """
            MATCH (m:Molecule)
            RETURN {
                id: toString(elementId(m)),
                name: m.name,
                formula: m.formula,
                smiles: m.smiles,
                molecular_weight: m.molecular_weight
            } as molecule
            """
            result = self.run_query(cypher_query)
            return [r["molecule"] for r in result]
        except Exception as e:
            self._handle_db_error(e, "getting all molecules")

    def search_molecules(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for molecules by name, formula, or SMILES.

        Args:
            query: Search query string

        Returns:
            List of dictionaries containing matching molecule details
        """
        try:
            cypher_query = """
            MATCH (m:Molecule)
            WHERE m.name =~ $query 
               OR m.formula =~ $query 
               OR m.smiles =~ $query
            RETURN {
                id: toString(elementId(m)),
                name: m.name,
                formula: m.formula,
                smiles: m.smiles,
                molecular_weight: m.molecular_weight
            } as molecule
            """
            result = self.run_query(cypher_query, {"query": f"(?i).*{query}.*"})
            return [r["molecule"] for r in result]
        except Exception as e:
            self._handle_db_error(e, f"searching molecules with query {query}")

    def create_molecule(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new molecule.

        Args:
            data: Dictionary containing molecule properties

        Returns:
            Dictionary containing created molecule details
        """
        try:
            cypher_query = """
            CREATE (m:Molecule)
            SET m += $data
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
                polar_surface_area: m.polar_surface_area
            } as molecule
            """
            result = self.run_query(cypher_query, {"data": data})
            return result[0]["molecule"] if result else None
        except Exception as e:
            self._handle_db_error(e, "creating molecule")

    def update_molecule(self, molecule_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing molecule.

        Args:
            molecule_id: ID of the molecule to update
            data: Dictionary containing updated molecule properties

        Returns:
            Dictionary containing updated molecule details
        """
        try:
            cypher_query = """
            MATCH (m:Molecule)
            WHERE elementId(m) = $molecule_id
            SET m += $data
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
                polar_surface_area: m.polar_surface_area
            } as molecule
            """
            result = self.run_query(cypher_query, {
                "molecule_id": self._validate_id(molecule_id),
                "data": data
            })
            return result[0]["molecule"] if result else None
        except Exception as e:
            self._handle_db_error(e, f"updating molecule {molecule_id}")

    def delete_molecule(self, molecule_id: str) -> bool:
        """
        Delete a molecule.

        Args:
            molecule_id: ID of the molecule to delete

        Returns:
            True if deletion was successful
        """
        try:
            cypher_query = """
            MATCH (m:Molecule)
            WHERE elementId(m) = $molecule_id
            DETACH DELETE m
            """
            self.run_query(cypher_query, {"molecule_id": self._validate_id(molecule_id)})
            return True
        except Exception as e:
            self._handle_db_error(e, f"deleting molecule {molecule_id}")
            return False

    def enrich_molecule(self, molecule_id: str, database: str, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Enrich a molecule with data from external databases.

        Args:
            molecule_id: ID of the molecule to enrich
            database: Name of the external database (e.g., "pubchem", "chembl")
            identifier: Identifier in the external database

        Returns:
            Dictionary containing enriched molecule details
        """
        try:
            # First verify the molecule exists
            molecule = self.get_molecule(molecule_id)
            if not molecule:
                raise ResourceNotFoundError(f"Molecule {molecule_id} not found")

            # Get properties based on database type
            if database == "pubchem":
                properties = self._get_pubchem_properties(identifier)
            elif database == "chembl":
                properties = self._get_chembl_properties(identifier)
            else:
                raise ValueError(f"Unsupported database: {database}")

            # Update molecule with new properties
            cypher_query = """
            MATCH (m:Molecule)
            WHERE elementId(m) = $molecule_id
            SET m += $properties
            WITH m
            OPTIONAL MATCH (m)-[r]-(related)
            WHERE (related:Target OR related:Organism)
            WITH m, collect(DISTINCT {
                id: toString(elementId(related)),
                name: related.name,
                type: labels(related)[0],
                relationship_type: type(r)
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
                relationships: relationships,
                enriched_from: $database
            } as molecule
            """
            result = self.run_query(cypher_query, {
                "molecule_id": self._validate_id(molecule_id),
                "properties": properties,
                "database": database
            })
            return result[0]["molecule"] if result else None
        except Exception as e:
            self._handle_db_error(e, f"enriching molecule {molecule_id}")

    def _get_pubchem_properties(self, cid: str) -> Dict[str, Any]:
        """Get molecule properties from PubChem."""
        # This would typically call the PubChem API
        # For now, return placeholder data
        return {
            "pubchem_cid": cid,
            "data_source": "PubChem"
        }

    def _get_chembl_properties(self, chembl_id: str) -> Dict[str, Any]:
        """Get molecule properties from ChEMBL."""
        # This would typically call the ChEMBL API
        # For now, return placeholder data
        return {
            "chembl_id": chembl_id,
            "data_source": "ChEMBL"
        }

    def create_molecule_from_pubchem(self, identifier: str) -> Optional[Molecule]:
        """
        Create a molecule from PubChem data.

        Args:
            identifier: PubChem identifier (CID, SMILES, or name)

        Returns:
            Optional[Molecule]: Created molecule if successful
        """
        try:
            # Try to convert to CID if it's a numeric string
            if identifier.isdigit():
                molecule = self.pubchem_service.get_molecule_by_cid(int(identifier))
            elif identifier.startswith("C") and identifier[1:].isdigit():
                # Handle CID with 'C' prefix
                molecule = self.pubchem_service.get_molecule_by_cid(int(identifier[1:]))
            elif all(c in "CN()O123456789" for c in identifier):
                # Likely a SMILES string
                molecule = self.pubchem_service.search_molecule_by_smiles(identifier)
            else:
                # Try name search
                molecules = self.pubchem_service.search_molecule_by_name(identifier)
                molecule = molecules[0] if molecules else None

            return molecule
        except Exception as e:
            self.logger.error(
                f"Error creating molecule from PubChem {identifier}: {str(e)}"
            )
            return None

    def create_molecule_from_drugbank(self, drugbank_id: str) -> Optional[Molecule]:
        """
        Create a molecule from DrugBank data.

        Args:
            drugbank_id: DrugBank identifier

        Returns:
            Optional[Molecule]: Created molecule if successful, None otherwise
        """
        try:
            molecule = self.drugbank_service.get_molecule_by_drugbank_id(drugbank_id)
            if molecule:
                self.db_manager.create_or_update_molecule(
                    molecule=molecule, source="DrugBank"
                )
                return molecule
            return None
        except Exception as e:
            self.logger.error(f"Error creating molecule from DrugBank: {str(e)}")
            return None

    def get_molecule_from_drugbank(self, drugbank_id: str) -> Optional[Dict[str, Any]]:
        """
        Get molecule data from DrugBank.

        Args:
            drugbank_id: DrugBank ID

        Returns:
            Optional[Dict[str, Any]]: Molecule data if found, None otherwise
        """
        if not self.drugbank_service:
            self.logger.warning("DrugBank service is not available - missing API key")
            return None

        try:
            return self.drugbank_service.get_molecule_by_drugbank_id(drugbank_id)
        except Exception as e:
            self.logger.error(f"Error getting molecule from DrugBank: {str(e)}")
            return None

    def enrich_from_drugbank(self, molecule_id: str, drugbank_id: str) -> bool:
        """
        Enrich molecule data from DrugBank.

        Args:
            molecule_id: Internal molecule ID
            drugbank_id: DrugBank ID

        Returns:
            bool: True if enrichment was successful, False otherwise
        """
        if not self.drugbank_service:
            self.logger.warning("DrugBank service is not available - missing API key")
            return False

        try:
            drugbank_data = self.drugbank_service.get_molecule_by_drugbank_id(
                drugbank_id
            )
            if not drugbank_data:
                return False

            # Update molecule with DrugBank data
            return self.update_molecule(molecule_id, drugbank_data)
        except Exception as e:
            self.logger.error(f"Error enriching molecule from DrugBank: {str(e)}")
            return False
