# scripts/run_server.py

"""Script to run the FastAPI server."""

import uvicorn
from hyperblend.config import get_settings


def main() -> None:
    """Run the FastAPI server."""
    settings = get_settings()

    uvicorn.run(
        "hyperblend.interfaces.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        workers=1,
        loop="asyncio",
    )


if __name__ == "__main__":
    main()
