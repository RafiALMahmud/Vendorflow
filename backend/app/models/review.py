"""Review tables share Developer 1's ORM Base and identity keys."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Application(Base):
    __tablename__ = 'applications'
    __table_args__ = (
        CheckConstraint("status IN ('draft','submitted','needs_correction','resubmitted','approved','rejected')", name='ck_application_status'),
        CheckConstraint('version >= 0', name='ck_application_version'),
        Index('uq_active_application_vendor', 'vendor_id', unique=True,
              postgresql_where=text("status IN ('draft','submitted','needs_correction','resubmitted')")),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    vendor_id: Mapped[UUID] = mapped_column(ForeignKey('vendors.id', ondelete='CASCADE'), index=True)
    status: Mapped[str] = mapped_column(String(30), default='draft', index=True)
    version: Mapped[int] = mapped_column(Integer, default=0)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer_user_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    correction_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RiskAssessmentRecord(Base):
    __tablename__ = 'risk_assessments'
    __table_args__ = (CheckConstraint('score >= 0 AND score <= 100', name='ck_risk_score'),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    application_id: Mapped[UUID] = mapped_column(ForeignKey('applications.id', ondelete='CASCADE'), index=True)
    score: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(40))
    findings_json: Mapped[list] = mapped_column(JSON)
    rules_version: Mapped[str] = mapped_column(String(100))
    snapshot_json: Mapped[dict] = mapped_column(JSON)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    application_id: Mapped[UUID] = mapped_column(ForeignKey('applications.id', ondelete='CASCADE'), index=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    action: Mapped[str] = mapped_column(String(40))
    before_json: Mapped[dict] = mapped_column(JSON)
    after_json: Mapped[dict] = mapped_column(JSON)
    note: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
