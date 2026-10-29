from __future__ import annotations

import asyncio

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.config import get_settings
from judicial_archive.core.enums import CatalogStatus
from judicial_archive.db.session import Database
from judicial_archive.modules.users.models import Permission, Role, RolePermission

SEED_RBAC_LOCK_KEY = 20261027

ROLE_NAMES: dict[str, str] = {
    "ADMINISTRADOR": "Administrador",
    "SUPERVISOR": "Supervisor",
    "ARCHIVISTA": "Archivista",
    "DIGITALIZADOR": "Digitalizador",
    "CONSULTA": "Usuario de consulta",
}

PERMISSIONS: tuple[tuple[str, str, str], ...] = (
    ("users.read", "Consultar usuarios", "Listar y consultar usuarios."),
    ("users.create", "Crear usuarios", "Dar de alta usuarios."),
    ("users.update", "Actualizar usuarios", "Modificar datos de usuarios."),
    ("users.delete", "Desactivar usuarios", "Aplicar baja logica a usuarios."),
    ("users.lock", "Bloquear usuarios", "Bloquear o desbloquear cuentas."),
    (
        "users.reset_password",
        "Restablecer contrasenas",
        "Asignar una contrasena temporal y forzar cambio.",
    ),
    ("roles.read", "Consultar roles", "Listar roles y sus permisos."),
    ("roles.manage", "Gestionar roles", "Crear y modificar roles."),
    ("permissions.read", "Consultar permisos", "Listar el catalogo de permisos."),
    ("permissions.manage", "Gestionar permisos", "Crear permisos nuevos."),
    ("sessions.read", "Consultar sesiones", "Ver sesiones activas por usuario."),
    ("sessions.manage", "Revocar sesiones", "Revocar sesiones de cualquier usuario."),
    ("audit.read", "Consultar auditoria", "Leer eventos de seguridad y auditoria."),
    ("catalog.read", "Consultar catalogos", "Ver tribunales, areas y anaqueles."),
    ("catalog.manage", "Gestionar catalogos", "Crear y modificar catalogos."),
    ("search.read", "Busqueda global", "Ejecutar busquedas autorizadas."),
    ("boxes.read", "Consultar cajas", "Ver cajas y su ubicacion."),
    ("boxes.create", "Crear cajas", "Registrar cajas nuevas."),
    ("boxes.update", "Actualizar cajas", "Editar metadatos de cajas."),
    ("boxes.delete", "Dar de baja cajas", "Aplicar baja logica a cajas."),
    ("cases.read", "Consultar expedientes", "Ver expedientes judiciales."),
    ("cases.create", "Crear expedientes", "Registrar expedientes."),
    ("cases.update", "Actualizar expedientes", "Editar expedientes."),
    ("documents.read", "Consultar documentos", "Ver documentos administrativos."),
    ("documents.manage", "Gestionar documentos", "Crear y editar documentos."),
    ("files.read", "Consultar archivos", "Ver metadatos de archivos."),
    ("files.upload", "Subir archivos", "Cargar archivos al almacenamiento privado."),
    ("files.download", "Descargar archivos", "Descargar archivos autorizados."),
    ("imports.read", "Consultar importaciones", "Ver lotes de importacion."),
    ("imports.create", "Crear importaciones", "Cargar lotes de importacion."),
    ("imports.approve", "Aprobar importaciones", "Aprobar la aplicacion de un lote."),
    ("ocr.review", "Revisar OCR", "Validar y corregir resultados de OCR."),
    ("loans.read", "Consultar prestamos", "Ver prestamos y vencimientos."),
    ("loans.manage", "Gestionar prestamos", "Registrar y cerrar prestamos."),
    ("movements.read", "Consultar movimientos", "Ver traslados y devoluciones."),
    (
        "movements.manage",
        "Gestionar movimientos",
        "Registrar traslados y devoluciones.",
    ),
    ("inventory.read", "Consultar inventario", "Ver sesiones y diferencias."),
    ("inventory.manage", "Gestionar inventario", "Ejecutar conciliaciones."),
    ("reports.read", "Consultar reportes", "Ver reportes autorizados."),
    ("reports.export", "Exportar reportes", "Generar Excel, CSV y PDF."),
    ("settings.read", "Consultar configuracion", "Ver politicas del sistema."),
    ("settings.manage", "Gestionar configuracion", "Modificar politicas del sistema."),
)

ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "ADMINISTRADOR": tuple(code for code, _, _ in PERMISSIONS),
    "SUPERVISOR": (
        "users.read",
        "roles.read",
        "permissions.read",
        "sessions.read",
        "sessions.manage",
        "audit.read",
        "catalog.read",
        "catalog.manage",
        "search.read",
        "boxes.read",
        "boxes.create",
        "boxes.update",
        "cases.read",
        "cases.create",
        "cases.update",
        "documents.read",
        "documents.manage",
        "files.read",
        "files.upload",
        "files.download",
        "imports.read",
        "imports.create",
        "imports.approve",
        "ocr.review",
        "loans.read",
        "loans.manage",
        "movements.read",
        "movements.manage",
        "inventory.read",
        "inventory.manage",
        "reports.read",
        "reports.export",
        "settings.read",
    ),
    "ARCHIVISTA": (
        "catalog.read",
        "search.read",
        "boxes.read",
        "boxes.create",
        "boxes.update",
        "cases.read",
        "cases.create",
        "cases.update",
        "documents.read",
        "documents.manage",
        "files.read",
        "files.upload",
        "files.download",
        "imports.read",
        "imports.create",
        "loans.read",
        "loans.manage",
        "movements.read",
        "movements.manage",
        "inventory.read",
        "inventory.manage",
        "reports.read",
    ),
    "DIGITALIZADOR": (
        "catalog.read",
        "search.read",
        "boxes.read",
        "cases.read",
        "documents.read",
        "files.read",
        "files.upload",
        "files.download",
        "imports.read",
        "imports.create",
        "ocr.review",
    ),
    "CONSULTA": (
        "catalog.read",
        "search.read",
        "boxes.read",
        "cases.read",
        "documents.read",
        "files.read",
        "files.download",
        "reports.read",
    ),
}


async def _ensure_role(session: AsyncSession, code: str, name: str) -> Role:
    role = await session.scalar(select(Role).where(Role.code == code))
    if role is None:
        role = Role(
            code=code,
            name=name,
            description=None,
            is_system=True,
            status=CatalogStatus.ACTIVE.value,
        )
        session.add(role)
        await session.flush()
        return role

    # Los roles creados por el seed antiguo pueden tener is_system=False
    changed = False
    if not role.is_system:
        role.is_system = True
        changed = True
    if role.status != CatalogStatus.ACTIVE.value:
        role.status = CatalogStatus.ACTIVE.value
        changed = True
    if changed:
        await session.flush()
    return role


async def _ensure_permission(
    session: AsyncSession,
    code: str,
    name: str,
    description: str,
) -> Permission:
    permission = await session.scalar(select(Permission).where(Permission.code == code))
    if permission is None:
        permission = Permission(code=code, name=name, description=description)
        session.add(permission)
        await session.flush()
        return permission

    changed = False
    if permission.name != name:
        permission.name = name
        changed = True
    if permission.description != description:
        permission.description = description
        changed = True
    if changed:
        await session.flush()
    return permission


async def seed_rbac(session: AsyncSession) -> None:
    """Aplica catalogo de permisos y matriz rol-permiso de forma idempotente.

    No elimina permisos ni asociaciones existentes:
    solo inserta lo que falta.
    El llamador responsable del commit

    Args:
        session (AsyncSession): Sesion predefinida
    """

    await session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"), {"lock_key": SEED_RBAC_LOCK_KEY}
    )

    roles = {code: await _ensure_role(session, code, name) for code, name in ROLE_NAMES.items()}
    permissions = {
        code: await _ensure_permission(session, code, name, description)
        for code, name, description in PERMISSIONS
    }

    rows = await session.execute(select(RolePermission.role_id, RolePermission.permission_id))
    existing = {(row[0], row[1]) for row in rows.all()}

    for role_code, permission_codes in ROLE_PERMISSIONS.items():
        role = roles[role_code]
        for permission_code in permission_codes:
            key = (role.id, permissions[permission_code].id)
            if key in existing:
                continue
            session.add(
                RolePermission(
                    role_id=role.id,
                    permission_id=permissions[permission_code].id,
                    granted_by=None,
                )
            )
            existing.add(key)


async def main() -> None:
    settings = get_settings()
    database = Database(settings)
    try:
        async with database.session() as session:
            await seed_rbac(session)
            await session.commit()
    finally:
        await database.dispose()
    print("RBAC aplicado correctamente")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
