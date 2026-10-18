"""Establish the Phase 0 migration baseline.

Revision ID: 0001_bootstrap
Revises:
"""

from collections.abc import Sequence


revision: str = "0001_bootstrap"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No tables are created until the owned Phase 1 identity migration."""


def downgrade() -> None:
    """The bootstrap revision has no schema changes to reverse."""
