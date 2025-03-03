"""Main entry point for HyperBlend management commands."""

import sys
from hyperblend_old.management import execute_from_command_line

if __name__ == "__main__":
    execute_from_command_line(sys.argv[1:])
