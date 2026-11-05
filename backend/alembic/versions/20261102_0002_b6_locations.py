"""B6 locations, history and movement constraints

Revision ID: 20261102_0002
Revises: 8c8fec15b660
Create Date: 2026-11-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261102_0002"
down_revision: Union[str, Sequence[str], None] = "8c8fec15b660"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CUSTODY_VALUES = (
    "'IN_PLACE', 'ON_LOAN', 'IN_TRANSIT', 'MISSING', "
    "'IN_RECONCILIATION', 'PENDING_VERIFICATION', 'UNKNOWN'"
)
ACTIVE_CUSTODY = "'IN_PLACE', 'IN_RECONCILIATION', 'PENDING_VERIFICATION'"
MOVEMENT_TYPES = (
    "'ASSIGN', 'UNASSIGN', 'TRANSFER', 'RETURN', "
    "'LOAN_PICKUP', 'LOAN_RETURN', 'RECONCILIATION'"
)


def upgrade() -> None:
    op.drop_constraint("ck_boxes_custody_status", "boxes", type_="check")
    op.create_check_constraint(
        "ck_boxes_custody_status",
        "boxes",
        f"custody_status IN ({CUSTODY_VALUES})",
    )

    op.drop_constraint("ck_boxes_custody_position", "boxes", type_="check")
    op.create_check_constraint(
        "ck_boxes_custody_position",
        "boxes",
        "("
        f"(custody_status IN ({ACTIVE_CUSTODY}) AND current_position_id IS NOT NULL)"
        f" OR (custody_status NOT IN ({ACTIVE_CUSTODY}) AND current_position_id IS NULL)"
        ")",
    )

    op.drop_index("uq_boxes_current_position_occupied", table_name="boxes")
    op.create_index(
        "uq_boxes_current_position_occupied",
        "boxes",
        ["current_position_id"],
        unique=True,
        postgresql_where=sa.text(
            f"custody_status IN ({ACTIVE_CUSTODY}) AND current_position_id IS NOT NULL"
        ),
    )

    op.drop_constraint("ck_box_movements_type", "box_movements", type_="check")
    op.create_check_constraint(
        "ck_box_movements_type",
        "box_movements",
        f"movement_type IN ({MOVEMENT_TYPES})",
    )

    op.create_index(
        "uq_box_movements_open_box",
        "box_movements",
        ["box_id"],
        unique=True,
        postgresql_where=sa.text("movement_status IN ('PLANNED', 'IN_TRANSIT')"),
    )

    op.add_column(
        "position_blocks",
        sa.Column("cancellation_reason", sa.String(length=500), nullable=True),
    )
    op.create_check_constraint(
        "ck_position_blocks_cancellation_reason",
        "position_blocks",
        "cancelled_at IS NULL OR "
        "(cancellation_reason IS NOT NULL AND length(btrim(cancellation_reason)) > 0)",
    )

    op.create_table(
        "box_location_history",
        sa.Column("box_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("from_position_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("to_position_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("from_custody_status", sa.String(length=24), nullable=True),
        sa.Column("to_custody_status", sa.String(length=24), nullable=False),
        sa.Column("from_location_precision", sa.String(length=16), nullable=True),
        sa.Column("to_location_precision", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column(
            "source",
            sa.String(length=16),
            server_default="API",
            nullable=False,
        ),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(reason)) > 0",
            name="ck_box_location_history_reason_not_empty",
        ),
        sa.CheckConstraint(
            "from_custody_status IS NULL OR "
            f"from_custody_status IN ({CUSTODY_VALUES})",
            name="ck_box_location_history_from_custody",
        ),
        sa.CheckConstraint(
            f"to_custody_status IN ({CUSTODY_VALUES})",
            name="ck_box_location_history_to_custody",
        ),
        sa.CheckConstraint(
            "from_location_precision IS NULL OR "
            "from_location_precision IN ('CONFIRMED', 'PENDING', 'UNKNOWN')",
            name="ck_box_location_history_from_precision",
        ),
        sa.CheckConstraint(
            "to_location_precision IN ('CONFIRMED', 'PENDING', 'UNKNOWN')",
            name="ck_box_location_history_to_precision",
        ),
        sa.CheckConstraint(
            "source IN ('API', 'RECONCILIATION', 'IMPORT', 'SYSTEM', 'MIGRATION')",
            name="ck_box_location_history_source",
        ),
        sa.ForeignKeyConstraint(
            ["box_id"],
            ["boxes.id"],
            name="fk_box_location_history_box_id_boxes",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["movement_id"],
            ["box_movements.id"],
            name="fk_box_location_history_movement_id_box_movements",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["from_position_id"],
            ["positions.id"],
            name="fk_box_location_history_from_position_id_positions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["to_position_id"],
            ["positions.id"],
            name="fk_box_location_history_to_position_id_positions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by"],
            ["users.id"],
            name="fk_box_location_history_changed_by_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_box_location_history"),
    )
    op.create_index(
        "ix_box_location_history_box_changed",
        "box_location_history",
        ["box_id", "changed_at"],
        unique=False,
    )
    op.create_index(
        "ix_box_location_history_to_position",
        "box_location_history",
        ["to_position_id", "changed_at"],
        unique=False,
    )
    op.create_index(
        "ix_box_location_history_movement",
        "box_location_history",
        ["movement_id"],
        unique=False,
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION sga_location_history_append_only()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'box_location_history es append-only'
                USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$;
        """
    )
    op.execute(
        "CREATE TRIGGER trg_box_location_history_append_only "
        "BEFORE UPDATE OR DELETE ON box_location_history "
        "FOR EACH ROW EXECUTE FUNCTION sga_location_history_append_only()"
    )
    op.execute(
        "CREATE TRIGGER trg_box_location_history_no_truncate "
        "BEFORE TRUNCATE ON box_location_history "
        "FOR EACH STATEMENT EXECUTE FUNCTION sga_location_history_append_only()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_box_location_history_no_truncate "
        "ON box_location_history"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_box_location_history_append_only "
        "ON box_location_history"
    )
    op.execute("DROP FUNCTION IF EXISTS sga_location_history_append_only()")

    op.drop_index("ix_box_location_history_movement", table_name="box_location_history")
    op.drop_index(
        "ix_box_location_history_to_position",
        table_name="box_location_history",
    )
    op.drop_index(
        "ix_box_location_history_box_changed",
        table_name="box_location_history",
    )
    op.drop_table("box_location_history")

    op.drop_constraint(
        "ck_position_blocks_cancellation_reason",
        "position_blocks",
        type_="check",
    )
    op.drop_column("position_blocks", "cancellation_reason")

    op.drop_index("uq_box_movements_open_box", table_name="box_movements")

    op.drop_constraint("ck_box_movements_type", "box_movements", type_="check")
    op.create_check_constraint(
        "ck_box_movements_type",
        "box_movements",
        "movement_type IN ('ASSIGN', 'TRANSFER', 'RETURN', "
        "'LOAN_PICKUP', 'LOAN_RETURN', 'RECONCILIATION')",
    )

    op.drop_index("uq_boxes_current_position_occupied", table_name="boxes")
    op.create_index(
        "uq_boxes_current_position_occupied",
        "boxes",
        ["current_position_id"],
        unique=True,
        postgresql_where=sa.text(
            "custody_status IN ('IN_PLACE', 'IN_RECONCILIATION') "
            "AND current_position_id IS NOT NULL"
        ),
    )

    op.drop_constraint("ck_boxes_custody_position", "boxes", type_="check")
    op.create_check_constraint(
        "ck_boxes_custody_position",
        "boxes",
        "("
        "(custody_status IN ('IN_PLACE', 'IN_RECONCILIATION') "
        "AND current_position_id IS NOT NULL)"
        " OR (custody_status NOT IN ('IN_PLACE', 'IN_RECONCILIATION') "
        "AND current_position_id IS NULL)"
        ")",
    )

    op.drop_constraint("ck_boxes_custody_status", "boxes", type_="check")
    op.create_check_constraint(
        "ck_boxes_custody_status",
        "boxes",
        "custody_status IN ('IN_PLACE', 'ON_LOAN', 'IN_TRANSIT', "
        "'MISSING', 'IN_RECONCILIATION', 'UNKNOWN')",
    )
