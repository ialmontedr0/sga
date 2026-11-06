"""case party uniqueness

Revision ID: 20261105_0002
Revises: 20261102_0002
Create Date: 2026-11-05 12:24:38.013115

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20261105_0002"
down_revision: str | Sequence[str] | None = "20261102_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_case_parties_case_person_role",
        "case_parties",
        ["case_file_id", "person_id", "party_role_id"],
        unique=True,
    )
    op.create_index(
        "ix_admin_documents_box_year",
        "administrative_documents",
        ["box_id", "document_year"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_admin_documents_box_year", table_name="administrative_documents")
    op.drop_index("uq_case_parties_case_person_role", table_name="case_parties")
