from setuptools import setup, find_packages

setup(
    name="hyperblend",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.0.0",
        "requests>=2.31.0",
        "rdkit>=2023.9.1",
        "sqlalchemy>=2.0.0",
        "alembic>=1.13.0",
        "fastapi>=0.109.0",
        "uvicorn>=0.27.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.23.0",
            "httpx>=0.26.0",
            "coverage>=7.4.0",
        ],
    },
)
