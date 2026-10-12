"""store product price as DECIMAL(10, 2)

Revision ID: 005
Revises: 004
Create Date: 2026-10-12 12:00:00.000000

MySQL FLOAT is single precision, so a stored 999.99 reads back as
999.989990234375. Converting to DECIMAL rounds existing values to the
nearest cent, which restores the prices that were originally submitted.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'products',
        'price',
        existing_type=sa.Float(),
        type_=sa.Numeric(precision=10, scale=2),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'products',
        'price',
        existing_type=sa.Numeric(precision=10, scale=2),
        type_=sa.Float(),
        existing_nullable=False,
    )
