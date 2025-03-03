"""Development tools and utilities."""

import argparse
import asyncio
import logging
import subprocess
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from hyperblend_old.config import settings
from hyperblend_old.infrastructure.repositories.models.base import Base
from hyperblend_old.management import register_command

logger = logging.getLogger(__name__)


def run_tests(pattern=None):
    """Run the test suite."""
    cmd = ["pytest", "-v"]
    if pattern:
        cmd.append(pattern)

    try:
        subprocess.run(cmd, check=True)
        logger.info("Tests completed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Tests failed with exit code {e.returncode}")
        sys.exit(e.returncode)


def run_server(host="127.0.0.1", port=8000, reload=True):
    """Run the development server."""
    cmd = [
        "uvicorn",
        "hyperblend.main:app",
        f"--host={host}",
        f"--port={port}",
    ]
    if reload:
        cmd.append("--reload")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Server failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        logger.info("Server stopped")


async def search_compounds(query):
    """Search for compounds in the database."""
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.begin() as conn:
            # Search by name
            result = await conn.execute(
                text(
                    """
                SELECT id, name, smiles, molecular_formula 
                FROM compounds 
                WHERE name LIKE :query 
                OR molecular_formula LIKE :query
            """
                ),
                {"query": f"%{query}%"},
            )

            compounds = result.fetchall()

            if not compounds:
                logger.info("No compounds found matching the query")
                return

            logger.info(f"Found {len(compounds)} matching compounds:")
            for compound in compounds:
                logger.info(f"  - {compound.name}")
                logger.info(f"    ID: {compound.id}")
                logger.info(f"    SMILES: {compound.smiles}")
                logger.info(f"    Formula: {compound.molecular_formula}")
                logger.info("---")
    finally:
        await engine.dispose()


@register_command("dev")
def command_dev(args):
    """Development tools command handler."""
    parser = argparse.ArgumentParser(description="Development tools")
    subparsers = parser.add_subparsers(dest="action", help="Action to perform")

    # Test runner
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("pattern", nargs="?", help="Test pattern to match")

    # Server runner
    server_parser = subparsers.add_parser("server", help="Run development server")
    server_parser.add_argument("--host", default="127.0.0.1", help="Server host")
    server_parser.add_argument("--port", type=int, default=8000, help="Server port")
    server_parser.add_argument(
        "--no-reload", action="store_true", help="Disable auto-reload"
    )

    # Compound search
    search_parser = subparsers.add_parser("search", help="Search compounds")
    search_parser.add_argument("query", help="Search query")

    parsed_args = parser.parse_args(args)

    if parsed_args.action == "test":
        run_tests(parsed_args.pattern)
    elif parsed_args.action == "server":
        run_server(parsed_args.host, parsed_args.port, not parsed_args.no_reload)
    elif parsed_args.action == "search":
        asyncio.run(search_compounds(parsed_args.query))
