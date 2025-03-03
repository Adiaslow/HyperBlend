"""Service for enriching data from external sources."""

import asyncio
import aiohttp
import pubchempy as pcp
from typing import Dict, List, Optional, Set, Any, cast, Tuple, TypedDict
from concurrent.futures import ProcessPoolExecutor
from functools import partial, lru_cache
from chembl_webresource_client.new_client import new_client
from chembl_webresource_client.unichem import unichem_client as new_unichem_client
import logging

from ..domain.models import Compound, Source, Target, TargetType
from ..core.config import settings

logger = logging.getLogger(__name__)

# Cache size for external API responses
CACHE_SIZE = 1000
BATCH_SIZE = 50  # Number of compounds to process in parallel


class SearchAttempt(TypedDict):
    """Type definition for search attempt parameters."""

    url: str
    params: Dict[str, Any]


@lru_cache(maxsize=CACHE_SIZE)
def _query_pubchem_worker(name: str) -> Optional[Dict[str, Any]]:
    """Worker function for PubChem queries with caching."""
    try:
        logger.info(f"Querying PubChem for compound: {name}")
        compounds = pcp.get_compounds(name, "name")
        if not compounds:
            logger.warning(f"No compounds found in PubChem for: {name}")
            return None

        compound = compounds[0]
        synonyms = []
        if hasattr(compound, "synonyms"):
            synonyms.extend(compound.synonyms)
        if hasattr(compound, "iupac_name"):
            synonyms.append(compound.iupac_name)

        result = {
            "cid": compound.cid,
            "molecular_formula": compound.molecular_formula,
            "molecular_weight": compound.molecular_weight,
            "canonical_smiles": compound.canonical_smiles,
            "synonyms": synonyms,
        }
        logger.info(f"Successfully retrieved PubChem data for: {name}")
        logger.debug(f"PubChem data: {result}")
        return result
    except Exception as e:
        logger.error(f"Error querying PubChem for {name}: {str(e)}", exc_info=True)
        return None


@lru_cache(maxsize=CACHE_SIZE)
def _query_chembl_worker(args: Tuple[str, str]) -> Optional[Dict[str, Any]]:
    """Worker function for ChEMBL queries with caching."""
    name, smiles = args
    try:
        logger.info(f"Querying ChEMBL for compound: {name}")
        molecule = new_client.molecule  # Remove cast as it's not needed

        # Try by name first using pref_name
        logger.debug(f"Trying ChEMBL query by preferred name: {name}")
        results = molecule.filter(pref_name__icontains=name)

        # If no results, try by SMILES
        if not results and smiles:
            logger.debug(f"Trying ChEMBL query by SMILES: {smiles}")
            results = molecule.filter(
                molecule_structures__canonical_smiles__exact=smiles
            )

        # If still no results, try by molecule synonyms
        if not results:
            logger.debug(f"Trying ChEMBL query by synonyms: {name}")
            results = molecule.filter(
                molecule_synonyms__molecule_synonym__icontains=name
            )

        if results:
            molecule_data = results[0]
            result = {
                "chembl_id": molecule_data.get("molecule_chembl_id", ""),
                "synonyms": [
                    syn.get("molecule_synonym", "")
                    for syn in molecule_data.get("molecule_synonyms", [])
                ],
            }
            logger.info(f"Successfully retrieved ChEMBL data for: {name}")
            logger.debug(f"ChEMBL data: {result}")
            return result
        else:
            logger.warning(f"No results found in ChEMBL for: {name}")
            return None
    except Exception as e:
        logger.error(f"Error querying ChEMBL for {name}: {str(e)}", exc_info=True)
        return None


class DataEnrichmentService:
    """Service for enriching data from external sources."""

    def __init__(self, max_workers: int = 8):  # Increased from 4 to 8 workers
        """Initialize the enrichment service."""
        self.session: Optional[aiohttp.ClientSession] = None
        self._compound_synonyms: Dict[str, Set[str]] = {}
        self._source_synonyms: Dict[str, Set[str]] = {}
        self._target_synonyms: Dict[str, Set[str]] = {}
        self._max_workers = max_workers
        # Initialize ChEMBL clients
        self._molecule = new_client.molecule  # Remove cast as it's not needed
        self._mechanism = new_client.mechanism  # Remove cast as it's not needed
        self._target = new_client.target  # Remove cast as it's not needed
        self._unichem = new_unichem_client  # Remove cast as it's not needed

    async def __aenter__(self):
        """Create aiohttp session."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT)
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def enrich_compounds(self, compounds: List[Compound]) -> List[Compound]:
        """Enrich multiple compounds in parallel."""
        if not self.session or self.session.closed:
            async with self:
                return await self._enrich_compounds_impl(compounds)
        return await self._enrich_compounds_impl(compounds)

    async def _enrich_compounds_impl(self, compounds: List[Compound]) -> List[Compound]:
        """Implementation of parallel compound enrichment."""
        try:
            # Process compounds in batches
            for i in range(0, len(compounds), BATCH_SIZE):
                batch = compounds[i : i + BATCH_SIZE]

                # Create process pool for parallel queries
                with ProcessPoolExecutor(max_workers=self._max_workers) as executor:
                    # Query PubChem in parallel
                    pubchem_futures = []
                    for compound in batch:
                        if not compound.pubchem_id:
                            future = executor.submit(
                                _query_pubchem_worker, compound.name
                            )
                            pubchem_futures.append((compound, future))

                    # Process PubChem results
                    await asyncio.get_event_loop().run_in_executor(
                        None, self._process_pubchem_results, pubchem_futures
                    )

                    # Query ChEMBL in parallel
                    chembl_futures = []
                    for compound in batch:
                        if not compound.chembl_id and compound.smiles:
                            future = executor.submit(
                                _query_chembl_worker, (compound.name, compound.smiles)
                            )
                            chembl_futures.append((compound, future))

                    # Process ChEMBL results
                    await asyncio.get_event_loop().run_in_executor(
                        None, self._process_chembl_results, chembl_futures
                    )

                # Query NAPRALERT in parallel
                napralert_tasks = []
                for compound in batch:
                    if not compound.napralert_id and compound.smiles:
                        task = asyncio.create_task(
                            self._query_napralert(compound.name, compound.smiles)
                        )
                        napralert_tasks.append((compound, task))

                # Wait for all NAPRALERT queries to complete
                for compound, task in napralert_tasks:
                    try:
                        napralert_data = await task
                        if napralert_data:
                            compound.napralert_id = napralert_data.get(
                                "napralert_id", ""
                            )
                            self._add_compound_synonyms(
                                compound.name, napralert_data.get("synonyms", [])
                            )
                    except Exception as e:
                        logger.error(
                            f"Error processing NAPRALERT results for {compound.name}: {str(e)}"
                        )

            return compounds

        except Exception as e:
            logger.error(f"Error enriching compounds: {str(e)}")
            return compounds

    def _process_pubchem_results(self, futures):
        """Process PubChem results in parallel."""
        for compound, future in futures:
            try:
                pubchem_data = future.result()
                if pubchem_data:
                    compound.pubchem_id = str(pubchem_data.get("cid", ""))
                    compound.molecular_formula = pubchem_data.get(
                        "molecular_formula", ""
                    )
                    compound.molecular_weight = pubchem_data.get("molecular_weight")
                    compound.smiles = pubchem_data.get("canonical_smiles", "")
                    self._add_compound_synonyms(
                        compound.name, pubchem_data.get("synonyms", [])
                    )
            except Exception as e:
                logger.error(
                    f"Error processing PubChem results for {compound.name}: {str(e)}"
                )

    def _process_chembl_results(self, futures):
        """Process ChEMBL results in parallel."""
        for compound, future in futures:
            try:
                chembl_data = future.result()
                if chembl_data:
                    compound.chembl_id = chembl_data.get("chembl_id", "")
                    self._add_compound_synonyms(
                        compound.name, chembl_data.get("synonyms", [])
                    )
            except Exception as e:
                logger.error(
                    f"Error processing ChEMBL results for {compound.name}: {str(e)}"
                )

    async def enrich_compound(self, compound: Compound) -> Compound:
        """Enrich a single compound."""
        result = await self.enrich_compounds([compound])
        return result[0]

    async def get_compound_targets(self, compound: Compound) -> List[Target]:
        """Get targets for a compound from ChEMBL."""
        if not compound.chembl_id:
            return []

        try:
            # Get mechanism data using ChEMBL web resource client
            mechanisms = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._mechanism.filter(
                    molecule_chembl_id=compound.chembl_id
                ).only(["target_chembl_id", "target_name", "target_type"]),
            )

            targets = []
            for mech in mechanisms:
                target_name = mech.get("target_name")
                if not target_name:
                    continue

                # Get detailed target information
                target_data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._target.get(mech.get("target_chembl_id", ""))
                )

                if target_data:
                    # Map ChEMBL target type to TargetType enum
                    target_type = mech.get("target_type", "UNKNOWN")
                    try:
                        target_type_enum = TargetType[target_type.upper()]
                    except (KeyError, AttributeError):
                        target_type_enum = TargetType.UNKNOWN

                    # Query UniProt for additional data
                    if not self.session or self.session.closed:
                        async with self:
                            uniprot_data = await self._query_uniprot(target_name)
                    else:
                        uniprot_data = await self._query_uniprot(target_name)

                    target = Target(
                        id=f"T{len(targets) + 1:03d}",
                        name=target_name,
                        standardized_name=(
                            uniprot_data.get("recommended_name", target_name)
                            if uniprot_data
                            else target_name
                        ),
                        type=target_type_enum,
                        organism=target_data.get("organism", ""),
                        description=target_data.get("description", ""),
                        uniprot_id=(
                            uniprot_data.get("uniprot_id", "") if uniprot_data else ""
                        ),
                        chembl_id=mech.get("target_chembl_id", ""),
                        gene_id=uniprot_data.get("gene_id", "") if uniprot_data else "",
                        gene_name=(
                            uniprot_data.get("gene_name", "") if uniprot_data else ""
                        ),
                    )
                    targets.append(target)
                    if uniprot_data:
                        self._add_target_synonyms(
                            target.name, uniprot_data.get("synonyms", [])
                        )

            return targets

        except Exception as e:
            print(f"Error getting targets for compound {compound.name}: {str(e)}")
            return []

    async def _query_napralert(
        self, name: str, smiles: str
    ) -> Optional[Dict[str, Any]]:
        """Query NAPRALERT database for natural product information."""
        if not self.session or self.session.closed:
            logger.error("No active session for NAPRALERT query")
            return None

        try:
            logger.info(f"Querying NAPRALERT for compound: {name}")

            # Define search strategies
            search_attempts: List[Optional[SearchAttempt]] = [
                # 1. Try exact name search
                {
                    "url": f"{settings.NAPRALERT_API}/search",
                    "params": {
                        "query": name,
                        "search_type": "exact",
                        "field": "compound_name",
                    },
                },
                # 2. Try SMILES search if available
                (
                    {
                        "url": f"{settings.NAPRALERT_API}/search",
                        "params": {
                            "query": smiles,
                            "search_type": "exact",
                            "field": "smiles",
                        },
                    }
                    if smiles
                    else None
                ),
                # 3. Try fuzzy name search
                {
                    "url": f"{settings.NAPRALERT_API}/search",
                    "params": {
                        "query": name,
                        "search_type": "fuzzy",
                        "field": "compound_name",
                    },
                },
            ]

            for attempt in search_attempts:
                if not attempt:  # Skip None entries
                    continue

                logger.debug(f"Trying NAPRALERT search with URL: {attempt['url']}")
                try:
                    async with self.session.post(
                        attempt["url"],
                        headers={
                            "Accept": "application/json",
                            "Content-Type": "application/json",
                        },
                        json=attempt["params"],
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data and isinstance(data, list) and len(data) > 0:
                                molecule = data[0]  # Get the first match
                                result = {
                                    "napralert_id": molecule.get("id", ""),
                                    "synonyms": [
                                        name
                                        for name in [
                                            molecule.get("name"),
                                            molecule.get("iupac_name"),
                                            molecule.get("cas"),
                                        ]
                                        if name
                                    ],
                                    "inchi": molecule.get("inchi", ""),
                                    "inchikey": molecule.get("inchikey", ""),
                                    "molecular_formula": molecule.get(
                                        "molecular_formula", ""
                                    ),
                                }
                                logger.info(
                                    f"Successfully retrieved NAPRALERT data for: {name}"
                                )
                                logger.debug(f"NAPRALERT data: {result}")
                                return result
                except aiohttp.ClientError as e:
                    logger.warning(f"NAPRALERT search attempt failed: {str(e)}")
                    continue

            logger.warning(
                f"No results found in NAPRALERT for: {name} after trying all search methods"
            )
            return None

        except Exception as e:
            logger.error(
                f"Error querying NAPRALERT for {name}: {str(e)}", exc_info=True
            )
            return None

    async def _query_uniprot(self, name: str) -> Optional[Dict[str, Any]]:
        """Query UniProt for protein information."""
        if not self.session or self.session.closed:
            return None

        try:
            url = f"{settings.UNIPROT_API}/search?query={name}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("results"):
                        result = data["results"][0]
                        return {
                            "uniprot_id": result.get("primaryAccession", ""),
                            "recommended_name": (
                                result.get("proteinDescription", {})
                                .get("recommendedName", {})
                                .get("fullName", {})
                                .get("value", "")
                            ),
                            "organism": result.get("organism", {}).get(
                                "scientificName", ""
                            ),
                            "function": (
                                result.get("comments", [{}])[0]
                                .get("function", [{}])[0]
                                .get("value", "")
                            ),
                            "gene_id": (
                                result.get("genes", [{}])[0]
                                .get("geneName", {})
                                .get("value", "")
                            ),
                            "gene_name": (
                                result.get("genes", [{}])[0]
                                .get("geneName", {})
                                .get("value", "")
                            ),
                            "synonyms": [
                                name.get("value", "")
                                for name in result.get("proteinDescription", {}).get(
                                    "alternativeNames", []
                                )
                            ],
                        }
        except Exception as e:
            print(f"Error querying UniProt: {str(e)}")
        return None

    def _add_compound_synonyms(self, name: str, synonyms: List[str]) -> None:
        """Add compound synonyms to the tracking dictionary."""
        if name not in self._compound_synonyms:
            self._compound_synonyms[name] = set()
        self._compound_synonyms[name].update(synonyms)

    def _add_target_synonyms(self, name: str, synonyms: List[str]) -> None:
        """Add target synonyms to the tracking dictionary."""
        if name not in self._target_synonyms:
            self._target_synonyms[name] = set()
        self._target_synonyms[name].update(synonyms)

    def get_compound_synonyms(self, name: str) -> Set[str]:
        """Get all known synonyms for a compound."""
        return self._compound_synonyms.get(name, set())

    def get_target_synonyms(self, name: str) -> Set[str]:
        """Get all known synonyms for a target."""
        return self._target_synonyms.get(name, set())
