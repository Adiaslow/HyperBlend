from typing import Optional
from pydantic import BaseModel, Field


class Compound(BaseModel):
    """Model representing a chemical compound."""

    id: str = Field(..., description="Unique identifier for the compound")
    name: str = Field(..., description="Name of the compound")
    formula: Optional[str] = Field(None, description="Chemical formula")
    molecular_weight: Optional[float] = Field(
        None, description="Molecular weight in g/mol"
    )
    smiles: Optional[str] = Field(None, description="SMILES representation")
    inchi: Optional[str] = Field(None, description="InChI representation")
    source: Optional[str] = Field(None, description="Source of the compound")
    description: Optional[str] = Field(None, description="Description of the compound")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "id": "C123456",
                "name": "Example Compound",
                "formula": "C6H12O6",
                "molecular_weight": 180.156,
                "smiles": "C1=CC=CC=C1",
                "inchi": "InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H",
                "source": "PubChem",
                "description": "An example compound for demonstration",
            }
        }
