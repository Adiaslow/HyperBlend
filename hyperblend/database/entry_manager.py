"""Database entry manager for handling molecule entries from various services."""

import logging
from typing import List, Optional, Dict, Any, Set, cast
from py2neo import Graph, Node, Relationship, NodeMatcher
from hyperblend.models.molecule import Molecule
from hyperblend.models.target import Target
from hyperblend.models.database.molecule import (
    MoleculeDB,
    OrganismDB,
    TargetDB,
)


class DatabaseEntryManager:
    """Manager for handling database entries from various services."""

    def __init__(self, graph: Graph):
        """
        Initialize the database entry manager.

        Args:
            graph: Neo4j graph database connection
        """
        self.graph = graph
        self.matcher = NodeMatcher(graph)
        self.logger = logging.getLogger(__name__)

    def create_or_update_molecule(self, molecule: Molecule, source: str) -> MoleculeDB:
        """
        Create or update a molecule in the database.

        Args:
            molecule: Molecule object to create/update
            source: Source of the molecule data (e.g., 'PubChem', 'ChEMBL', 'COCONUT')

        Returns:
            MoleculeDB: Created or updated molecule database object
        """
        # Check if molecule already exists
        existing = self.graph.nodes.match(
            "Molecule", inchikey=molecule.inchikey
        ).first()

        if existing:
            return self._update_molecule(existing, molecule, source)
        return self._create_molecule(molecule, source)

    def add_or_update_organism(
        self, name: str, rank: str, iri: str, molecule_count: int, source: str
    ) -> Node:
        """
        Add a new organism or update existing one in the database.

        Args:
            name: Organism name
            rank: Taxonomic rank
            iri: IRI identifier
            molecule_count: Number of associated molecules
            source: Source of the organism data

        Returns:
            Node: Database organism node
        """
        try:
            # Check for existing organism by IRI
            existing = self.graph.nodes.match("Organism", iri=iri).first()

            if existing:
                # Update existing organism
                self.logger.info(f"Updating existing organism: {existing['iri']}")
                existing.update(
                    {
                        "name": name,
                        "rank": rank,
                        "molecule_count": molecule_count,
                    }
                )
                self.graph.push(existing)

                # Add source relationship
                source_node = self._get_or_create_source(source)
                self.graph.merge(Relationship(existing, "FROM_SOURCE", source_node))

                return existing
            else:
                # Create new organism
                self.logger.info(f"Creating new organism: {name}")
                organism = Node(
                    "Organism",
                    name=name,
                    rank=rank,
                    iri=iri,
                    molecule_count=molecule_count,
                )
                self.graph.create(organism)

                # Add source relationship
                source_node = self._get_or_create_source(source)
                self.graph.merge(Relationship(organism, "FROM_SOURCE", source_node))

                return organism

        except Exception as e:
            self.logger.error(f"Error adding/updating organism: {str(e)}")
            raise

    def _find_existing_molecule(self, molecule: Molecule) -> Optional[Node]:
        """
        Find existing molecule in database using various identifiers.

        Args:
            molecule: Molecule to find

        Returns:
            Optional[Node]: Existing molecule if found
        """
        # Try finding by various identifiers in order of reliability
        if molecule.inchikey:
            existing = self.graph.nodes.match(
                "Molecule", inchikey=molecule.inchikey
            ).first()
            if existing:
                return existing

        if molecule.inchi:
            existing = self.graph.nodes.match("Molecule", inchi=molecule.inchi).first()
            if existing:
                return existing

        if molecule.smiles:
            existing = self.graph.nodes.match(
                "Molecule", smiles=molecule.smiles
            ).first()
            if existing:
                return existing

        # Try finding by external IDs
        if molecule.pubchem_cid:
            existing = self.graph.nodes.match(
                "Molecule", pubchem_cid=molecule.pubchem_cid
            ).first()
            if existing:
                return existing

        if molecule.chembl_id:
            existing = self.graph.nodes.match(
                "Molecule", chembl_id=molecule.chembl_id
            ).first()
            if existing:
                return existing

        return None

    def _update_molecule(
        self, existing: Node, molecule: Molecule, source: str
    ) -> MoleculeDB:
        """
        Update an existing molecule in the database.

        Args:
            existing: Existing molecule node
            molecule: New molecule data
            source: Source of the new data

        Returns:
            MoleculeDB: Updated molecule database object
        """
        # Update properties
        for key, value in molecule.model_dump().items():
            if value is not None:
                existing[key] = value

        # Add source as a property
        existing["source"] = source

        # Save changes
        self.graph.push(existing)
        return MoleculeDB.wrap(existing)

    def _create_molecule(self, molecule: Molecule, source: str) -> MoleculeDB:
        """
        Create a new molecule in the database.

        Args:
            molecule: Molecule to create
            source: Source of the data

        Returns:
            MoleculeDB: Created molecule database object
        """
        # Create molecule node
        node = Node("Molecule")
        for key, value in molecule.model_dump().items():
            if value is not None:
                node[key] = value

        # Add source as a property
        node["source"] = source

        # Create node
        self.graph.create(node)
        return MoleculeDB.wrap(node)

    def _get_or_create_source(self, source: str) -> Node:
        """
        Get or create a source node.

        Args:
            source: Source name

        Returns:
            Node: Source node
        """
        source_node = Node("Source", name=source)
        self.graph.merge(source_node, "Source", "name")
        return source_node

    def create_or_merge_node(
        self, label: str, key_properties: Dict[str, Any], properties: Dict[str, Any]
    ) -> Node:
        """
        Create a new node or merge with existing one.

        Args:
            label: Node label
            key_properties: Properties that uniquely identify the node
            properties: All node properties

        Returns:
            Node: Created or merged node
        """
        try:
            node = Node(label, **properties)
            self.graph.merge(node, label, *key_properties.keys())
            return node
        except Exception as e:
            self.logger.error(f"Error creating/merging node: {str(e)}")
            raise

    def create_relationship(
        self,
        from_label: str,
        from_properties: Dict[str, Any],
        relationship_type: str,
        to_label: str,
        to_properties: Dict[str, Any],
    ) -> None:
        """
        Create a relationship between two nodes.

        Args:
            from_label: Label of the source node
            from_properties: Properties to identify the source node
            relationship_type: Type of relationship
            to_label: Label of the target node
            to_properties: Properties to identify the target node
        """
        try:
            # Get or create nodes
            from_node = self.get_node(from_label, from_properties)
            to_node = self.get_node(to_label, to_properties)

            if from_node and to_node:
                rel = Relationship(from_node, relationship_type, to_node)
                self.graph.merge(rel)
        except Exception as e:
            self.logger.error(f"Error creating relationship: {str(e)}")
            raise

    def get_node(self, label: str, properties: Dict[str, Any]) -> Optional[Node]:
        """
        Get a node from the database.

        Args:
            label: Node label
            properties: Properties to identify the node

        Returns:
            Optional[Node]: Found node or None
        """
        try:
            node = self.matcher.match(label, **properties).first()
            return cast(Optional[Node], node)
        except Exception as e:
            self.logger.error(f"Error getting node: {str(e)}")
            raise

    def get_related_nodes(
        self,
        from_label: str,
        from_properties: Dict[str, Any],
        relationship_type: str,
        to_label: str,
    ) -> List[Node]:
        """
        Get nodes related to a given node.

        Args:
            from_label: Label of the source node
            from_properties: Properties to identify the source node
            relationship_type: Type of relationship
            to_label: Label of the target nodes

        Returns:
            List[Node]: List of related nodes
        """
        try:
            # Get the source node
            from_node = self.get_node(from_label, from_properties)
            if not from_node:
                return []

            # Find related nodes using a parameterized query
            prop_key = list(from_properties.keys())[0]
            prop_value = list(from_properties.values())[0]

            query = (
                f"MATCH (n:{from_label})-[r:{relationship_type}]->(m:{to_label}) "
                f"WHERE n.{prop_key} = $prop "
                f"RETURN m"
            )

            result = self.graph.run(query, prop=prop_value)
            if not result:
                return []

            return [
                cast(Node, record["m"]) for record in result if record and "m" in record
            ]

        except Exception as e:
            self.logger.error(f"Error getting related nodes: {str(e)}")
            raise

    def create_or_update_target(
        self,
        target_id: str,
        name: str,
        type: str,
        organism: Optional[str] = None,
        confidence_score: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create or update a target in the database.

        Args:
            target_id: ChEMBL target ID
            name: Target name
            type: Target type
            organism: Source organism
            confidence_score: Confidence score of target prediction

        Returns:
            Optional[Dict[str, Any]]: Created or updated target data
        """
        try:
            # Create Cypher query
            query = """
            MERGE (t:Target {chembl_id: $target_id})
            ON CREATE SET
                t.name = $name,
                t.type = $type,
                t.organism = $organism,
                t.confidence_score = $confidence_score,
                t.created_at = datetime()
            ON MATCH SET
                t.name = $name,
                t.type = $type,
                t.organism = $organism,
                t.confidence_score = CASE
                    WHEN $confidence_score > t.confidence_score OR t.confidence_score IS NULL
                    THEN $confidence_score
                    ELSE t.confidence_score
                END,
                t.updated_at = datetime()
            RETURN t
            """

            # Execute query
            result = self.graph.run(
                query,
                target_id=target_id,
                name=name,
                type=type,
                organism=organism,
                confidence_score=confidence_score,
            ).data()

            return result[0]["t"] if result else None

        except Exception as e:
            self.logger.error(f"Error creating/updating target: {str(e)}")
            return None

    def create_molecule_target_relationship(
        self,
        molecule_chembl_id: str,
        target_chembl_id: str,
        confidence_score: float,
        activities: List[Dict[str, Any]],
    ) -> bool:
        """
        Create or update a relationship between a molecule and a target.

        Args:
            molecule_chembl_id: ChEMBL molecule ID
            target_chembl_id: ChEMBL target ID
            confidence_score: Confidence score of the relationship
            activities: List of activity measurements

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create Cypher query
            query = """
            MATCH (m:Molecule {chembl_id: $molecule_id})
            MATCH (t:Target {chembl_id: $target_id})
            MERGE (m)-[r:TARGETS]->(t)
            SET r.confidence_score = CASE
                    WHEN $confidence_score > r.confidence_score OR r.confidence_score IS NULL
                    THEN $confidence_score
                    ELSE r.confidence_score
                END,
                r.activities = $activities,
                r.updated_at = datetime()
            RETURN r
            """

            # Execute query
            result = self.graph.run(
                query,
                molecule_id=molecule_chembl_id,
                target_id=target_chembl_id,
                confidence_score=confidence_score,
                activities=activities,
            ).data()

            return bool(result)

        except Exception as e:
            self.logger.error(f"Error creating molecule-target relationship: {str(e)}")
            return False
