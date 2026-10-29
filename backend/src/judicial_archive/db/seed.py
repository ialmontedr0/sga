from __future__ import annotations

import asyncio

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.config import get_settings
from judicial_archive.core.enums import CatalogStatus
from judicial_archive.db.base import Base
from judicial_archive.db.seed_rbac import seed_rbac
from judicial_archive.db.session import Database
from judicial_archive.modules.courts.models import (
    Court,
    NumberingPolicy,
    PartyRole,
    SystemSetting,
)
from judicial_archive.modules.locations.models import Area, Shelf
from judicial_archive.modules.users.models import Role

SEED_LOCK_KEY = 20261026

ROLES = (
    ("ADMINISTRADOR", "Administrador"),
    ("SUPERVISOR", "Supervisor"),
    ("ARCHIVISTA", "Archivista"),
    ("DIGITALIZADOR", "Digitalizador"),
    ("CONSULTA", "Usuario de consulta"),
)

AREAS = (("A", "Zona A"), ("B", "Zona B"), ("C", "Zona C"), ("D", "Zona D"), ("O", "Zona O"))

SHELVES = {"A": 9, "B": 8, "C": 6, "D": 13, "O": 3}

COURTS = (
    {
        "code_raw": "589",
        "name": "Juzgado de Instruccion",
        "status": "ACTIVE",
        "notes": "Activo.",
    },
    {
        "code_raw": "589",
        "name": "Juzgao de Instruccion en Atencion Permanente",
        "status": "ACTIVE",
        "notes": "Activo.",
    },
    {
        "code_raw": "102",
        "name": "Camara Penal de la Corte de Apelacion",
        "status": "ACTIVE",
        "notes": "Activo.",
    },
    {
        "code_raw": "106",
        "name": "Primera Camara Penal del Juzgado de Primera Instancia",
        "status": "INACTIVE",
        "notes": "Inactivo.",
    },
    {
        "code_raw": "107",
        "name": "Segunda Camara Penal del Juzgado de Primera Instancia",
        "status": "INACTIVE",
        "notes": "Inactivo.",
    },
    {
        "code_raw": "107",
        "name": "Juzgado de Primera Instancia Unipersonal",
        "status": "ACTIVE",
        "notes": "Activo.",
    },
    {
        "code_raw": "107-01",
        "name": "Tribunal de Ejecucion de la Pena",
        "status": "ACTIVE",
        "notes": "Activo.",
    },
    {
        "code_raw": "107-02",
        "name": "Tribunal Colegiado de Primera Instancia",
        "status": "ACTIVE",
        "notes": "Activo.",
    },
)


async def _existing(session: AsyncSession, model: type[Base], **filters: object) -> Base | None:
    statement = select(model).filter_by(**filters)
    return await session.scalar(statement)


async def _ensure_role(session: AsyncSession, code: str, name: str) -> None:
    if await _existing(session, Role, code=code) is not None:
        return
    session.add(
        Role(
            code=code,
            name=name,
            description=None,
            is_system=True,
            status=CatalogStatus.ACTIVE.value,
        )
    )


async def _ensure_area(session: AsyncSession, code: str, name: str) -> None:
    if await _existing(session, Area, code=code) is not None:
        return
    session.add(Area(code=code, name=name, description=None, status="ACTIVE"))


async def _ensure_shelf(
    session: AsyncSession,
    area: Area,
    code: str,
) -> None:
    if await _existing(session, Shelf, area_id=area.id, code=code) is not None:
        return
    session.add(
        Shelf(
            area_id=area.id,
            code=code,
            name=f"Anaquel {code}",
            levels=None,
            positions_per_level=None,
            status="ACTIVE",
            notes="Capacidad pendiente de confirmacion.",
        )
    )


async def _ensure_court(session: AsyncSession, data: dict[str, str]) -> None:
    code_raw = data["code_raw"]
    existing = await session.scalar(
        select(Court).where(Court.code_raw == code_raw, Court.name == data["name"])
    )
    if existing is not None:
        return
    session.add(
        Court(
            code_raw=code_raw,
            code_normalized=code_raw.strip().upper(),
            name=data["name"],
            court_type=None,
            jurisdiction=None,
            status=data["status"],
            effective_from=None,
            effective_to=None,
            source="B1",
            notes=data["notes"],
        )
    )


async def _ensure_party_role(session: AsyncSession) -> None:
    if await _existing(session, PartyRole, code="IMPUTADO") is not None:
        return
    session.add(
        PartyRole(
            code="IMPUTADO",
            name="Imputado",
            description="Rol de parte confirmado para B1.",
            is_system=True,
            status=CatalogStatus.ACTIVE.value,
        )
    )


async def _ensure_numbering_policy(session: AsyncSession) -> None:
    if await _existing(session, NumberingPolicy, code="BOX_GLOBAL") is not None:
        return
    session.add(
        NumberingPolicy(
            code="BOX_GLOBAL",
            description="Numeracion global inicial de cajas.",
            scope="GLOBAL",
            court_id=None,
            box_type=None,
            year=None,
            sequence_name="box_visible_number_seq",
            prefix=None,
            suffix=None,
            padding=0,
            start_value=4402,
            step=1,
            reset_policy="NEVER",
            is_active=True,
            effective_to=None,
            notes="La secuencia es la fuente de verdad del proximo numero.",
        )
    )


async def _ensure_timezone_setting(session: AsyncSession) -> None:
    if await _existing(session, SystemSetting, key="system.timezone") is not None:
        return
    session.add(
        SystemSetting(
            key="system.timezone",
            value="America/Santo_Domingo",
            value_type="STRING",
            description="Zona horaria de presentacion del sistema.",
            updated_by=None,
        )
    )


async def seed_database(session: AsyncSession) -> None:
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"), {"lock_key": SEED_LOCK_KEY}
    )

    for code, name in ROLES:
        await _ensure_role(session, code, name)

    for code, name in AREAS:
        await _ensure_area(session, code, name)
    await session.flush()

    for area_code, count in SHELVES.items():
        area = await session.scalar(select(Area).where(Area.code == area_code))
        if area is None:
            raise RuntimeError(f"No se encontro el area {area_code}")
        for number in range(1, count + 1):
            await _ensure_shelf(session, area, f"{area_code}{number}")

    for court_data in COURTS:
        await _ensure_court(session, court_data)

    await _ensure_party_role(session)
    await _ensure_numbering_policy(session)
    await _ensure_timezone_setting(session)

    # permisos y matriz rol-permiso
    await seed_rbac(session)

    await session.commit()


async def main() -> None:
    settings = get_settings()
    database = Database(settings)
    try:
        async with database.session() as session:
            await seed_database(session)
    finally:
        await database.dispose()
    print("Semillas aplicadas correctamente")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(
        main(),
        loop_factory=asyncio.SelectorEventLoop,
    )
