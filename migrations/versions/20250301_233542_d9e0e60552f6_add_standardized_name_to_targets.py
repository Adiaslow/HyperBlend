"""add standardized name to targets

Revision ID: d9e0e60552f6
Revises: 
Create Date: 2025-03-01 23:35:42.123456

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d9e0e60552f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add standardized_name column to biological_targets table
    op.add_column("biological_targets", sa.Column("standardized_name", sa.String()))


def downgrade() -> None:
    # Remove standardized_name column from biological_targets table
    op.drop_column("biological_targets", "standardized_name")
