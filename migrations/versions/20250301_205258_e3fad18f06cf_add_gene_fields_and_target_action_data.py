"""Add gene fields and target action data

Revision ID: e3fad18f06cf
Revises: c3f461a23ef9
Create Date: 2025-03-01 20:52:58.694710+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3fad18f06cf"
down_revision: Union[str, None] = "c3f461a23ef9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add gene fields to biological_targets table
    op.add_column(
        "biological_targets", sa.Column("gene_id", sa.String(), nullable=True)
    )
    op.add_column(
        "biological_targets", sa.Column("gene_name", sa.String(), nullable=True)
    )
    op.create_index(
        op.f("ix_biological_targets_gene_id"),
        "biological_targets",
        ["gene_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_biological_targets_gene_name"),
        "biological_targets",
        ["gene_name"],
        unique=False,
    )

    # Add action data columns to compound_targets table
    op.add_column("compound_targets", sa.Column("action", sa.String(), nullable=True))
    op.add_column(
        "compound_targets", sa.Column("action_type", sa.String(), nullable=True)
    )
    op.add_column(
        "compound_targets", sa.Column("action_value", sa.Float(), nullable=True)
    )
    op.add_column("compound_targets", sa.Column("evidence", sa.String(), nullable=True))
    op.add_column(
        "compound_targets", sa.Column("evidence_urls", sa.String(), nullable=True)
    )


def downgrade() -> None:
    # Remove action data columns from compound_targets table
    op.drop_column("compound_targets", "evidence_urls")
    op.drop_column("compound_targets", "evidence")
    op.drop_column("compound_targets", "action_value")
    op.drop_column("compound_targets", "action_type")
    op.drop_column("compound_targets", "action")

    # Remove gene fields from biological_targets table
    op.drop_index(
        op.f("ix_biological_targets_gene_name"), table_name="biological_targets"
    )
    op.drop_index(
        op.f("ix_biological_targets_gene_id"), table_name="biological_targets"
    )
    op.drop_column("biological_targets", "gene_name")
    op.drop_column("biological_targets", "gene_id")
