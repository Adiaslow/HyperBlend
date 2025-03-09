"""Service for querying organisms from the internal database."""

import logging
from typing import List, Optional, Dict, Any
from py2neo import Graph, NodeMatcher

from .base_service import BaseInternalService


class OrganismService(BaseInternalService):
    """Service for querying organisms from the database."""

    def __init__(self, graph: Graph):
        """
        Initialize the organism service.

        Args:
            graph: Neo4j graph database connection
        """
        super().__init__(graph)
        self.matcher = NodeMatcher(graph)

    def find_by_name(self, name: str, exact: bool = False) -> List[Dict[str, Any]]:
        """
        Find organisms by name.

        Args:
            name: Name to search for
            exact: Whether to perform exact match (default: False)

        Returns:
            List[Dict[str, Any]]: List of organisms found
        """
        if exact:
            query = """
            MATCH (o:Organism {name: $name})
            OPTIONAL MATCH (o)-[:FROM_SOURCE]->(src:Source)
            OPTIONAL MATCH (o)-[:PRODUCES]->(m:Molecule)
            RETURN o, collect(DISTINCT src.name) as sources, count(DISTINCT m) as molecule_count
            """
        else:
            query = """
            MATCH (o:Organism)
            WHERE o.name =~ $pattern
            OPTIONAL MATCH (o)-[:FROM_SOURCE]->(src:Source)
            OPTIONAL MATCH (o)-[:PRODUCES]->(m:Molecule)
            RETURN o, collect(DISTINCT src.name) as sources, count(DISTINCT m) as molecule_count
            """

        try:
            pattern = f"(?i).*{name}.*"  # Case-insensitive pattern
            results = self.graph.run(
                query, parameters={"name": name, "pattern": pattern}
            ).data()

            return [self._format_organism_result(result) for result in results]
        except Exception as e:
            self.logger.error(f"Error finding organisms by name: {str(e)}")
            return []

    def find_by_rank(self, rank: str) -> List[Dict[str, Any]]:
        """
        Find organisms by taxonomic rank.

        Args:
            rank: Taxonomic rank to filter by

        Returns:
            List[Dict[str, Any]]: List of organisms found
        """
        query = """
        MATCH (o:Organism {rank: $rank})
        OPTIONAL MATCH (o)-[:FROM_SOURCE]->(src:Source)
        OPTIONAL MATCH (o)-[:PRODUCES]->(m:Molecule)
        RETURN o, collect(DISTINCT src.name) as sources, count(DISTINCT m) as molecule_count
        """

        try:
            results = self.graph.run(query, parameters={"rank": rank}).data()
            return [self._format_organism_result(result) for result in results]
        except Exception as e:
            self.logger.error(f"Error finding organisms by rank: {str(e)}")
            return []

    def find_by_source(self, source: str) -> List[Dict[str, Any]]:
        """
        Find organisms from a specific source.

        Args:
            source: Source name to filter by

        Returns:
            List[Dict[str, Any]]: List of organisms found
        """
        query = """
        MATCH (o:Organism)-[:FROM_SOURCE]->(src:Source {name: $source})
        OPTIONAL MATCH (o)-[:FROM_SOURCE]->(other_src:Source)
        OPTIONAL MATCH (o)-[:PRODUCES]->(m:Molecule)
        RETURN o, collect(DISTINCT other_src.name) as sources, count(DISTINCT m) as molecule_count
        """

        try:
            results = self.graph.run(query, parameters={"source": source}).data()
            return [self._format_organism_result(result) for result in results]
        except Exception as e:
            self.logger.error(f"Error finding organisms by source: {str(e)}")
            return []

    def get_organism_molecules(self, name: str) -> List[Dict[str, Any]]:
        """
        Get molecules produced by an organism.

        Args:
            name: Organism name

        Returns:
            List[Dict[str, Any]]: List of molecules found
        """
        query = """
        MATCH (o:Organism {name: $name})-[:PRODUCES]->(m:Molecule)
        OPTIONAL MATCH (m)-[:HAS_SYNONYM]->(s:Synonym)
        OPTIONAL MATCH (m)-[:FROM_SOURCE]->(src:Source)
        RETURN m, collect(DISTINCT s.name) as synonyms, collect(DISTINCT src.name) as sources
        """

        try:
            results = self.graph.run(query, parameters={"name": name}).data()
            return [self._format_molecule_result(result) for result in results]
        except Exception as e:
            self.logger.error(f"Error getting organism molecules: {str(e)}")
            return []

    def _ensure_source_exists(self, source: str) -> bool:
        """
        Ensure a source node exists in the database.

        Args:
            source: Name of the source

        Returns:
            bool: True if source exists or was created
        """
        query = """
        MERGE (s:Source {name: $source})
        RETURN s
        """

        try:
            result = self.graph.run(query, parameters={"source": source}).data()
            return len(result) > 0
        except Exception as e:
            self.logger.error(f"Error ensuring source exists: {str(e)}")
            return False

    def _ensure_molecule_exists(
        self, molecule_id: str, source: str, properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Ensure a molecule node exists in the database.

        Args:
            molecule_id: ID of the molecule
            source: Source of the molecule
            properties: Optional dictionary of molecule properties

        Returns:
            bool: True if molecule exists or was created
        """
        # Start with required properties
        molecule_props = {"id": molecule_id, "source": source}

        # Add optional properties if provided
        if properties:
            for key in [
                "name",
                "formula",
                "molecular_weight",
                "smiles",
                "inchi",
                "inchikey",
                "pubchem_cid",
                "chembl_id",
                "logp",
                "polar_surface_area",
            ]:
                if key in properties:
                    molecule_props[key] = properties[key]

        query = """
        MERGE (m:Molecule {id: $molecule_id})
        SET m += $properties
        WITH m
        MATCH (s:Source {name: $source})
        MERGE (m)-[:FROM_SOURCE]->(s)
        RETURN m
        """

        try:
            result = self.graph.run(
                query,
                parameters={
                    "molecule_id": molecule_id,
                    "properties": molecule_props,
                    "source": source,
                },
            ).data()
            return len(result) > 0
        except Exception as e:
            self.logger.error(f"Error ensuring molecule exists: {str(e)}")
            return False

    def link_molecule_to_organism(
        self,
        organism_name: str,
        molecule_id: str,
        source: str,
        molecule_properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Create a PRODUCES relationship between an organism and a molecule.

        Args:
            organism_name: Name of the organism
            molecule_id: ID of the molecule
            source: Source of the relationship (e.g., 'COCONUT')
            molecule_properties: Optional dictionary of molecule properties

        Returns:
            bool: True if relationship was created successfully
        """
        # Ensure source and molecule exist
        if not self._ensure_source_exists(source):
            return False
        if not self._ensure_molecule_exists(molecule_id, source, molecule_properties):
            return False

        query = """
        MATCH (o:Organism {name: $organism_name})
        MATCH (m:Molecule {id: $molecule_id})
        MERGE (o)-[:PRODUCES {source: $source}]->(m)
        RETURN o, m
        """

        try:
            result = self.graph.run(
                query,
                parameters={
                    "organism_name": organism_name,
                    "molecule_id": molecule_id,
                    "source": source,
                },
            ).data()
            success = len(result) > 0
            if success:
                self.logger.info(
                    f"Linked molecule {molecule_id} to organism {organism_name}"
                )
            else:
                self.logger.warning(
                    f"Failed to link molecule {molecule_id} to organism {organism_name}"
                )
            return success
        except Exception as e:
            self.logger.error(f"Error linking molecule to organism: {str(e)}")
            return False

    def link_molecules_to_organism(
        self,
        organism_name: str,
        molecule_ids: List[str],
        source: str,
        molecule_properties: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> int:
        """
        Create PRODUCES relationships between an organism and multiple molecules.

        Args:
            organism_name: Name of the organism
            molecule_ids: List of molecule IDs
            source: Source of the relationships (e.g., 'COCONUT')
            molecule_properties: Optional dictionary mapping molecule IDs to their properties

        Returns:
            int: Number of relationships created successfully
        """
        success_count = 0
        for molecule_id in molecule_ids:
            props = (
                molecule_properties.get(molecule_id) if molecule_properties else None
            )
            if self.link_molecule_to_organism(
                organism_name, molecule_id, source, props
            ):
                success_count += 1

        self.logger.info(
            f"Linked {success_count}/{len(molecule_ids)} molecules to {organism_name}"
        )
        return success_count

    def _format_organism_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format organism query result.

        Args:
            result: Raw query result

        Returns:
            Dict[str, Any]: Formatted organism data
        """
        if not result:
            return {}

        organism = result["o"]
        return {
            "name": organism.get("name", ""),
            "rank": organism.get("rank", ""),
            "iri": organism.get("iri", ""),
            "molecule_count": result.get("molecule_count", 0),
            "sources": result.get("sources", []),
        }

    def _format_molecule_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format molecule query result.

        Args:
            result: Raw query result

        Returns:
            Dict[str, Any]: Formatted molecule data
        """
        if not result:
            return {}

        molecule = result["m"]
        return {
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
