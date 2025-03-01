# scripts/run_tests.py

"""Script to run the test suite."""

import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Run the test suite."""
    # Get project root directory
    project_root = Path(__file__).parent.parent

    # Run pytest with coverage
    result = subprocess.run(
        [
            "pytest",
            "-v",
            "--cov=hyperblend",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--asyncio-mode=auto",
            str(project_root / "tests"),
        ],
        cwd=project_root,
    )

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
