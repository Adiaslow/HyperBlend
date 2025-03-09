"""Model representing a biological organism in the system."""

from typing import Optional, List
from pydantic import BaseModel, Field


class Organism(BaseModel):
    """An organism that contains molecules of interest."""

    id: str = Field(..., description="Unique identifier for the organism")
    scientific_name: str = Field(..., description="Scientific name (Latin binomial)")
    common_names: List[str] = Field(default_factory=list, description="Common names")

    # Taxonomy
    kingdom: Optional[str] = Field(None, description="Taxonomic kingdom")
    phylum: Optional[str] = Field(None, description="Taxonomic phylum")
    class_name: Optional[str] = Field(None, description="Taxonomic class")
    order: Optional[str] = Field(None, description="Taxonomic order")
    family: Optional[str] = Field(None, description="Taxonomic family")
    genus: Optional[str] = Field(None, description="Taxonomic genus")
    species: Optional[str] = Field(None, description="Taxonomic species")

    # External database identifiers
    ncbi_taxonomy_id: Optional[str] = Field(None, description="NCBI Taxonomy ID")
    gbif_id: Optional[str] = Field(
        None, description="Global Biodiversity Information Facility ID"
    )

    # Additional information
    description: Optional[str] = Field(None, description="Description of the organism")
    habitat: Optional[str] = Field(None, description="Natural habitat")
    distribution: Optional[List[str]] = Field(
        default_factory=list, description="Geographical distribution"
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "ORG123",
                "scientific_name": "Lophophora williamsii",
                "common_names": ["Peyote", "Peyotl"],
                "kingdom": "Plantae",
                "phylum": "Tracheophyta",
                "class_name": "Magnoliopsida",
                "order": "Caryophyllales",
                "family": "Cactaceae",
                "genus": "Lophophora",
                "species": "williamsii",
                "ncbi_taxonomy_id": "263965",
                "gbif_id": "3084923",
                "description": "A small, spineless cactus native to Mexico and southwestern United States",
                "habitat": "Desert and semi-desert regions",
                "distribution": ["Mexico", "United States (Texas)"],
            }
        }
