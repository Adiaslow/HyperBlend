"""Service for querying molecules from the internal database."""

import logging
from typing import List, Optional, Dict, Any
from py2neo import Graph, NodeMatcher

from hyperblend.models.molecule import Molecule
from .base_service import BaseInternalService
from hyperblend.services.external.pubchem_service import PubChemService
from hyperblend.services.external.chembl_service import ChEMBLService
from hyperblend.services.external.drugbank_service import DrugBankService


class MoleculeService(BaseInternalService):
    """Service for querying molecules from the database."""

    def __init__(self, graph: Graph, drugbank_api_key: Optional[str] = None):
        """
        Initialize the molecule service.

        Args:
            graph: Neo4j graph database connection
            drugbank_api_key: Optional DrugBank API key
        """
        # Call parent class constructor first
        super().__init__(graph)

        # Initialize service-specific attributes
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
        Get a molecule by ID.

        Args:
            molecule_id: The molecule ID in format 'database:uuid:number'

        Returns:
            Optional[Dict[str, Any]]: Molecule data if found, None otherwise
        """
        try:
            # Extract the numeric ID from the full element ID format
            id_parts = molecule_id.split(":")
            if len(id_parts) != 3:
                self.logger.error(f"Invalid molecule ID format: {molecule_id}")
                return None

            numeric_id = id_parts[2]  # Get the last part which is the numeric ID

            # Query to get molecule details
            cypher_query = """
            MATCH (m:Molecule)
            WHERE toString(elementId(m)) ENDS WITH $numeric_id
            WITH m
            OPTIONAL MATCH (m)-[:HAS_SYNONYM]->(s:Synonym)
            WITH m, collect(DISTINCT s.name) as synonyms
            RETURN {
                id: toString(elementId(m)),
                name: m.name,
                description: m.description,
                formula: m.formula,
                molecular_weight: m.molecular_weight,
                smiles: m.smiles,
                inchi: m.inchi,
                inchikey: m.inchikey,
                logp: m.logp,
                polar_surface_area: m.polar_surface_area,
                pubchem_cid: m.pubchem_cid,
                chembl_id: m.chembl_id,
                synonyms: synonyms,
                source: m.source
            } as molecule
            """

            # Execute query and get result
            result = self.graph.run(cypher_query, numeric_id=numeric_id).data()

            if not result:
                self.logger.warning(f"No molecule found with ID: {molecule_id}")
                return None

            molecule_data = result[0].get("molecule")
            if not molecule_data:
                self.logger.error(
                    f"Unexpected query result format for molecule ID: {molecule_id}"
                )
                return None

            return molecule_data

        except Exception as e:
            self.logger.error(f"Error getting molecule: {str(e)}")
            raise

    def get_all_molecules(self) -> List[Dict[str, Any]]:
        """Get all molecules."""
        query = """
        MATCH (m:Molecule)
        RETURN m
        """
        results = self.graph.run(query)
        return [
            {
                "id": str(result["m"].id),
                "name": result["m"]["name"],
                "smiles": result["m"].get("smiles"),
                "description": result["m"].get("description"),
                "source": result["m"].get("source"),
            }
            for result in results
        ]

    def search_molecules(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for molecules by name or description."""
        query = """
        MATCH (m:Molecule)
        WHERE toLower(m.name) CONTAINS toLower($search_term)
           OR toLower(coalesce(m.description, '')) CONTAINS toLower($search_term)
        OPTIONAL MATCH (m)-[:FROM_ORGANISM]->(o:Organism)
        RETURN m,
               collect(DISTINCT o.name) as organisms
        """
        results = self.graph.run(query, search_term=search_term)
        return [
            {
                "id": str(result["m"].id),
                "name": result["m"]["name"],
                "smiles": result["m"].get("smiles"),
                "description": result["m"].get("description"),
                "organisms": result["organisms"],
            }
            for result in results
        ]

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

    def update_molecule(self, molecule_id: str, enriched_data: Molecule) -> bool:
        """
        Update a molecule with enriched data.

        Args:
            molecule_id: The molecule ID in format 'database:uuid:number'
            enriched_data: The enriched molecule data

        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Extract the numeric ID from the full element ID format
            id_parts = molecule_id.split(":")
            if len(id_parts) != 3:
                self.logger.error(f"Invalid molecule ID format: {molecule_id}")
                return False

            numeric_id = id_parts[2]  # Get the last part which is the numeric ID

            # Prepare update data
            update_data = {
                "name": enriched_data.name,
                "formula": enriched_data.formula,
                "molecular_weight": enriched_data.molecular_weight,
                "smiles": enriched_data.smiles,
                "inchi": enriched_data.inchi,
                "inchikey": enriched_data.inchikey,
                "pubchem_cid": enriched_data.pubchem_cid,
                "chembl_id": enriched_data.chembl_id,
                "logp": enriched_data.logp,
                "polar_surface_area": enriched_data.polar_surface_area,
            }

            # Update query
            cypher_query = """
            MATCH (m:Molecule)
            WHERE toString(elementId(m)) ENDS WITH $numeric_id
            SET m += $update_data
            RETURN m
            """

            result = self.graph.run(
                cypher_query, numeric_id=numeric_id, update_data=update_data
            ).data()
            return len(result) > 0

        except Exception as e:
            self.logger.error(f"Error updating molecule: {str(e)}")
            return False

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
