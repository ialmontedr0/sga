from __future__ import annotations

import asyncio
import getpass
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from judicial_archive.core.config import get_settings
from judicial_archive.core.enums import UserStatus
from judicial_archive.core.security import hash_password
from judicial_archive.modules.auth.models import SecurityEvent
from judicial_archive.modules.users.models import Role, User, UserRole

# Añadir src al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))


async def main() -> None:
    print("=== ALTA SEGURA DE ADMINISTRADOR - SGA ===")
    print("Este script NO usa contraseñas por defecto.")
    print()

    username = input("Usuario (3-64): ").strip()
    if len(username) < 3 or len(username) > 64:
        print("Usuario inválido (3-64 caracteres)")
        sys.exit(1)

    email_input = input("Email (opcional, dejar vacío para omitir): ").strip()
    email = email_input or None

    display_name = input("Nombre completo: ").strip()
    if not display_name or len(display_name) < 1:
        print("Nombre requerido")
        sys.exit(1)

    while True:
        try:
            pwd1 = getpass.getpass("Contraseña (mínimo 12 caracteres): ")
        except Exception:
            pwd1 = input("Contraseña (mínimo 12 caracteres): ")
        if len(pwd1) < 12:
            print("Mínimo 12 caracteres")
            continue
        try:
            pwd2 = getpass.getpass("Confirmar contraseña: ")
        except Exception:
            pwd2 = input("Confirmar contraseña: ")
        if pwd1 != pwd2:
            print("Las contraseñas no coinciden")
            continue
        break

    settings = get_settings()
    engine = create_async_engine(str(settings.database_url), echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with SessionLocal() as session:
            async with session.begin():
                # Verificar usuario existente
                res = await session.execute(
                    select(User).where(User.username_normalized == username.lower())
                )
                if res.scalar_one_or_none():
                    print("ERROR: El usuario ya existe")
                    sys.exit(1)

                # Verificar email existente
                if email:
                    res = await session.execute(
                        select(User).where(User.email_normalized == email.lower())
                    )
                    if res.scalar_one_or_none():
                        print("ERROR: El email ya existe")
                        sys.exit(1)

                # Buscar rol Administrador
                res = await session.execute(select(Role).where(Role.code == "ADMINISTRADOR"))
                role = res.scalar_one_or_none()
                if not role:
                    print("ERROR: Rol 'ADMINISTRADOR' no existe.")
                    print(
                        "Asegúrate de haber ejecutado las migraciones: uv run alembic upgrade head"
                    )
                    sys.exit(1)

                # Crear usuario
                user = User(
                    username=username,
                    username_normalized=username.lower(),
                    email=email,
                    email_normalized=email.lower() if email else None,
                    display_name=display_name,
                    password_hash=hash_password(pwd1),
                    status=UserStatus.ACTIVE.value,
                    must_change_password=False,
                    failed_login_count=0,
                    locked_until=None,
                )
                session.add(user)
                await session.flush()

                # Asignar rol
                session.add(UserRole(user_id=user.id, role_id=role.id))
                # Evento de seguridad
                session.add(
                    SecurityEvent(
                        event_type="admin_created_via_script",
                        user_id=user.id,
                        actor_id=None,
                        details={"username": username, "created_by": "script"},
                    )
                )

            print()
            print("✅ Administrador creado correctamente")
            print(f"   Usuario: {username}")
            print(f"   ID: {user.id}")
            print(f"   Email: {email or '(sin email)'}")
            print()
            print("Recuerde: no compartir credenciales y usar mínimo privilegio.")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(
        main(),
        loop_factory=asyncio.SelectorEventLoop,
    )
