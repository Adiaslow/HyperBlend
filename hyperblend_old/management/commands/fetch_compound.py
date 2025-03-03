"""Fetch and integrate compound data from multiple sources."""

import argparse
import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Mapping, cast
import aiohttp
from aiohttp import ClientTimeout
from datetime import datetime
from hyperblend_old.config.neo4j import get_async_driver, Labels, RelTypes, Props
from hyperblend_old.management import register_command
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API endpoints
PUBCHEM_API_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
CHEMBL_API = "https://www.ebi.ac.uk/chembl/api/data"
UNIPROT_API = "https://rest.uniprot.org/uniprotkb"
COCONUT_API = "https://coconut.naturalproducts.net/api/v1"

# API request settings
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
REQUEST_TIMEOUT = 30  # seconds


def generate_id(prefix: str) -> str:
    """Generate a unique ID with a prefix."""
    return f"{prefix}_{str(uuid.uuid4())}"


async def retry_request(
    session: aiohttp.ClientSession, method: str, url: str, **kwargs
) -> Optional[Dict[str, Any]]:
    """Make an HTTP request with retry logic."""
    timeout = ClientTimeout(total=REQUEST_TIMEOUT)
    kwargs["timeout"] = timeout

    for attempt in range(MAX_RETRIES):
        try:
            async with getattr(session, method)(url, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return None
                elif response.status == 429:  # Rate limit
                    retry_after = int(response.headers.get("Retry-After", RETRY_DELAY))
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    logger.warning(
                        f"Request failed with status {response.status}: {url}"
                    )
                    return None
        except asyncio.TimeoutError:
            logger.warning(f"Request timed out: {url}")
            await asyncio.sleep(RETRY_DELAY * (attempt + 1))
        except Exception as e:
            logger.error(f"Request failed: {url} - {str(e)}")
            await asyncio.sleep(RETRY_DELAY * (attempt + 1))

    return None


async def fetch_pubchem_data(
    session: aiohttp.ClientSession, query: Mapping[str, Optional[str]]
) -> Optional[Dict[str, Any]]:
    """Fetch compound data from PubChem."""
    logger.info(f"Fetching PubChem data for query: {query}")
    try:
        # Try CID first if provided
        if query.get("pubchem_cid"):
            url = f"{PUBCHEM_API_BASE}/compound/cid/{query['pubchem_cid']}/JSON"
            data = await retry_request(session, "get", url)
            if data:
                return data

        # Try CAS number
        if query.get("cas"):
            url = f"{PUBCHEM_API_BASE}/compound/name/{query['cas']}/JSON"
            data = await retry_request(session, "get", url)
            if data:
                return data

        # Try compound name
        if query.get("name"):
            url = f"{PUBCHEM_API_BASE}/compound/name/{query['name']}/JSON"
            data = await retry_request(session, "get", url)
            if data:
                return data

        return None
    except Exception as e:
        logger.error(f"Error fetching PubChem data: {str(e)}")
        return None


async def fetch_chembl_data(
    session: aiohttp.ClientSession, query: Mapping[str, Optional[str]]
) -> Optional[Dict[str, Any]]:
    """Fetch compound data from ChEMBL."""
    try:
        # Try ChEMBL ID first if provided
        if query.get("chembl_id"):
            url = f"{CHEMBL_API}/molecule/{query['chembl_id']}"
            data = await retry_request(session, "get", url)
            if data:
                return data

        # Try searching by structure if we have SMILES
        if query.get("smiles"):
            url = f"{CHEMBL_API}/molecule/similarity"
            params = {"smiles": query["smiles"], "similarity": "100"}
            data = await retry_request(session, "get", url, params=params)
            if data and data.get("molecules"):
                return data["molecules"][0]

        return None
    except Exception as e:
        logger.error(f"Error fetching ChEMBL data: {str(e)}")
        return None


async def fetch_coconut_data(
    session: aiohttp.ClientSession, query: Mapping[str, Optional[str]]
) -> Optional[Dict[str, Any]]:
    """Fetch compound data from COCONUT."""
    try:
        # Try searching by name
        if query.get("name"):
            url = f"{COCONUT_API}/compound/search"
            params = {"query": cast(str, query["name"])}
            data = await retry_request(session, "get", url, params=params)
            if data and data.get("compounds"):
                compound_id = data["compounds"][0]["id"]
                # Get detailed data
                url = f"{COCONUT_API}/compound/{compound_id}"
                detail_data = await retry_request(session, "get", url)
                if detail_data:
                    return detail_data

        return None
    except Exception as e:
        logger.error(f"Error fetching COCONUT data: {str(e)}")
        return None


async def fetch_uniprot_data(
    session: aiohttp.ClientSession, query: Mapping[str, Optional[str]]
) -> List[Dict[str, Any]]:
    """Fetch human target data from UniProt."""
    targets = []

    # Search for human proteins that interact with the compound
    if query.get("name"):
        url = f"{UNIPROT_API}/search"
        params = {
            "query": f'organism_id:9606 AND {cast(str, query["name"])}',
            "format": "json",
        }
        data = await retry_request(session, "get", url, params=params)
        if data:
            targets.extend(data.get("results", []))

    return targets


async def create_or_update_compound(
    session, compound_data: Dict[str, Any], source_id: Optional[str] = None
) -> str:
    """Create or update a compound record in Neo4j."""
    compound_id = compound_data.get("id") or generate_id("CMP")
    current_time = datetime.utcnow().isoformat()

    # Get common name from PubChem data if available
    common_name = None
    if compound_data.get("pubchem_data"):
        pubchem_synonyms = (
            compound_data["pubchem_data"]
            .get("PC_Compounds", [{}])[0]
            .get("synonyms", [])
        )
        # Look for common name patterns
        for syn in pubchem_synonyms:
            if (
                len(syn) < 30
                and syn.replace("-", "").replace(" ", "").isalpha()
                and not any(
                    x in syn.lower()
                    for x in ["acid", "ester", "oxide", "chloride", "sulfate"]
                )
            ):
                common_name = syn
                break

    # Determine display name and canonical name
    display_name = (
        common_name or compound_data.get("name") or compound_data.get("iupac_name")
    )

    canonical_name = (
        compound_data.get("iupac_name") or compound_data.get("name") or common_name
    )

    # Create compound node
    cypher = f"""
    MERGE (c:{Labels.COMPOUND} {{{Props.ID}: $id}})
    SET 
        c.{Props.NAME} = $name,
        c.{Props.CANONICAL_NAME} = $canonical_name,
        c.{Props.SMILES} = $smiles,
        c.{Props.MOLECULAR_FORMULA} = $molecular_formula,
        c.{Props.MOLECULAR_WEIGHT} = $molecular_weight,
        c.{Props.DESCRIPTION} = $description,
        c.{Props.PUBCHEM_ID} = $pubchem_id,
        c.{Props.CHEMBL_ID} = $chembl_id,
        c.{Props.COCONUT_ID} = $coconut_id,
        c.{Props.CREATED_AT} = $created_at,
        c.{Props.LAST_UPDATED} = $last_updated
    """

    params = {
        "id": compound_id,
        "name": display_name,
        "canonical_name": canonical_name,
        "smiles": compound_data.get("smiles"),
        "molecular_formula": compound_data.get("molecular_formula"),
        "molecular_weight": compound_data.get("molecular_weight"),
        "description": compound_data.get("description"),
        "pubchem_id": compound_data.get("pubchem_id"),
        "chembl_id": compound_data.get("chembl_id"),
        "coconut_id": compound_data.get("coconut_id"),
        "created_at": current_time,
        "last_updated": current_time,
    }

    await session.run(cypher, params)

    # Add synonyms
    if compound_data.get("pubchem_data"):
        pubchem_synonyms = (
            compound_data["pubchem_data"]
            .get("PC_Compounds", [{}])[0]
            .get("synonyms", [])
        )
        for syn in pubchem_synonyms:
            cypher = f"""
            MATCH (c:{Labels.COMPOUND} {{{Props.ID}: $compound_id}})
            MERGE (s:Synonym {{name: $name, source: 'PubChem'}})
            MERGE (c)-[r:HAS_SYNONYM]->(s)
            """
            await session.run(cypher, {"compound_id": compound_id, "name": syn})

    # Link to source if provided
    if source_id:
        cypher = f"""
        MATCH (c:{Labels.COMPOUND} {{{Props.ID}: $compound_id}})
        MATCH (s:{Labels.SOURCE} {{{Props.ID}: $source_id}})
        MERGE (c)-[r:{RelTypes.FOUND_IN}]->(s)
        SET r.{Props.CREATED_AT} = $created_at
        """
        await session.run(
            cypher,
            {
                "compound_id": compound_id,
                "source_id": source_id,
                "created_at": current_time,
            },
        )

    return compound_id


async def create_or_update_source(session, source_data: Dict[str, Any]) -> str:
    """Create or update a source record in Neo4j."""
    source_id = source_data.get("id") or generate_id("SRC")
    current_time = datetime.utcnow().isoformat()

    cypher = f"""
    MERGE (s:{Labels.SOURCE} {{{Props.ID}: $id}})
    SET 
        s.{Props.NAME} = $name,
        s.{Props.TYPE} = $type,
        s.{Props.DESCRIPTION} = $description,
        s.common_names = $common_names,
        s.native_regions = $native_regions,
        s.traditional_uses = $traditional_uses,
        s.taxonomy = $taxonomy,
        s.{Props.CREATED_AT} = $created_at,
        s.{Props.LAST_UPDATED} = $last_updated
    """

    params = {
        "id": source_id,
        "name": source_data["name"],
        "type": source_data.get("type", "plant"),
        "description": source_data.get("description"),
        "common_names": json.dumps(source_data.get("common_names", [])),
        "native_regions": json.dumps(source_data.get("native_regions", [])),
        "traditional_uses": json.dumps(source_data.get("traditional_uses", [])),
        "taxonomy": json.dumps(source_data.get("taxonomy", {})),
        "created_at": current_time,
        "last_updated": current_time,
    }

    await session.run(cypher, params)
    return source_id


async def create_or_update_target(
    session, target_data: Dict[str, Any], compound_id: Optional[str] = None
) -> str:
    """Create or update a target record in Neo4j."""
    target_id = target_data.get("id") or generate_id("TGT")
    current_time = datetime.utcnow().isoformat()

    # Standardize target name
    name = target_data.get("name", "")
    standardized_name = None

    if name:
        name_lower = name.lower()

        # Handle receptor names
        receptor_patterns = {
            "serotonin": ["5-ht", "5ht", "serotonin", "hydroxytryptamine"],
            "dopamine": ["dopamine", "da receptor"],
            "gaba": ["gaba", "gamma-aminobutyric"],
            "glutamate": ["glutamate", "nmda", "ampa", "kainate"],
            "acetylcholine": ["acetylcholine", "muscarinic", "nicotinic", "ach"],
            "adrenergic": ["adrenergic", "adrenoceptor"],
            "opioid": ["opioid", "opiate"],
            "cannabinoid": ["cannabinoid", "cb1", "cb2"],
        }

        for std_name, patterns in receptor_patterns.items():
            if any(pattern in name_lower for pattern in patterns):
                subtype_match = re.search(r"[0-9]+[A-Za-z]*", name)
                subtype = subtype_match.group(0) if subtype_match else ""
                standardized_name = f"{std_name.title()} receptor {subtype}".strip()
                break

        # Handle enzyme names
        if not standardized_name:
            enzyme_patterns = {
                "monoamine oxidase": ["monoamine oxidase", "mao"],
                "cytochrome p450": ["cytochrome p450", "cyp"],
                "acetylcholinesterase": ["acetylcholinesterase", "ache"],
                "fatty acid amide hydrolase": ["fatty acid amide hydrolase", "faah"],
            }

            for std_name, patterns in enzyme_patterns.items():
                if any(pattern in name_lower for pattern in patterns):
                    subtype_match = re.search(r"[A-Za-z]?-?[0-9A-Z]+", name)
                    subtype = subtype_match.group(0) if subtype_match else ""
                    standardized_name = f"{std_name.title()} {subtype}".strip()
                    break

        # Basic standardization if no specific pattern matched
        if not standardized_name:
            name_clean = re.sub(r"protein|receptor|enzyme|human", "", name_lower)
            name_clean = re.sub(r"\s+", " ", name_clean).strip()
            standardized_name = name_clean.title()

    # Determine target type
    target_type = target_data.get("type", "protein")
    if standardized_name:
        if "receptor" in standardized_name.lower():
            target_type = "receptor"
        elif any(
            enzyme in standardized_name.lower()
            for enzyme in ["oxidase", "esterase", "hydrolase", "synthase"]
        ):
            target_type = "enzyme"
        elif "transporter" in standardized_name.lower():
            target_type = "transporter"

    cypher = f"""
    MERGE (t:{Labels.TARGET} {{{Props.ID}: $id}})
    SET 
        t.{Props.NAME} = $name,
        t.standardized_name = $standardized_name,
        t.{Props.TYPE} = $type,
        t.{Props.DESCRIPTION} = $description,
        t.{Props.ORGANISM} = $organism,
        t.{Props.UNIPROT_ID} = $uniprot_id,
        t.{Props.CHEMBL_ID} = $chembl_id,
        t.{Props.GENE_ID} = $gene_id,
        t.gene_name = $gene_name,
        t.{Props.CREATED_AT} = $created_at,
        t.{Props.LAST_UPDATED} = $last_updated
    """

    params = {
        "id": target_id,
        "name": name,
        "standardized_name": standardized_name,
        "type": target_type,
        "description": target_data.get("description"),
        "organism": target_data.get("organism", "Homo sapiens"),
        "uniprot_id": target_data.get("uniprot_id"),
        "chembl_id": target_data.get("chembl_id"),
        "gene_id": target_data.get("gene_id"),
        "gene_name": target_data.get("gene_name"),
        "created_at": current_time,
        "last_updated": current_time,
    }

    await session.run(cypher, params)

    # Link to compound if provided
    if compound_id:
        cypher = f"""
        MATCH (c:{Labels.COMPOUND} {{{Props.ID}: $compound_id}})
        MATCH (t:{Labels.TARGET} {{{Props.ID}: $target_id}})
        MERGE (c)-[r:{RelTypes.BINDS_TO}]->(t)
        SET 
            r.{Props.ACTION} = $action,
            r.{Props.ACTION_TYPE} = $action_type,
            r.{Props.ACTION_VALUE} = $action_value,
            r.{Props.EVIDENCE} = $evidence,
            r.{Props.EVIDENCE_URLS} = $evidence_urls,
            r.{Props.CREATED_AT} = $created_at
        """

        await session.run(
            cypher,
            {
                "compound_id": compound_id,
                "target_id": target_id,
                "action": target_data.get("action"),
                "action_type": target_data.get("action_type"),
                "action_value": target_data.get("action_value"),
                "evidence": target_data.get("evidence"),
                "evidence_urls": target_data.get("evidence_urls"),
                "created_at": current_time,
            },
        )

    return target_id


async def fetch_and_integrate_data(
    species_name: Optional[str],
    compound_name: Optional[str],
    cas_number: Optional[str],
    pubchem_cid: Optional[str],
    chembl_id: Optional[str],
) -> None:
    """Fetch data from all sources and integrate it into Neo4j."""
    driver = await get_async_driver()

    try:
        async with aiohttp.ClientSession() as http_session:
            # Prepare query dictionary
            query = {
                "name": compound_name,
                "cas": cas_number,
                "pubchem_cid": pubchem_cid,
                "chembl_id": chembl_id,
            }

            # Fetch data from all sources
            pubchem_data = await fetch_pubchem_data(http_session, query)
            chembl_data = await fetch_chembl_data(http_session, query)
            coconut_data = await fetch_coconut_data(http_session, query)
            uniprot_data = await fetch_uniprot_data(http_session, query)

            # Combine data
            compound_data = {
                "name": compound_name,
                "pubchem_data": pubchem_data,
                "chembl_data": chembl_data,
                "coconut_data": coconut_data,
                "pubchem_id": pubchem_cid,
                "chembl_id": chembl_id,
                "cas": cas_number,
            }

            # Extract SMILES and other properties
            if pubchem_data:
                compound_data.update(
                    {
                        "smiles": pubchem_data.get("PC_Compounds", [{}])[0].get(
                            "canonical_smiles"
                        ),
                        "molecular_formula": pubchem_data.get("PC_Compounds", [{}])[
                            0
                        ].get("molecular_formula"),
                        "molecular_weight": pubchem_data.get("PC_Compounds", [{}])[
                            0
                        ].get("molecular_weight"),
                    }
                )
            elif chembl_data:
                compound_data.update(
                    {
                        "smiles": chembl_data.get("molecule_structures", {}).get(
                            "canonical_smiles"
                        ),
                        "molecular_formula": chembl_data.get(
                            "molecule_properties", {}
                        ).get("full_molformula"),
                        "molecular_weight": chembl_data.get(
                            "molecule_properties", {}
                        ).get("full_mwt"),
                    }
                )
            elif coconut_data:
                compound_data.update(
                    {
                        "smiles": coconut_data.get("smiles"),
                        "molecular_formula": coconut_data.get("molecular_formula"),
                        "molecular_weight": coconut_data.get("molecular_weight"),
                    }
                )

            async with driver.session() as neo4j_session:
                # Create source if species name provided
                source_id = None
                if species_name:
                    source_id = await create_or_update_source(
                        neo4j_session,
                        {
                            "name": species_name,
                            "type": "plant",
                        },
                    )

                # Create compound
                compound_id = await create_or_update_compound(
                    neo4j_session, compound_data, source_id
                )

                # Create targets and link to compound
                for target_data in uniprot_data:
                    # Extract target information
                    protein_name = None
                    if "proteinDescription" in target_data:
                        recommended_name = target_data["proteinDescription"].get(
                            "recommendedName", {}
                        )
                        if "fullName" in recommended_name:
                            protein_name = recommended_name["fullName"].get("value")

                    if not protein_name and "gene" in target_data:
                        protein_name = target_data["gene"].get("name", {}).get("value")

                    if not protein_name:
                        protein_name = target_data.get("id")

                    if protein_name:
                        await create_or_update_target(
                            neo4j_session,
                            {
                                "name": protein_name,
                                "uniprot_id": target_data.get("accession"),
                                "gene_name": target_data.get("gene", [{}])[0]
                                .get("name", {})
                                .get("value"),
                                "description": target_data.get("comments", [{}])[0]
                                .get("text", [{}])[0]
                                .get("value"),
                            },
                            compound_id,
                        )

                logger.info(f"Successfully integrated data for {compound_name}")
    finally:
        await driver.close()


@register_command("fetch")
async def command_fetch(args):
    """Fetch compound data from multiple sources."""
    parser = argparse.ArgumentParser(description="Fetch and integrate compound data")
    parser.add_argument("--species", help="Species name")
    parser.add_argument("--name", help="Compound name")
    parser.add_argument("--cas", help="CAS number")
    parser.add_argument("--pubchem", help="PubChem CID")
    parser.add_argument("--chembl", help="ChEMBL ID")

    parsed_args = parser.parse_args(args)

    if not any(
        [parsed_args.name, parsed_args.cas, parsed_args.pubchem, parsed_args.chembl]
    ):
        parser.error(
            "At least one identifier (name, CAS, PubChem CID, or ChEMBL ID) is required"
        )

    await fetch_and_integrate_data(
        species_name=parsed_args.species,
        compound_name=parsed_args.name,
        cas_number=parsed_args.cas,
        pubchem_cid=parsed_args.pubchem,
        chembl_id=parsed_args.chembl,
    )
