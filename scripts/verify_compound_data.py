# scripts/verify_compound_data.py

"""Script to verify and update compound data using PubChem and ChEMBL APIs."""

import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
import asyncio
import aiohttp
from datetime import datetime
import requests
import time
import pubchempy as pcp


@dataclass
class CompoundInfo:
    """Compound information from external databases."""

    pubchem_id: Optional[str] = None
    chembl_id: Optional[str] = None
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    smiles: Optional[str] = None
    iupac_name: Optional[str] = None
    synonyms: Optional[list[str]] = None
    description: Optional[str] = None
    source: Optional[str] = None  # Which database provided this info
    xlogp: Optional[float] = None  # Added XLogP property


def get_pubchem_data(cid: str) -> Dict[str, Any]:
    """
    Fetch compound data from PubChem using PubChemPy.
    """
    try:
        # Get compound by CID
        compounds = pcp.get_compounds(cid, "cid")
        if not compounds:
            print(f"No compound found for CID {cid}")
            return {}

        compound = compounds[0]

        # Get synonyms
        synonyms = compound.synonyms if hasattr(compound, "synonyms") else []

        return {
            "iupac_name": (
                compound.iupac_name if hasattr(compound, "iupac_name") else ""
            ),
            "molecular_formula": (
                compound.molecular_formula
                if hasattr(compound, "molecular_formula")
                else ""
            ),
            "molecular_weight": (
                compound.molecular_weight
                if hasattr(compound, "molecular_weight")
                else 0.0
            ),
            "canonical_smiles": (
                compound.canonical_smiles
                if hasattr(compound, "canonical_smiles")
                else ""
            ),
            "xlogp": compound.xlogp if hasattr(compound, "xlogp") else 0.0,
            "synonyms": synonyms,
        }

    except Exception as e:
        print(f"Error fetching PubChem data for {cid}: {str(e)}")
        return {}


async def fetch_with_retry(
    session: aiohttp.ClientSession, url: str, max_retries: int = 3
) -> Optional[Dict[str, Any]]:
    """Fetch data from URL with retry logic."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Accept": "application/json",
    }
    timeout = aiohttp.ClientTimeout(total=30)

    for attempt in range(max_retries):
        try:
            async with session.get(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:  # Rate limit
                    wait_time = 2**attempt  # Exponential backoff
                    print(f"Rate limited. Waiting {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                elif response.status == 404:
                    print(f"Resource not found: {url}")
                    return None
                else:
                    print(f"Error {response.status} for {url}: {await response.text()}")
                    return None
        except asyncio.TimeoutError:
            print(f"Timeout on attempt {attempt + 1} for {url}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
            continue
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
            continue
    return None


async def fetch_chembl_data(chembl_id: str) -> Optional[Dict[str, Any]]:
    """Fetch compound data from ChEMBL."""
    url = f"https://www.ebi.ac.uk/chembl/api/data/molecule/{chembl_id}"
    async with aiohttp.ClientSession() as session:
        return await fetch_with_retry(session, url)


def verify_compound_sync(compound: Dict[str, Any]) -> CompoundInfo:
    """Verify compound information using PubChem (synchronous)."""
    info = CompoundInfo()

    # Check PubChem if ID is available
    if compound.get("pubchem_id"):
        print(f"  Checking PubChem (ID: {compound['pubchem_id']})...")
        pubchem_data = get_pubchem_data(compound["pubchem_id"])
        if pubchem_data:
            info.molecular_formula = pubchem_data.get("molecular_formula")
            if pubchem_data.get("molecular_weight"):
                info.molecular_weight = float(pubchem_data["molecular_weight"])
            info.iupac_name = pubchem_data.get("iupac_name")
            info.smiles = pubchem_data.get("canonical_smiles")
            info.pubchem_id = compound["pubchem_id"]
            info.source = "PubChem"
            if pubchem_data.get("xlogp"):
                info.xlogp = float(pubchem_data["xlogp"])
            info.synonyms = pubchem_data.get("synonyms")

    return info


async def verify_compound_chembl(
    compound: Dict[str, Any], info: CompoundInfo
) -> CompoundInfo:
    """Verify compound information using ChEMBL (async)."""
    # Check ChEMBL if ID is available and we don't have complete data from PubChem
    if compound.get("chembl_id") and not all(
        [info.molecular_formula, info.molecular_weight, info.smiles]
    ):
        print(f"  Checking ChEMBL (ID: {compound['chembl_id']})...")
        chembl_data = await fetch_chembl_data(compound["chembl_id"])
        if chembl_data:
            info.chembl_id = compound["chembl_id"]
            if not info.molecular_formula:
                info.molecular_formula = chembl_data.get("molecule_properties", {}).get(
                    "full_molformula"
                )
            if not info.molecular_weight:
                info.molecular_weight = chembl_data.get("molecule_properties", {}).get(
                    "full_mwt"
                )
            if not info.smiles:
                info.smiles = chembl_data.get("molecule_structures", {}).get(
                    "canonical_smiles"
                )
            if not info.source:
                info.source = "ChEMBL"

    return info


async def main():
    """Main function to verify compound data."""
    # Import COMPOUNDS from the script directly
    script_path = Path(__file__).parent / "add_sceletium_data.py"
    with open(script_path, "r") as f:
        exec_globals = {}
        exec(f.read(), exec_globals)
        COMPOUNDS = exec_globals["COMPOUNDS"]

    print("Verifying compound data...")
    verified_data = {}

    for compound in COMPOUNDS:
        print(f"\nVerifying {compound['name']}...")

        # First try PubChem (synchronous)
        info = verify_compound_sync(compound)

        # Then try ChEMBL if needed (async)
        info = await verify_compound_chembl(compound, info)

        # Compare and report differences
        if info.molecular_formula and info.molecular_formula != compound.get(
            "molecular_formula"
        ):
            print(f"  Molecular formula mismatch:")
            print(f"    Current: {compound.get('molecular_formula')}")
            print(f"    {info.source}: {info.molecular_formula}")

        if (
            info.molecular_weight
            and abs(info.molecular_weight - compound.get("molecular_weight", 0)) > 0.01
        ):
            print(f"  Molecular weight mismatch:")
            print(f"    Current: {compound.get('molecular_weight')}")
            print(f"    {info.source}: {info.molecular_weight}")

        if info.smiles and info.smiles != compound.get("smiles"):
            print(f"  SMILES mismatch:")
            print(f"    Current: {compound.get('smiles')}")
            print(f"    {info.source}: {info.smiles}")

        if info.iupac_name:
            print(f"  IUPAC Name ({info.source}): {info.iupac_name}")

        if info.xlogp is not None:
            print(f"  XLogP ({info.source}): {info.xlogp}")

        if info.synonyms:
            print(f"  Found {len(info.synonyms)} synonyms")

        verified_data[compound["id"]] = {
            "current": compound,
            "verified": {
                "pubchem_id": info.pubchem_id,
                "chembl_id": info.chembl_id,
                "molecular_formula": info.molecular_formula,
                "molecular_weight": info.molecular_weight,
                "smiles": info.smiles,
                "iupac_name": info.iupac_name,
                "source": info.source,
                "xlogp": info.xlogp,
                "synonyms": info.synonyms,
            },
        }

    # Save verification results
    results_file = Path("compound_verification_results.json")
    with open(results_file, "w") as f:
        json.dump(verified_data, f, indent=2, default=str)

    print(f"\nVerification complete. Results saved to {results_file.absolute()}")


if __name__ == "__main__":
    asyncio.run(main())
