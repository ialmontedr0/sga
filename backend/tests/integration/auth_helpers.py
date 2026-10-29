from __future__ import annotations

from collections.abc import Sequence

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from judicial_archive.core.enums import UserStatus
from judicial_archive.core.security import hash_password
from judicial_archive.db.seed_rbac import seed_rbac
from judicial_archive.modules.users.models import Role, User, UserRole

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "AdminPassword123!"
USER_PASSWORD = "UserPassword123!"


async def seed_user_with_role(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    username: str,
    password: str,
    role_code: str,
    display_name: str | None = None,
) -> None:
    async with session_factory() as session:
        await seed_rbac(session)
        role = await session.scalar(select(Role).where(Role.code == role_code))
        if role is None:
            raise AssertionError(f"Rol {role_code} no existe")

        user = User(
            username=username,
            username_normalized=username.lower(),
            email=None,
            email_normalized=None,
            display_name=display_name or username.title(),
            password_hash=hash_password(password),
            status=UserStatus.ACTIVE.value,
            must_change_password=False,
            failed_login_count=0,
        )
        session.add(user)
        await session.flush()
        session.add(UserRole(user_id=user.id, role_id=role.id, assigned_by=None))
        await session.commit()


async def seed_admin(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    username: str = ADMIN_USERNAME,
    password: str = ADMIN_PASSWORD,
) -> None:
    await seed_user_with_role(
        session_factory,
        username=username,
        password=password,
        role_code="ADMINISTRADOR",
        display_name="Administrador de prueba",
    )


def get_csrf(client: TestClient) -> str:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200, response.text
    token = response.json()["csrf_token"]
    assert isinstance(token, str) and token  # noqa: PT018
    return token


def csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("sga_csrf")
    assert token
    return {"X-CSRF-Token": token}


def login(client: TestClient, username: str, password: str) -> None:
    token = get_csrf(client)
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200, response.text


def logout(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    assert response.status_code == 200, response.text


def create_user(
    client: TestClient,
    *,
    username: str,
    password: str = USER_PASSWORD,
    role_codes: Sequence[str] = ("CONSULTA",),
) -> str:
    response = client.post(
        "/api/v1/users/",
        json={
            "username": username,
            "email": None,
            "display_name": username.title(),
            "password": password,
            "role_codes": list(role_codes),
            "must_change_password": False,
        },
        headers=csrf_headers(client),
    )
    assert response.status_code == 200, response.text
    listing = client.get("/api/v1/users/")
    assert listing.status_code == 200, listing.text
    for user in listing.json():
        if user["username"] == username:
            return str(user["id"])
    raise AssertionError(f"Usuario {username} no aparece en el listado")
