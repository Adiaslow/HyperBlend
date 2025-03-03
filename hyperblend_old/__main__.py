# hyperblend/__main__.py
"""Main entry point for hyperblend CLI."""

import sys
from hyperblend_old.management import execute_from_command_line

if __name__ == "__main__":
    execute_from_command_line(sys.argv[1:])
