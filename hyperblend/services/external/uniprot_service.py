"""Service for interacting with the UniProt API and storing data in Neo4j."""

import logging
from typing import Dict, List, Optional, Any, TypedDict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from py2neo import Graph
from ..base_service import BaseService
from hyperblend.database.entry_manager import DatabaseEntryManager

logger = logging.getLogger(__name__)


class ProteinResult(TypedDict):
    """Type definition for protein result."""

    uniprot_id: str
    entry_name: str
    protein_name: str
    gene_names: List[str]
    organism: str
    length: Optional[int]
    sequence: Optional[str]
    ec_numbers: List[str]
    function: str
    catalytic_activity: List[str]
    pathways: List[str]
    diseases: List[str]
    chembl_ids: List[str]
    pdb_ids: List[str]


class UniProtService(BaseService):
    """Service for interacting with the UniProt API and storing data in Neo4j."""

    def __init__(self, db_manager: Optional[DatabaseEntryManager] = None):
        """Initialize the UniProt service.

        Args:
            db_manager: Optional database manager for storing entries
        """
        super().__init__()
        self.base_url = "https://rest.uniprot.org/uniprotkb"

        # Initialize database connection with proper configuration
        if db_manager is None:
            graph = Graph(
                "bolt://localhost:7687", auth=("neo4j", "password"), name="neo4j"
            )
            db_manager = DatabaseEntryManager(graph)

        self.db_manager = db_manager

        # Setup session with retry capability
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry_strategy))

    def search_protein(self, query: str, organism: str = None) -> List[Dict[str, Any]]:
        """
        Search for proteins in UniProt.

        Args:
            query: The search query
            organism: Optional organism name to filter results

        Returns:
            List of protein entries matching the search criteria
        """
        try:
            # Clean and encode query parameters
            query = query.strip()
            if organism:
                organism = organism.strip()

            # Build search query parts
            query_parts = []

            # Add main query - if it contains a colon, treat as field-specific search
            if ":" in query:
                query_parts.append(query)
            else:
                query_parts.append(f'content:"{query}"')

            # Add reviewed filter
            query_parts.append("reviewed:true")

            # Add organism filter if specified
            if organism:
                query_parts.append(f'organism:"{organism}"')

            # Combine query parts
            combined_query = " AND ".join(query_parts)

            # Set up request parameters
            params = {"format": "json", "size": 5, "query": combined_query}

            # Make request with retry session
            response = self.session.get(f"{self.base_url}/search", params=params)
            response.raise_for_status()

            data = response.json()
            return data.get("results", [])

        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching for protein {query}: {str(e)}")
            return []

    def get_protein(
        self, uniprot_id: str, use_cache: bool = True
    ) -> Optional[ProteinResult]:
        """
        Get detailed information about a specific protein.

        Args:
            uniprot_id: UniProt accession number
            use_cache: Whether to check the database first

        Returns:
            Dictionary containing protein details or None if not found
        """
        if use_cache:
            cached_result = self._get_cached_protein(uniprot_id)
            if cached_result:
                return cached_result

        params = {"format": "json"}

        try:
            response = self.session.get(f"{self.base_url}/{uniprot_id}", params=params)
            response.raise_for_status()
            result = self._format_protein_result(response.json())
            self._store_protein(result)
            return result
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error getting protein {uniprot_id}: {e}")
            return None

    def get_protein_sequence(self, uniprot_id: str) -> Optional[str]:
        """
        Get the sequence of a specific protein.

        Args:
            uniprot_id: UniProt accession number

        Returns:
            Protein sequence as string or None if not found
        """
        params = {"format": "fasta"}

        try:
            response = self.session.get(f"{self.base_url}/{uniprot_id}", params=params)
            response.raise_for_status()

            # Skip the header line and join the sequence lines
            sequence_lines = response.text.split("\n")[1:]
            return "".join(sequence_lines).strip()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error getting sequence for {uniprot_id}: {e}")
            return None

    def get_protein_features(self, uniprot_id: str) -> List[Dict[str, Any]]:
        """
        Get structural and functional features of a protein.

        Args:
            uniprot_id: UniProt accession number

        Returns:
            List of feature dictionaries
        """
        params = {"format": "json"}

        try:
            # Features are now included in the main protein response
            response = self.session.get(f"{self.base_url}/{uniprot_id}", params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("features", [])
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error getting features for {uniprot_id}: {e}")
            return []

    def _store_protein(self, protein_data: Dict[str, Any]) -> None:
        """
        Store protein data in the database.

        Args:
            protein_data: Protein data from UniProt API
        """
        try:
            logger.debug(f"Storing protein {protein_data.get('primaryAccession')}")

            # Create or merge protein node
            protein_props = {
                "uniprot_id": protein_data.get("primaryAccession"),
                "entry_name": protein_data.get("uniProtkbId"),
                "name": protein_data.get("proteinDescription", {})
                .get("recommendedName", {})
                .get("fullName", {})
                .get("value"),
                "organism": protein_data.get("organism", {}).get("scientificName"),
                "length": protein_data.get("sequence", {}).get("length"),
                "function": protein_data.get("comments", [{}])[0]
                .get("text", [{}])[0]
                .get("value"),
            }

            protein_node = self.db_manager.create_or_merge_node(
                "Protein", {"uniprot_id": protein_props["uniprot_id"]}, protein_props
            )
            logger.debug(f"Created/merged protein node: {protein_node}")

            # Create gene nodes and relationships
            for gene in protein_data.get("genes", []):
                gene_name = gene.get("geneName", {}).get("value")
                if gene_name:
                    gene_node = self.db_manager.create_or_merge_node(
                        "Gene", {"name": gene_name}, {"name": gene_name}
                    )
                    self.db_manager.create_relationship(
                        "Protein",
                        {"uniprot_id": protein_props["uniprot_id"]},
                        "ENCODED_BY",
                        "Gene",
                        {"name": gene_name},
                    )
                    logger.debug(f"Created gene relationship: {gene_name}")

            # Create pathway nodes and relationships
            for comment in protein_data.get("comments", []):
                if comment.get("commentType") == "PATHWAY":
                    for text in comment.get("texts", []):
                        pathway_name = text.get("value")
                        if pathway_name:
                            pathway_node = self.db_manager.create_or_merge_node(
                                "Pathway",
                                {"name": pathway_name},
                                {"name": pathway_name},
                            )
                            self.db_manager.create_relationship(
                                "Protein",
                                {"uniprot_id": protein_props["uniprot_id"]},
                                "INVOLVED_IN",
                                "Pathway",
                                {"name": pathway_name},
                            )
                            logger.debug(
                                f"Created pathway relationship: {pathway_name}"
                            )

            # Create disease nodes and relationships
            for comment in protein_data.get("comments", []):
                if comment.get("commentType") == "DISEASE":
                    for disease in comment.get("diseases", []):
                        disease_name = disease.get("diseaseId")
                        if disease_name:
                            disease_node = self.db_manager.create_or_merge_node(
                                "Disease",
                                {"name": disease_name},
                                {"name": disease_name},
                            )
                            self.db_manager.create_relationship(
                                "Protein",
                                {"uniprot_id": protein_props["uniprot_id"]},
                                "ASSOCIATED_WITH",
                                "Disease",
                                {"name": disease_name},
                            )
                            logger.debug(
                                f"Created disease relationship: {disease_name}"
                            )

            # Create structure nodes and relationships
            for structure in protein_data.get("structures", []):
                pdb_id = structure.get("pdbId")
                if pdb_id:
                    structure_node = self.db_manager.create_or_merge_node(
                        "Structure",
                        {"pdb_id": pdb_id},
                        {"pdb_id": pdb_id, "source": "PDB"},
                    )
                    self.db_manager.create_relationship(
                        "Protein",
                        {"uniprot_id": protein_props["uniprot_id"]},
                        "HAS_STRUCTURE",
                        "Structure",
                        {"pdb_id": pdb_id},
                    )
                    logger.debug(f"Created structure relationship: {pdb_id}")

            # Create ChEMBL references
            for xref in protein_data.get("uniProtKBCrossReferences", []):
                if xref.get("database") == "ChEMBL":
                    chembl_id = xref.get("id")
                    if chembl_id:
                        chembl_node = self.db_manager.create_or_merge_node(
                            "Molecule",
                            {"chembl_id": chembl_id},
                            {"chembl_id": chembl_id, "source": "ChEMBL"},
                        )
                        self.db_manager.create_relationship(
                            "Protein",
                            {"uniprot_id": protein_props["uniprot_id"]},
                            "HAS_CHEMBL",
                            "Molecule",
                            {"chembl_id": chembl_id},
                        )
                        logger.debug(f"Created ChEMBL relationship: {chembl_id}")

        except Exception as e:
            logger.error(f"Error storing protein data: {str(e)}")

    def _get_cached_protein(self, uniprot_id: str) -> Optional[ProteinResult]:
        """Get a protein from the database cache.

        Args:
            uniprot_id: The UniProt ID to look up

        Returns:
            The cached protein data or None if not found
        """
        try:
            # Get the protein node
            protein_node = self.db_manager.get_node(
                "Protein", {"uniprot_id": uniprot_id}
            )

            if not protein_node:
                return None

            # Get relationships
            gene_names = self.db_manager.get_related_nodes(
                "Protein", {"uniprot_id": uniprot_id}, "ENCODED_BY", "Gene"
            )

            ec_numbers = self.db_manager.get_related_nodes(
                "Protein", {"uniprot_id": uniprot_id}, "HAS_EC_NUMBER", "ECNumber"
            )

            pathways = self.db_manager.get_related_nodes(
                "Protein", {"uniprot_id": uniprot_id}, "INVOLVED_IN", "Pathway"
            )

            diseases = self.db_manager.get_related_nodes(
                "Protein", {"uniprot_id": uniprot_id}, "ASSOCIATED_WITH", "Disease"
            )

            chembl_ids = self.db_manager.get_related_nodes(
                "Protein", {"uniprot_id": uniprot_id}, "HAS_CHEMBL", "Molecule"
            )

            pdb_ids = self.db_manager.get_related_nodes(
                "Protein", {"uniprot_id": uniprot_id}, "HAS_STRUCTURE", "Structure"
            )

            # Convert Node objects to dictionaries for safe property access
            protein_dict = dict(protein_node)

            result: ProteinResult = {
                "uniprot_id": str(protein_dict.get("uniprot_id", "")),
                "entry_name": str(protein_dict.get("entry_name", "")),
                "protein_name": str(protein_dict.get("protein_name", "")),
                "gene_names": [str(gene.get("name", "")) for gene in gene_names],
                "organism": str(protein_dict.get("organism", "")),
                "length": protein_dict.get("length"),
                "sequence": protein_dict.get("sequence"),
                "ec_numbers": [str(ec.get("number", "")) for ec in ec_numbers],
                "function": str(protein_dict.get("function", "")),
                "catalytic_activity": [],  # Not currently stored in Neo4j
                "pathways": [str(pathway.get("name", "")) for pathway in pathways],
                "diseases": [str(disease.get("name", "")) for disease in diseases],
                "chembl_ids": [str(mol.get("chembl_id", "")) for mol in chembl_ids],
                "pdb_ids": [str(struct.get("pdb_id", "")) for struct in pdb_ids],
            }

            return result

        except Exception as e:
            self.logger.error(f"Error retrieving cached protein {uniprot_id}: {e}")
            return None

    def _format_protein_result(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format the UniProt API response into a standardized format.

        Args:
            data: Raw response from UniProt API

        Returns:
            Formatted protein data
        """
        try:
            # Extract protein names
            protein_name = ""
            if "proteinDescription" in data:
                recommended_name = data["proteinDescription"].get("recommendedName", {})
                if recommended_name:
                    protein_name = recommended_name.get("fullName", {}).get("value", "")
                if (
                    not protein_name
                    and "alternativeNames" in data["proteinDescription"]
                ):
                    alt_names = data["proteinDescription"]["alternativeNames"]
                    if alt_names:
                        protein_name = alt_names[0].get("fullName", {}).get("value", "")

            # Extract gene names
            gene_names = []
            if "genes" in data:
                for gene in data["genes"]:
                    if "geneName" in gene:
                        gene_names.append(gene["geneName"].get("value", ""))

            # Extract organism information
            organism = ""
            if "organism" in data:
                organism = data["organism"].get("scientificName", "")

            # Extract function information
            function = ""
            if "comments" in data:
                function_comments = [
                    c for c in data["comments"] if c["commentType"] == "FUNCTION"
                ]
                if function_comments:
                    function = (
                        function_comments[0].get("texts", [{}])[0].get("value", "")
                    )

            # Extract EC numbers
            ec_numbers = []
            if (
                "proteinDescription" in data
                and "ecNumbers" in data["proteinDescription"]
            ):
                ec_numbers = [
                    ec.get("value", "")
                    for ec in data["proteinDescription"]["ecNumbers"]
                ]

            # Extract pathways
            pathways = []
            if "comments" in data:
                pathway_comments = [
                    c for c in data["comments"] if c["commentType"] == "PATHWAY"
                ]
                for comment in pathway_comments:
                    if "texts" in comment:
                        pathways.extend(
                            text.get("value", "") for text in comment["texts"]
                        )

            # Extract disease associations
            diseases = []
            if "comments" in data:
                disease_comments = [
                    c for c in data["comments"] if c["commentType"] == "DISEASE"
                ]
                for comment in disease_comments:
                    if "disease" in comment:
                        diseases.append(comment["disease"].get("description", ""))

            # Extract cross-references
            chembl_ids = []
            pdb_ids = []
            if "uniProtKBCrossReferences" in data:
                for xref in data["uniProtKBCrossReferences"]:
                    if xref["database"] == "ChEMBL":
                        chembl_ids.append(xref.get("id", ""))
                    elif xref["database"] == "PDB":
                        pdb_ids.append(xref.get("id", ""))

            return {
                "uniprot_id": data.get("primaryAccession", ""),
                "entry_name": data.get("uniProtkbId", ""),
                "protein_name": protein_name,
                "gene_names": gene_names,
                "organism": organism,
                "length": data.get("sequence", {}).get("length", 0),
                "function": function,
                "ec_numbers": ec_numbers,
                "pathways": pathways,
                "diseases": diseases,
                "chembl_ids": chembl_ids,
                "pdb_ids": pdb_ids,
            }

        except Exception as e:
            logger.error(f"Error formatting protein result: {str(e)}")
            return {}
