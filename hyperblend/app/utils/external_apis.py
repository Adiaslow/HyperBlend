import aiohttp
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class PubChemAPI:
    """Utility class for interacting with the PubChem REST API."""

    def __init__(self):
        self.base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    async def get_compound_by_cas(self, cas_number: str) -> Optional[Dict[str, Any]]:
        """
        Fetch compound data from PubChem using CAS number.

        Args:
            cas_number: The CAS registry number of the compound

        Returns:
            Dictionary containing compound data or None if not found
        """
        try:
            # First get the PubChem CID using the CAS number
            async with aiohttp.ClientSession() as session:
                # Search for CID using CAS
                url = f"{self.base_url}/compound/name/{cas_number}/cids/JSON"
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    data = await response.json()
                    if "IdentifierList" not in data:
                        return None
                    cid = data["IdentifierList"]["CID"][0]

                    # Get compound properties using CID
                    return await self.get_compound_by_cid(str(cid))
        except Exception as e:
            logger.error(f"Error fetching compound data for CAS {cas_number}: {str(e)}")
            return None

    async def get_compound_by_cid(self, cid: str) -> Optional[Dict[str, Any]]:
        """
        Fetch compound data from PubChem using compound ID (CID).

        Args:
            cid: The PubChem Compound ID

        Returns:
            Dictionary containing compound data or None if not found
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Get compound properties
                properties = [
                    "IUPACName",
                    "MolecularFormula",
                    "MolecularWeight",
                    "CanonicalSMILES",
                    "InChI",
                    "InChIKey",
                ]
                url = f"{self.base_url}/compound/cid/{cid}/property/{','.join(properties)}/JSON"

                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    prop_data = await response.json()
                    if "PropertyTable" not in prop_data:
                        return None

                    # Get compound description
                    desc_url = f"{self.base_url}/compound/cid/{cid}/description/JSON"
                    async with session.get(desc_url) as desc_response:
                        description = ""
                        if desc_response.status == 200:
                            desc_data = await desc_response.json()
                            if (
                                "InformationList" in desc_data
                                and "Information" in desc_data["InformationList"]
                            ):
                                description = desc_data["InformationList"][
                                    "Information"
                                ][0].get("Description", "")

                    # Format the response
                    prop = prop_data["PropertyTable"]["Properties"][0]
                    return {
                        "name": prop.get("IUPACName", ""),
                        "molecular_formula": prop.get("MolecularFormula", ""),
                        "molecular_weight": prop.get("MolecularWeight", 0),
                        "smiles": prop.get("CanonicalSMILES", ""),
                        "inchi": prop.get("InChI", ""),
                        "inchi_key": prop.get("InChIKey", ""),
                        "pubchem_cid": cid,
                        "description": description,
                        "cas_number": cas_number if "cas_number" in locals() else None,
                    }
        except Exception as e:
            logger.error(f"Error fetching compound data for CID {cid}: {str(e)}")
            return None


class ChemblAPI:
    """Class for interacting with the ChEMBL API."""

    pass


class DrugBankAPI:
    """Class for interacting with the DrugBank API."""

    pass
