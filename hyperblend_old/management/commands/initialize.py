"""Database initialization and setup command."""

import argparse
import asyncio
import logging
import sys
from typing import List, Optional, Tuple, Sequence, Any
from hyperblend_old.management import register_command, _commands

logger = logging.getLogger(__name__)


async def run_command(command: str, args: Sequence[str]) -> None:
    """Run a management command."""
    if command not in _commands:
        logger.error(f"Unknown command: {command}")
        sys.exit(1)

    try:
        result = _commands[command](args)
        if asyncio.iscoroutine(result):
            await result
    except Exception as e:
        logger.error(f"Command '{command}' failed: {str(e)}")
        sys.exit(1)


async def initialize_database(clean: bool = False, skip_import: bool = False) -> None:
    """Initialize and populate the database."""
    steps = [
        # 1. Database Setup
        (
            "Setting up database...",
            [
                ("db", ["init"]),
                ("db", ["cleanup-targets"]) if clean else None,
                ("db", ["clear-test"]) if clean else None,
            ],
        ),
        # 2. Data Import (if not skipped)
        (
            "Importing data...",
            (
                [
                    ("import", ["plant", "Sceletium tortuosum"]),
                    ("import", ["plant", "Psilocybe cubensis"]),
                    ("import", ["targets"]),
                    ("import", ["pubchem"]),
                ]
                if not skip_import
                else []
            ),
        ),
        # 3. Data Standardization
        (
            "Standardizing data...",
            [
                ("standardize", ["compounds"]),
                ("standardize", ["targets"]),
                ("standardize", ["sources"]),
                ("standardize", ["smiles"]),
            ],
        ),
        # 4. Data Verification
        (
            "Verifying data...",
            [
                ("verify", ["compounds"]),
                ("verify", ["targets"]),
                ("verify", ["sources"]),
            ],
        ),
    ]

    for step_desc, commands in steps:
        logger.info(step_desc)
        for cmd, args in commands:
            if cmd is not None:  # Skip None commands (conditionally disabled)
                await run_command(cmd, args or [])
                logger.info(f"✓ Completed: {cmd} {' '.join(args or [])}")
        logger.info("---")


@register_command("initialize")
async def command_initialize(args: List[str]) -> None:
    """Initialize the database with standardized and verified data."""
    parser = argparse.ArgumentParser(
        description="Initialize database with standardized and verified data"
    )
    parser.add_argument(
        "--clean", action="store_true", help="Clean existing data before initialization"
    )
    parser.add_argument(
        "--skip-import", action="store_true", help="Skip data import step"
    )

    parsed_args = parser.parse_args(args)

    try:
        await initialize_database(
            clean=parsed_args.clean, skip_import=parsed_args.skip_import
        )
        logger.info("Database initialization completed successfully!")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        sys.exit(1)
