"""Add compound synonyms table and modify compounds table.

Revision ID: 20250302_010000
Create Date: 2025-03-02 01:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20250302_010000"
down_revision: Union[str, None] = "c3f461a23ef9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create compound_synonyms table and modify compounds table."""
    # Add canonical_name column to compounds table
    op.add_column(
        "compounds",
        sa.Column("canonical_name", sa.String(), nullable=True),
    )

    # Create compound_synonyms table
    op.create_table(
        "compound_synonyms",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("compound_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "source", sa.String(), nullable=True
        ),  # e.g., 'PubChem', 'ChEMBL', 'IUPAC'
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["compound_id"],
            ["compounds.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("compound_id", "name", name="uq_compound_synonym"),
    )

    # Create indexes
    op.create_index(
        "ix_compound_synonyms_name",
        "compound_synonyms",
        ["name"],
    )
    op.create_index(
        "ix_compounds_canonical_name",
        "compounds",
        ["canonical_name"],
    )


def downgrade() -> None:
    """Remove compound_synonyms table and revert compounds table changes."""
    op.drop_index("ix_compound_synonyms_name", "compound_synonyms")
    op.drop_index("ix_compounds_canonical_name", "compounds")
    op.drop_table("compound_synonyms")
    op.drop_column("compounds", "canonical_name")
