"""Feature A branch

Revision ID: featA002
Revises: base001
Create Date: 2024-01-15 11:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "featA002"
down_revision: Union[str, None] = "base001"
branch_labels: Union[str, Sequence[str], None] = ["feature-a"]
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("base_table", sa.Column("feature_a_col", sa.String()))


def downgrade() -> None:
    op.drop_column("base_table", "feature_a_col")
