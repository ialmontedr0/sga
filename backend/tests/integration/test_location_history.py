from __future__ import annotations

import pytest
from sqlalchemy import delete, text, update
from sqlalchemy.exc import DBAPIError

from judicial_archive.modules.boxes.models import BoxLocationHistory

pytestmark = pytest.mark.integration


async def _execute_and_commit(session, statement) -> None:
    await session.execute(statement)
    await session.commit()


async def _seed_history(db_session, tree):
    row = BoxLocationHistory(
        box_id=tree.box_ids[0],
        to_custody_status="UNKNOWN",
        to_location_precision="UNKNOWN",
        reason="Historial de prueba",
    )
    db_session.add(row)
    await db_session.commit()
    return row


async def test_history_accepts_insert(db_session, location_tree) -> None:
    row = await _seed_history(db_session, location_tree)

    stored = await db_session.get(BoxLocationHistory, row.id)

    assert stored is not None
    assert stored.reason == "Historial de prueba"


async def test_history_rejects_update(db_session, location_tree) -> None:
    row = await _seed_history(db_session, location_tree)

    with pytest.raises(DBAPIError):
        await _execute_and_commit(
            db_session,
            update(BoxLocationHistory)
            .where(BoxLocationHistory.id == row.id)
            .values(reason="alterado"),
        )
    await db_session.rollback()


async def test_history_rejects_delete(db_session, location_tree) -> None:
    row = await _seed_history(db_session, location_tree)

    with pytest.raises(DBAPIError):
        await _execute_and_commit(
            db_session,
            delete(BoxLocationHistory).where(BoxLocationHistory.id == row.id),
        )
    await db_session.rollback()


async def test_history_rejects_truncate(db_session) -> None:
    with pytest.raises(DBAPIError):
        await _execute_and_commit(db_session, text("TRUNCATE TABLE box_location_history"))
    await db_session.rollback()
