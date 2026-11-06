from __future__ import annotations

from judicial_archive.core.enums import BoxType, CustodyStatus, MovementStatus

ACTIVE_LOCATION_CUSTODY_STATUSES = frozenset(
    {
        CustodyStatus.IN_PLACE.value,
        CustodyStatus.IN_RECONCILIATION.value,
        CustodyStatus.PENDING_VERIFICATION.value,
    }
)

OPEN_MOVEMENT_STATUSES = frozenset(
    {
        MovementStatus.PLANNED.value,
        MovementStatus.IN_TRANSIT.value,
    }
)

CUSTODY_WITH_POSITION_SQL = (
    "custody_status IN ('IN_PLACE', 'IN_RECONCILIATION', 'PENDING_VERIFICATION') "
    "AND current_position_id IS NOT NULL"
)
CUSTODY_WITHOUT_POSITION_SQL = (
    "custody_status NOT IN ('IN_PLACE', 'IN_RECONCILIATION', 'PENDING_VERIFICATION') "
    "AND current_position_id IS NULL"
)
CONTENT_TYPE_BY_BOX_TYPE = {
    BoxType.EXPEDIENTES.value: "CASE_FILE",
    BoxType.DOCUMENTOS_ADMINISTRATIVOS.value: "ADMINISTRATIVE_DOCUMENT",
}

BOX_MUTABLE_FIELDS = frozenset({"description", "confidentiality"})
BOX_IMMUTABLE_FIELDS = frozenset({"court_id", "year", "box_type", "visible_number"})
