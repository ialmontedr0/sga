"""area code unique

Revision ID: 8c8fec15b660
Revises: 88ae4fe9cb05
Create Date: 2026-10-29 14:35:08.460757

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "<rev>"
down_revision: str | Sequence[str] | None = "88ae4fe9cb05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint("uq_areas_code", "areas", ["code"])


def downgrade() -> None:
    op.drop_constraint("uq_areas_code", "areas", type_="unique")
