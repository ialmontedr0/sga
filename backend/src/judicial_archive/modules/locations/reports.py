from __future__ import annotations

import csv
import io
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.modules.locations.services import occupancy_report


def _csv_safe(value: object) -> str:
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{text}"
    return text


async def occupancy_csv(
    session: AsyncSession,
    *,
    area_id: UUID | None,
    shelf_id: UUID | None,
) -> str:
    report = await occupancy_report(session, area_id=area_id, shelf_id=shelf_id)
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "area_code",
            "area_name",
            "shelf_code",
            "shelf_name",
            "configured_capacity",
            "visible_capacity",
            "occupied_positions",
            "available_positions",
            "blocked_positions",
            "retired_positions",
            "occupancy_rate",
            "capacity_matches",
        ]
    )
    for row in report.rows:
        writer.writerow(
            [
                _csv_safe(row.area_code),
                _csv_safe(row.area_name),
                _csv_safe(row.shelf_code),
                _csv_safe(row.shelf_name or ""),
                row.configured_capacity,
                row.visible_capacity,
                row.occupied_positions,
                row.available_positions,
                row.blocked_positions,
                row.retired_positions,
                row.occupancy_rate,
                "true" if row.capacity_matches else "false",
            ]
        )
    return output.getvalue()
