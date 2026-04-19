"""Add email column

Revision ID: def456
Revises: abc123
Create Date: 2024-01-15 11:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "def456"
down_revision: Union[str, None] = "abc123"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "email")
