"""Model representing a biological target in the system."""

from typing import Optional, List
from pydantic import BaseModel, Field


class Target(BaseModel):
    """A biological target (protein, receptor, etc.) that molecules can interact with."""

    id: str = Field(..., description="Unique identifier for the target")
    name: str = Field(..., description="Name of the target")
    type: str = Field(..., description="Type of target (e.g., protein, receptor)")

    # Protein information (if applicable)
    gene_name: Optional[str] = Field(None, description="Associated gene name")
    protein_sequence: Optional[str] = Field(None, description="Amino acid sequence")
    organism: Optional[str] = Field(None, description="Source organism")

    # External database identifiers
    uniprot_id: Optional[str] = Field(None, description="UniProt ID")
    chembl_target_id: Optional[str] = Field(None, description="ChEMBL target ID")
    pdb_ids: Optional[List[str]] = Field(
        default_factory=list, description="Related PDB structure IDs"
    )

    # Functional information
    function: Optional[str] = Field(None, description="Biological function")
    pathways: Optional[List[str]] = Field(
        default_factory=list, description="Associated biological pathways"
    )
    diseases: Optional[List[str]] = Field(
        default_factory=list, description="Related diseases"
    )

    # Classification
    family: Optional[str] = Field(None, description="Protein family")
    subfamily: Optional[str] = Field(None, description="Protein subfamily")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "TAR123",
                "name": "Cannabinoid receptor 1",
                "type": "G-protein coupled receptor",
                "gene_name": "CNR1",
                "protein_sequence": "MKSILDGLADTTFRTITTDLLYVGSNDIQYEDIKGDMASKLGYFPQKFPLTSFRGSPFQEKMTAGDNPQLVPADQVNITEFYNKSLSSFKENEENIQCGENFMDIECFMVLNPSQQLAIAVLSLTLGTFTVLENLLVLCVILHSRSLRCRPSYHFIGSLAVADLLGSVIFVYSFIDFHVFHRKDSRNVFLFKLGGVTASFTASVGSLFLTAIDRYISIHRPLAYKRIVTRPKAVVAFCLMWTIAIVIAVLPLLGWNCEKLQSVCSDIFPHIDETYLMFWIGVTSVLLLFIVYAYMYILWKAHSHAVRMIQRGTQKSIIIHTSEDGKVQVTRPDQARMDIRLAKTLVLILVVLIICWGPLLAIMVYDVFGKMNKLIKTVFAFCSMLCLLNSTVNPIIYALRSKDLRHAFRSMFPSCEGTAQPLDNSMGDSDCLHKHANNAASVHRAAESCIKSTVKIAKVTMSVSTDTSAEAL",
                "organism": "Homo sapiens",
                "uniprot_id": "P21554",
                "chembl_target_id": "CHEMBL218",
                "pdb_ids": ["5TGZ", "5U09"],
                "function": "G-protein coupled receptor that binds endocannabinoids and mediates cannabinoid-induced CNS effects",
                "pathways": ["Endocannabinoid signaling", "Neurotransmitter binding"],
                "diseases": ["Obesity", "Substance dependence"],
                "family": "G protein-coupled receptors",
                "subfamily": "Cannabinoid receptors",
            }
        }
