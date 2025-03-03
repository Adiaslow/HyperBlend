from setuptools import setup, find_packages

setup(
    name="hyperblend",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "flask>=3.0.0",
        "flask-cors>=4.0.0",
        "neo4j>=5.14.0",
        "pydantic>=2.5.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "pandas>=2.1.0",
        "numpy>=1.24.0",
        "biopython>=1.83",
        "rdkit>=2023.9.0",
        "flask-assets>=2.1.0",
    ],
    python_requires=">=3.8",
)
