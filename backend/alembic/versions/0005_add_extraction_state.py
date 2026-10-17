"""Add document extraction state and normalization details.

Revision ID: 0005_add_extraction_state
Revises: 0004_create_documents
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005_add_extraction_state"
down_revision: str | None = "0004_create_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("processing_error", sa.Text(), nullable=True))
    op.add_column(
        "extracted_fields", sa.Column("normalized_value", sa.Text(), nullable=True)
    )
    op.add_column(
        "extracted_fields", sa.Column("review_note", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("extracted_fields", "review_note")
    op.drop_column("extracted_fields", "normalized_value")
    op.drop_column("documents", "processing_error")
