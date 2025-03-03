from typing import List, Optional, Dict, Any
from ..models.domain import Compound
from ..db.repository import BaseRepository
from ..utils.external_apis import PubChemAPI, ChemblAPI, DrugBankAPI
from hyperblend.db.neo4j import Neo4jDatabase
from hyperblend.config.settings import settings
import logging

logger = logging.getLogger(__name__)


class CompoundService:
    """Service for handling compound-related operations."""

    def __init__(self):
        """Initialize the compound service with a Neo4j connection."""
        self.repository = BaseRepository(Compound)
        self.pubchem_api = PubChemAPI()
        self.chembl_api = ChemblAPI()
        self.drugbank_api = DrugBankAPI()
        self.db = Neo4jDatabase()
        self.db.connect()

    def search_compound(self, query: str) -> List[Compound]:
        """Search for compounds across multiple databases."""
        compounds = []

        # Search PubChem
        pubchem_results = self.pubchem_api.search(query)
        for result in pubchem_results:
            compound = Compound(
                id=result.get("cid"),
                name=result.get("name"),
                smiles=result.get("smiles"),
                molecular_formula=result.get("molecular_formula"),
                molecular_weight=result.get("molecular_weight"),
                source="pubchem",
                confidence_score=0.9,
            )
            compounds.append(compound)

        # Search ChEMBL
        chembl_results = self.chembl_api.search(query)
        for result in chembl_results:
            compound = Compound(
                id=result.get("chembl_id"),
                name=result.get("pref_name"),
                smiles=result.get("smiles"),
                molecular_formula=result.get("molecular_formula"),
                molecular_weight=result.get("molecular_weight"),
                source="chembl",
                confidence_score=0.8,
            )
            compounds.append(compound)

        # Search DrugBank
        drugbank_results = self.drugbank_api.search(query)
        for result in drugbank_results:
            compound = Compound(
                id=result.get("drugbank_id"),
                name=result.get("name"),
                smiles=result.get("smiles"),
                molecular_formula=result.get("molecular_formula"),
                molecular_weight=result.get("molecular_weight"),
                source="drugbank",
                confidence_score=0.85,
            )
            compounds.append(compound)

        return compounds

    def get_compound_details(self, compound_id: str, source: str) -> Optional[Compound]:
        """Get detailed information about a compound from a specific source."""
        if source == "pubchem":
            details = self.pubchem_api.get_details(compound_id)
        elif source == "chembl":
            details = self.chembl_api.get_details(compound_id)
        elif source == "drugbank":
            details = self.drugbank_api.get_details(compound_id)
        else:
            return None

        if details:
            return Compound(
                id=compound_id,
                name=details.get("name"),
                smiles=details.get("smiles"),
                molecular_formula=details.get("molecular_formula"),
                molecular_weight=details.get("molecular_weight"),
                source=source,
                confidence_score=0.95,
            )
        return None

    def save_compound(self, compound: Compound) -> Compound:
        """Save a compound to the database."""
        return self.repository.create(compound)

    def get_compound(self, compound_id: str) -> Optional[Compound]:
        """
        Get a compound by ID.

        Args:
            compound_id: The ID of the compound to retrieve

        Returns:
            Compound object if found, None otherwise
        """
        cypher_query = """
        MATCH (c:Compound)
        WHERE id(c) = $compound_id
        RETURN c
        """

        with self.db.driver.session() as session:
            result = session.run(cypher_query, compound_id=int(compound_id))
            record = result.single()
            if record:
                node = record["c"]
                return Compound(
                    id=str(node.id),
                    name=node.get("name"),
                    smiles=node.get("smiles"),
                    description=node.get("description"),
                )
        return None

    def update_compound(
        self, compound_id: str, compound: Compound
    ) -> Optional[Compound]:
        """
        Update an existing compound.

        Args:
            compound_id: ID of compound to update
            compound: Updated Compound object

        Returns:
            Updated Compound object if found, None otherwise
        """
        cypher_query = """
        MATCH (c:Compound)
        WHERE id(c) = $compound_id
        SET c.name = $name,
            c.smiles = $smiles,
            c.description = $description
        RETURN c
        """

        with self.db.driver.session() as session:
            result = session.run(
                cypher_query,
                compound_id=int(compound_id),
                name=compound.name,
                smiles=compound.smiles,
                description=compound.description,
            )
            record = result.single()
            if record:
                node = record["c"]
                return Compound(
                    id=str(node.id),
                    name=node.get("name"),
                    smiles=node.get("smiles"),
                    description=node.get("description"),
                )
        return None

    def delete_compound(self, compound_id: str) -> bool:
        """
        Delete a compound.

        Args:
            compound_id: ID of compound to delete

        Returns:
            True if compound was deleted, False if not found
        """
        cypher_query = """
        MATCH (c:Compound)
        WHERE id(c) = $compound_id
        DELETE c
        RETURN count(c) as deleted
        """

        with self.db.driver.session() as session:
            result = session.run(cypher_query, compound_id=int(compound_id))
            return result.single()["deleted"] > 0

    def get_compound_targets(self, compound_id: str) -> List[Dict[str, Any]]:
        """Get all targets associated with a compound."""
        with self.repository.db.session() as session:
            query = """
            MATCH (c:compound {id: $compound_id})-[r:INTERACTS_WITH]->(t:target)
            RETURN t, r
            """
            result = session.run(query, compound_id=compound_id)
            return [
                {"target": dict(record["t"]), "interaction": dict(record["r"])}
                for record in result
            ]

    def get_compound_sources(self, compound_id: str) -> List[Dict[str, Any]]:
        """Get all natural sources containing the compound."""
        with self.repository.db.session() as session:
            query = """
            MATCH (s:source)-[r:CONTAINS]->(c:compound {id: $compound_id})
            RETURN s, r
            """
            result = session.run(query, compound_id=compound_id)
            return [
                {"source": dict(record["s"]), "relationship": dict(record["r"])}
                for record in result
            ]

    def get_graph_nodes(self, query: str = "") -> List[Dict[str, Any]]:
        """
        Get nodes for graph visualization.

        Args:
            query: Optional search query to filter nodes

        Returns:
            List of node dictionaries with id, label, and type
        """
        try:
            # First verify database connection
            if not self.db.driver:
                logger.error("Database connection not established")
                return []

            cypher_query = """
            MATCH (n)
            WHERE n.name IS NOT NULL
            AND (CASE WHEN $query <> ''
                 THEN toLower(n.name) CONTAINS toLower($query)
                 ELSE true END)
            RETURN DISTINCT id(n) as id, 
                   n.name as name,
                   labels(n)[0] as type,
                   n.smiles as smiles,
                   n.description as description
            LIMIT 100
            """

            with self.db.driver.session() as session:
                result = session.run(cypher_query, query=query)
                nodes = []
                for record in result:
                    try:
                        node = {
                            "id": str(record["id"]),  # Convert ID to string
                            "name": record["name"],
                            "type": record["type"],
                            "smiles": record.get("smiles"),
                            "description": record.get("description"),
                        }
                        nodes.append(node)
                    except Exception as e:
                        logger.error(
                            f"Error processing node record: {str(e)}", exc_info=True
                        )
                        continue

                logger.info(f"Found {len(nodes)} nodes for graph visualization")
                return nodes
        except Exception as e:
            logger.error(f"Error fetching graph nodes: {str(e)}", exc_info=True)
            return []

    def get_graph_relationships(self, query: str = "") -> List[Dict[str, Any]]:
        """
        Get relationships for graph visualization.

        Args:
            query: Optional search query to filter relationships

        Returns:
            List of relationship dictionaries with source, target and type
        """
        try:
            # First verify database connection
            if not self.db.driver:
                logger.error("Database connection not established")
                return []

            cypher_query = """
            MATCH (source)-[r]->(target)
            WHERE source.name IS NOT NULL 
            AND target.name IS NOT NULL
            AND (CASE WHEN $query <> ''
                 THEN toLower(source.name) CONTAINS toLower($query)
                 OR toLower(target.name) CONTAINS toLower($query)
                 ELSE true END)
            RETURN DISTINCT id(source) as source,
                   id(target) as target,
                   type(r) as type
            LIMIT 200
            """

            with self.db.driver.session() as session:
                result = session.run(cypher_query, query=query)
                relationships = []
                for record in result:
                    try:
                        rel = {
                            "source": str(record["source"]),  # Convert ID to string
                            "target": str(record["target"]),  # Convert ID to string
                            "type": record["type"],
                        }
                        relationships.append(rel)
                    except Exception as e:
                        logger.error(
                            f"Error processing relationship record: {str(e)}",
                            exc_info=True,
                        )
                        continue

                logger.info(
                    f"Found {len(relationships)} relationships for graph visualization"
                )
                return relationships
        except Exception as e:
            logger.error(f"Error fetching graph relationships: {str(e)}", exc_info=True)
            return []

    def get_compound_related(self, compound_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get related nodes for a compound.

        Args:
            compound_id: The ID of the compound

        Returns:
            Dictionary with lists of related sources and targets
        """
        cypher_query = """
        MATCH (c:Compound)-[r]-(related)
        WHERE id(c) = $compound_id
        RETURN DISTINCT id(related) as id,
               related.name as name,
               labels(related)[0] as type,
               type(r) as relationship
        """

        with self.db.driver.session() as session:
            result = session.run(cypher_query, compound_id=int(compound_id))
            related = {"sources": [], "targets": []}
            for record in result:
                node_type = record["type"]
                if node_type == "Source":
                    related["sources"].append(dict(record))
                elif node_type == "Target":
                    related["targets"].append(dict(record))
            return related

    def search_compounds(self, query: str) -> List[Compound]:
        """
        Search for compounds by name or SMILES.

        Args:
            query: Search query string

        Returns:
            List of matching Compound objects
        """
        cypher_query = """
        MATCH (c:Compound)
        WHERE toLower(c.name) CONTAINS toLower($query)
        OR toLower(c.smiles) CONTAINS toLower($query)
        RETURN c
        LIMIT 50
        """

        compounds = []
        with self.db.driver.session() as session:
            result = session.run(cypher_query, query=query)
            for record in result:
                node = record["c"]
                compounds.append(
                    Compound(
                        id=str(node.id),
                        name=node.get("name"),
                        smiles=node.get("smiles"),
                        description=node.get("description"),
                    )
                )
        return compounds

    def create_compound(self, compound: Compound) -> Compound:
        """
        Create a new compound.

        Args:
            compound: Compound object to create

        Returns:
            Created Compound object with ID
        """
        cypher_query = """
        CREATE (c:Compound {
            name: $name,
            smiles: $smiles,
            description: $description
        })
        RETURN c
        """

        with self.db.driver.session() as session:
            result = session.run(
                cypher_query,
                name=compound.name,
                smiles=compound.smiles,
                description=compound.description,
            )
            record = result.single()
            node = record["c"]
            return Compound(
                id=str(node.id),
                name=node.get("name"),
                smiles=node.get("smiles"),
                description=node.get("description"),
            )

    async def create_compound_from_cas(self, cas_number: str) -> Optional[Compound]:
        """
        Create a compound from a CAS number by fetching data from PubChem.

        Args:
            cas_number: The CAS registry number of the compound

        Returns:
            Created Compound object if successful, None if not found
        """
        try:
            # First check if compound already exists
            cypher_query = """
            MATCH (c:Compound {cas_number: $cas_number})
            RETURN c
            """

            with self.db.driver.session() as session:
                result = session.run(cypher_query, cas_number=cas_number)
                if result.single():
                    logger.info(f"Compound with CAS {cas_number} already exists")
                    return None

            # Fetch compound data from PubChem
            compound_data = await self.pubchem_api.get_compound_by_cas(cas_number)
            if not compound_data:
                logger.warning(f"No compound found for CAS {cas_number}")
                return None

            # Create compound node
            create_query = """
            CREATE (c:Compound {
                name: $name,
                cas_number: $cas_number,
                smiles: $smiles,
                inchi: $inchi,
                inchi_key: $inchi_key,
                molecular_formula: $molecular_formula,
                molecular_weight: $molecular_weight,
                iupac_name: $iupac_name,
                description: $description,
                pubchem_cid: $pubchem_cid
            })
            RETURN c
            """

            with self.db.driver.session() as session:
                result = session.run(
                    create_query,
                    name=compound_data.get("name"),
                    cas_number=cas_number,
                    smiles=compound_data.get("smiles"),
                    inchi=compound_data.get("inchi"),
                    inchi_key=compound_data.get("inchi_key"),
                    molecular_formula=compound_data.get("molecular_formula"),
                    molecular_weight=compound_data.get("molecular_weight"),
                    iupac_name=compound_data.get("iupac_name"),
                    description=compound_data.get("description"),
                    pubchem_cid=compound_data.get("pubchem_cid"),
                )
                record = result.single()
                if record:
                    node = record["c"]
                    return Compound(
                        id=str(node.id),
                        name=node.get("name"),
                        cas_number=node.get("cas_number"),
                        smiles=node.get("smiles"),
                        inchi=node.get("inchi"),
                        inchi_key=node.get("inchi_key"),
                        molecular_formula=node.get("molecular_formula"),
                        molecular_weight=node.get("molecular_weight"),
                        iupac_name=node.get("iupac_name"),
                        description=node.get("description"),
                        pubchem_cid=node.get("pubchem_cid"),
                    )

            return None
        except Exception as e:
            logger.error(f"Error creating compound from CAS {cas_number}: {str(e)}")
            raise

    def get_all_compounds(self) -> List[Compound]:
        """
        Get all compounds from the database.

        Returns:
            List of all Compound objects
        """
        cypher_query = """
        MATCH (c:Compound)
        RETURN c
        LIMIT 100
        """

        compounds = []
        with self.db.driver.session() as session:
            result = session.run(cypher_query)
            for record in result:
                node = record["c"]
                compounds.append(
                    Compound(
                        id=str(node.id),
                        name=node.get("name"),
                        smiles=node.get("smiles"),
                        description=node.get("description"),
                        molecular_formula=node.get("molecular_formula"),
                        molecular_weight=node.get("molecular_weight"),
                        cas_number=node.get("cas_number"),
                        pubchem_cid=node.get("pubchem_cid"),
                        chembl_id=node.get("chembl_id"),
                        drugbank_id=node.get("drugbank_id"),
                        chebi_id=node.get("chebi_id"),
                    )
                )
        return compounds

    def check_database_status(self) -> Dict[str, Any]:
        """
        Check the current status of the database.

        Returns:
            Dictionary containing database statistics
        """
        try:
            cypher_query = """
            MATCH (n)
            WITH labels(n) as labels, count(*) as count
            RETURN labels, count
            ORDER BY count DESC
            """

            with self.db.driver.session() as session:
                result = session.run(cypher_query)
                stats = [dict(record) for record in result]
                logger.info(f"Database status: {stats}")
                return {"node_counts": stats}
        except Exception as e:
            logger.error(f"Error checking database status: {str(e)}", exc_info=True)
            return {"error": str(e)}
