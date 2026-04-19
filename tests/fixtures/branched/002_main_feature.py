"""Main branch feature

Revision ID: main002
Revises: base001
Create Date: 2024-01-15 11:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "main002"
down_revision: Union[str, None] = "base001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("base_table", sa.Column("main_col", sa.String()))


def downgrade() -> None:
    op.drop_column("base_table", "main_col")
