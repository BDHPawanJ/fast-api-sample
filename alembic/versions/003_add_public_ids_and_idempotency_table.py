"""add public ids and idempotency table

Revision ID: 003
Revises: 002
Create Date: 2026-09-03 19:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add public UUID IDs and persisted idempotency key table."""
    bind = op.get_bind()

    def has_table(table_name: str) -> bool:
        return sa.inspect(bind).has_table(table_name)

    def has_column(table_name: str, column_name: str) -> bool:
        columns = sa.inspect(bind).get_columns(table_name)
        return any(column["name"] == column_name for column in columns)

    def has_index(table_name: str, index_name: str) -> bool:
        indexes = sa.inspect(bind).get_indexes(table_name)
        return any(index["name"] == index_name for index in indexes)

    if not has_column("users", "public_id"):
        op.add_column("users", sa.Column("public_id", sa.String(length=36), nullable=True))
    if not has_column("products", "public_id"):
        op.add_column(
            "products", sa.Column("public_id", sa.String(length=36), nullable=True)
        )

    op.execute("UPDATE users SET public_id = UUID() WHERE public_id IS NULL")
    op.execute("UPDATE products SET public_id = UUID() WHERE public_id IS NULL")

    op.alter_column(
        "users",
        "public_id",
        existing_type=sa.String(length=36),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "products",
        "public_id",
        existing_type=sa.String(length=36),
        existing_nullable=True,
        nullable=False,
    )

    if not has_index("users", op.f("ix_users_public_id")):
        op.create_index(op.f("ix_users_public_id"), "users", ["public_id"], unique=True)
    if not has_index("products", op.f("ix_products_public_id")):
        op.create_index(
            op.f("ix_products_public_id"), "products", ["public_id"], unique=True
        )

    if not has_table("idempotency_keys"):
        op.create_table(
            "idempotency_keys",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("key", sa.String(length=128), nullable=False),
            sa.Column("operation", sa.String(length=100), nullable=False),
            sa.Column("request_hash", sa.String(length=64), nullable=False),
            sa.Column("principal_id", sa.String(length=36), nullable=True),
            sa.Column("response_status", sa.Integer(), nullable=False),
            sa.Column("response_body", sa.Text(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if not has_index("idempotency_keys", op.f("ix_idempotency_keys_key")):
        op.create_index(
            op.f("ix_idempotency_keys_key"), "idempotency_keys", ["key"], unique=False
        )
    if not has_index("idempotency_keys", op.f("ix_idempotency_keys_operation")):
        op.create_index(
            op.f("ix_idempotency_keys_operation"),
            "idempotency_keys",
            ["operation"],
            unique=False,
        )
    if not has_index("idempotency_keys", op.f("ix_idempotency_keys_principal_id")):
        op.create_index(
            op.f("ix_idempotency_keys_principal_id"),
            "idempotency_keys",
            ["principal_id"],
            unique=False,
        )


def downgrade() -> None:
    """Drop idempotency key table and public UUID IDs."""
    bind = op.get_bind()

    def has_table(table_name: str) -> bool:
        return sa.inspect(bind).has_table(table_name)

    def has_column(table_name: str, column_name: str) -> bool:
        if not has_table(table_name):
            return False
        columns = sa.inspect(bind).get_columns(table_name)
        return any(column["name"] == column_name for column in columns)

    def has_index(table_name: str, index_name: str) -> bool:
        if not has_table(table_name):
            return False
        indexes = sa.inspect(bind).get_indexes(table_name)
        return any(index["name"] == index_name for index in indexes)

    if has_index("idempotency_keys", op.f("ix_idempotency_keys_principal_id")):
        op.drop_index(
            op.f("ix_idempotency_keys_principal_id"), table_name="idempotency_keys"
        )
    if has_index("idempotency_keys", op.f("ix_idempotency_keys_operation")):
        op.drop_index(op.f("ix_idempotency_keys_operation"), table_name="idempotency_keys")
    if has_index("idempotency_keys", op.f("ix_idempotency_keys_key")):
        op.drop_index(op.f("ix_idempotency_keys_key"), table_name="idempotency_keys")
    if has_table("idempotency_keys"):
        op.drop_table("idempotency_keys")

    if has_index("products", op.f("ix_products_public_id")):
        op.drop_index(op.f("ix_products_public_id"), table_name="products")
    if has_index("users", op.f("ix_users_public_id")):
        op.drop_index(op.f("ix_users_public_id"), table_name="users")
    if has_column("products", "public_id"):
        op.drop_column("products", "public_id")
    if has_column("users", "public_id"):
        op.drop_column("users", "public_id")
