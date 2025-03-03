"""Management command system for HyperBlend."""

import asyncio
import importlib
import os
import sys
from pathlib import Path
from typing import Callable, Dict, Union, Awaitable, Any, List

# Type for command functions
CommandFunc = Union[
    Callable[[List[str]], None],  # Sync command
    Callable[[List[str]], Awaitable[None]],  # Async command
]

# Dictionary to store registered commands
_commands: Dict[str, CommandFunc] = {}


def register_command(name: str) -> Callable[[CommandFunc], CommandFunc]:
    """Register a management command."""

    def decorator(func: CommandFunc) -> CommandFunc:
        _commands[name] = func
        return func

    return decorator


def discover_commands() -> None:
    """Discover and import all management commands."""
    commands_dir = Path(__file__).parent / "commands"
    for entry in os.listdir(commands_dir):
        if entry.endswith(".py") and not entry.startswith("__"):
            name = entry[:-3]  # Remove .py extension
            importlib.import_module(f"hyperblend.management.commands.{name}")


def execute_from_command_line(argv: list) -> None:
    """Execute a management command from command line arguments."""
    discover_commands()

    if not argv or argv[0] in ["-h", "--help"]:
        print("Available commands:")
        for name in sorted(_commands.keys()):
            print(f"  {name}")
        sys.exit(0)

    command = argv[0]
    if command not in _commands:
        print(f"Unknown command: {command}")
        print("Available commands:")
        for name in sorted(_commands.keys()):
            print(f"  {name}")
        sys.exit(1)

    try:
        result = _commands[command](argv[1:])
        if asyncio.iscoroutine(result):
            asyncio.run(result)
    except Exception as e:
        print(f"Error executing command {command}: {str(e)}")
        sys.exit(1)
