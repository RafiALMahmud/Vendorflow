"""add application risk and audit review tables

Revision ID: 0006_review
Revises: 0005_add_extraction_state
Create Date: 2026-10-18 15:58:18.831038
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0006_review'
down_revision: Union[str, None] = '0005_add_extraction_state'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('applications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('vendor_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reviewer_user_id', sa.Uuid(), nullable=True),
    sa.Column('correction_note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('draft','submitted','needs_correction','resubmitted','approved','rejected')", name='ck_application_status'),
    sa.CheckConstraint('version >= 0', name='ck_application_version'),
    sa.ForeignKeyConstraint(['reviewer_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_applications_status'), 'applications', ['status'], unique=False)
    op.create_index(op.f('ix_applications_vendor_id'), 'applications', ['vendor_id'], unique=False)
    op.create_index('uq_active_application_vendor', 'applications', ['vendor_id'], unique=True, postgresql_where=sa.text("status IN ('draft','submitted','needs_correction','resubmitted')"))
    op.create_table('audit_events',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('actor_user_id', sa.Uuid(), nullable=True),
    sa.Column('action', sa.String(length=40), nullable=False),
    sa.Column('before_json', sa.JSON(), nullable=False),
    sa.Column('after_json', sa.JSON(), nullable=False),
    sa.Column('note', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_events_application_id'), 'audit_events', ['application_id'], unique=False)
    op.create_table('risk_assessments',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('score', sa.Integer(), nullable=False),
    sa.Column('level', sa.String(length=40), nullable=False),
    sa.Column('findings_json', sa.JSON(), nullable=False),
    sa.Column('rules_version', sa.String(length=100), nullable=False),
    sa.Column('snapshot_json', sa.JSON(), nullable=False),
    sa.Column('assessed_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('score >= 0 AND score <= 100', name='ck_risk_score'),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_risk_assessments_application_id'), 'risk_assessments', ['application_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_risk_assessments_application_id'), table_name='risk_assessments')
    op.drop_table('risk_assessments')
    op.drop_index(op.f('ix_audit_events_application_id'), table_name='audit_events')
    op.drop_table('audit_events')
    op.drop_index('uq_active_application_vendor', table_name='applications', postgresql_where=sa.text("status IN ('draft','submitted','needs_correction','resubmitted')"))
    op.drop_index(op.f('ix_applications_vendor_id'), table_name='applications')
    op.drop_index(op.f('ix_applications_status'), table_name='applications')
    op.drop_table('applications')
