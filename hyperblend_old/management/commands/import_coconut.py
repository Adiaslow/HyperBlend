"""Command to import data from the COCONUT database."""

import argparse
import asyncio
import logging
import aiohttp
from sqlalchemy.ext.asyncio import create_async_engine
from hyperblend_old.config import settings
from hyperblend_old.infrastructure.repositories.models.base import Base
from hyperblend_old.infrastructure.repositories.models.compounds import Compound
from hyperblend_old.management import register_command

logger = logging.getLogger(__name__)


async def get_auth_token(session, email, password):
    """Get authentication token from COCONUT API."""
    auth_url = "https://coconut.naturalproducts.net/api/auth/login"
    async with session.post(
        auth_url, json={"email": email, "password": password}
    ) as response:
        if response.status != 200:
            raise Exception(f"Authentication failed: {response.status}")
        data = await response.json()
        return data.get("access_token")


async def search_compounds(session, query, token):
    """Search for compounds in COCONUT database."""
    search_url = "https://coconut.naturalproducts.net/api/search"
    headers = {"Authorization": f"Bearer {token}"}
    search_data = {
        "search": {
            "scopes": [],
            "filters": [{"field": "name", "operator": "like", "value": f"%{query}%"}],
        }
    }

    async with session.post(search_url, json=search_data, headers=headers) as response:
        print(f"Response status: {response.status}")
        if response.status != 200:
            raise Exception(f"Search failed: {response.status}")
        return await response.json()


async def get_or_create_compound(session, compound_data):
    """Get or create a compound record."""
    coconut_id = compound_data["identifier"].split(".")[0]

    async with session.begin():
        # Check if compound exists
        result = await session.execute(
            f"SELECT * FROM compounds WHERE coconut_id = '{coconut_id}'"
        )
        existing = result.fetchone()

        if not existing:
            # Create new compound
            compound = Compound(
                name=compound_data["name"],
                smiles=compound_data["canonical_smiles"],
                coconut_id=coconut_id,
                coconut_data=compound_data,
            )
            session.add(compound)
            await session.commit()
            return compound
        return existing


async def import_compound_data(query, email, password):
    """Import compound data from COCONUT."""
    print(f"Starting import for compound: {query}")

    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with aiohttp.ClientSession() as http_session:
        try:
            # Get authentication token
            token = await get_auth_token(http_session, email, password)

            # Search for compounds
            search_results = await search_compounds(http_session, query, token)
            print(f"Found {len(search_results.get('data', []))} compound entries")

            # Process compounds
            async with engine.begin() as db_session:
                for compound_data in search_results.get("data", []):
                    await get_or_create_compound(db_session, compound_data)

            print("Successfully imported compound data for", query)

        except Exception as e:
            logger.error(f"Error importing compound data: {str(e)}")
            raise
        finally:
            await engine.dispose()


@register_command("import_coconut")
def command_import_coconut(args):
    """Command handler for COCONUT data import."""
    parser = argparse.ArgumentParser(description="Import data from COCONUT database")
    parser.add_argument("query", help="Search query for compounds")
    parser.add_argument(
        "--email", help="COCONUT API email", default=settings.COCONUT_EMAIL
    )
    parser.add_argument(
        "--password", help="COCONUT API password", default=settings.COCONUT_PASSWORD
    )

    parsed_args = parser.parse_args(args)
    asyncio.run(
        import_compound_data(parsed_args.query, parsed_args.email, parsed_args.password)
    )
