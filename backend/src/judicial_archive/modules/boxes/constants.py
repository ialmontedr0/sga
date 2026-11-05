from __future__ import annotations

from judicial_archive.core.enums import CustodyStatus, MovementStatus

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
