"""Feature A continued

Revision ID: featA003
Revises: featA002
Create Date: 2024-01-15 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "featA003"
down_revision: Union[str, None] = "featA002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("idx_feature_a", "base_table", ["feature_a_col"])


def downgrade() -> None:
    op.drop_index("idx_feature_a", "base_table")
