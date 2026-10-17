"""Create vendor profiles.

Revision ID: 0003_create_vendors
Revises: 0002_create_users
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_create_vendors"
down_revision: str | None = "0002_create_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vendors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("registration_number", sa.String(length=100), nullable=False),
        sa.Column("contact_email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_vendors_owner_user_id",
        "vendors",
        ["owner_user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_vendors_owner_user_id", table_name="vendors")
    op.drop_table("vendors")
