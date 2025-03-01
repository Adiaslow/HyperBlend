"""Add external compound data table.

Revision ID: c3f461a23ef9
Revises: 
Create Date: 2025-03-01 01:56:09.123456

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3f461a23ef9"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create external compound data table."""
    op.create_table(
        "externalcompounddata",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("compound_id", sa.String(), nullable=False),
        sa.Column("chembl_id", sa.String(), nullable=True),
        sa.Column("pubchem_id", sa.String(), nullable=True),
        sa.Column("iupac_name", sa.String(), nullable=True),
        sa.Column("inchi", sa.String(), nullable=True),
        sa.Column("inchi_key", sa.String(), nullable=True),
        sa.Column("canonical_smiles", sa.String(), nullable=True),
        sa.Column("isomeric_smiles", sa.String(), nullable=True),
        sa.Column("molecular_formula", sa.String(), nullable=True),
        sa.Column("molecular_weight", sa.Float(), nullable=True),
        sa.Column("xlogp", sa.Float(), nullable=True),
        sa.Column("tpsa", sa.Float(), nullable=True),
        sa.Column("complexity", sa.Float(), nullable=True),
        sa.Column("h_bond_donor_count", sa.Integer(), nullable=True),
        sa.Column("h_bond_acceptor_count", sa.Integer(), nullable=True),
        sa.Column("rotatable_bond_count", sa.Integer(), nullable=True),
        sa.Column("heavy_atom_count", sa.Integer(), nullable=True),
        sa.Column("synonyms", sa.JSON(), nullable=True),
        sa.Column("target_interactions", sa.JSON(), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["compound_id"],
            ["compounds.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chembl_id"),
        sa.UniqueConstraint("pubchem_id"),
        sa.Index("ix_externalcompounddata_chembl_id", "chembl_id"),
        sa.Index("ix_externalcompounddata_pubchem_id", "pubchem_id"),
        sa.Index("ix_externalcompounddata_inchi_key", "inchi_key"),
    )


def downgrade() -> None:
    """Drop external compound data table."""
    op.drop_table("externalcompounddata")
