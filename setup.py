"""Setup file for hyperblend package."""

from setuptools import setup, find_packages

setup(
    name="hyperblend",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "py2neo",
        "pubchempy",
        "chembl_webresource_client",
    ],
    python_requires=">=3.8",
)
