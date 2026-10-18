"""Create documents and extracted fields.

Revision ID: 0004_create_documents
Revises: 0003_create_vendors
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004_create_documents"
down_revision: str | None = "0003_create_vendors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vendor_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("storage_key", sa.String(length=80), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column(
            "processing_status",
            sa.String(length=20),
            server_default="uploaded",
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "document_type IN ('trade_license', 'business_registration', "
            "'tax_certificate', 'other')",
            name="ck_documents_document_type",
        ),
        sa.CheckConstraint(
            "processing_status IN ('uploaded', 'processing', 'processed', 'failed')",
            name="ck_documents_processing_status",
        ),
        sa.CheckConstraint("file_size > 0", name="ck_documents_file_size_positive"),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_documents_storage_key"),
    )
    op.create_index("ix_documents_vendor_id", "documents", ["vendor_id"])

    op.create_table(
        "extracted_fields",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("confirmed_value", sa.Text(), nullable=True),
        sa.Column(
            "review_status",
            sa.String(length=20),
            server_default="unreviewed",
            nullable=False,
        ),
        sa.Column("extraction_method", sa.String(length=50), nullable=True),
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
        sa.CheckConstraint(
            "review_status IN ('unreviewed', 'confirmed', 'corrected')",
            name="ck_extracted_fields_review_status",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id", "field_name", name="uq_extracted_fields_document_field"
        ),
    )
    op.create_index(
        "ix_extracted_fields_document_id", "extracted_fields", ["document_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_extracted_fields_document_id", table_name="extracted_fields")
    op.drop_table("extracted_fields")
    op.drop_index("ix_documents_vendor_id", table_name="documents")
    op.drop_table("documents")
