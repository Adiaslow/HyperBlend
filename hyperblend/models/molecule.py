"""Model representing a molecule (chemical compound) in the system."""

from typing import Optional, List
from pydantic import BaseModel, Field


class Molecule(BaseModel):
    """A molecule that can be found in organisms and interact with biological targets."""

    id: str = Field(..., description="Unique identifier for the molecule")
    name: str = Field(..., description="Common name of the molecule")
    formula: Optional[str] = Field(None, description="Chemical formula")
    molecular_weight: Optional[float] = Field(
        None, description="Molecular weight in g/mol"
    )
    smiles: Optional[str] = Field(None, description="SMILES representation")
    inchi: Optional[str] = Field(None, description="InChI representation")
    inchikey: Optional[str] = Field(None, description="InChIKey for the molecule")

    # External database identifiers
    pubchem_cid: Optional[str] = Field(None, description="PubChem Compound ID")
    chembl_id: Optional[str] = Field(None, description="ChEMBL ID")
    drugbank_id: Optional[str] = Field(None, description="DrugBank ID")

    # Physical properties
    logp: Optional[float] = Field(None, description="Calculated LogP")
    polar_surface_area: Optional[float] = Field(
        None, description="Topological polar surface area"
    )

    # Biological properties
    known_activities: Optional[List[str]] = Field(
        default_factory=list, description="Known biological activities"
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "MOL123",
                "name": "Caffeine",
                "formula": "C8H10N4O2",
                "molecular_weight": 194.19,
                "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
                "inchi": "InChI=1S/C8H10N4O2/c1-10-4-9-6-5(10)7(13)12(3)8(14)11(6)2/h4H,1-3H3",
                "inchikey": "RYYVLZVUVIJVGH-UHFFFAOYSA-N",
                "pubchem_cid": "2519",
                "chembl_id": "CHEMBL113",
                "drugbank_id": "DB00847",
                "logp": -0.07,
                "polar_surface_area": 58.4,
                "known_activities": [
                    "adenosine receptor antagonist",
                    "phosphodiesterase inhibitor",
                ],
            }
        }
