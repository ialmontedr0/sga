from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    Field,
    PostgresDsn,
    RedisDsn,
    SecretStr,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
StorageBackend = Literal["local"]


class Settings(BaseSettings):
    """Configuracion tipada de la aplicacion, validada al arrancar."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SGA_",
        case_sensitive=False,
        extra="forbid",
        validate_default=True,
    )

    # Obligatorios: no tienen valor por defecto seguro.
    secret_key: SecretStr
    database_url: PostgresDsn
    redis_url: RedisDsn

    # Aplicacion
    app_name: str = "SGA - Sistema de Gestion Documental Judicial"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    docs_enabled: bool = False
    log_level: LogLevel = "INFO"
    log_json: bool = True

    # HTTP
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    trusted_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    request_id_header: str = Field(
        default="X-Request-ID",
        pattern=r"^[A-Za-z0-9-]{3,64}$",
    )
    max_request_body_bytes: int = Field(default=1_048_576, ge=1024, le=16_777_216)

    # Base de datos
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=20, ge=0, le=100)
    db_echo: bool = False
    db_pool_pre_ping: bool = True
    db_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)

    # Redis
    redis_socket_timeout_seconds: float = Field(default=3.0, gt=0, le=60)

    # Sesiones y CSRF (se implementan en B4)
    session_cookie_name: str = "sga_session"
    session_cookie_secure: bool = True
    session_idle_minutes: int = Field(default=30, ge=5, le=1440)
    session_absolute_hours: int = Field(default=12, ge=1, le=720)
    csrf_cookie_name: str = "sga_csrf"
    csrf_header_name: str = "X-CSRF-Token"

    # Tareas en segundo plano
    task_queue_name: str = "sga"
    task_max_jobs: int = Field(default=4, ge=1, le=64)
    task_job_timeout_seconds: int = Field(default=900, ge=10, le=86400)

    # Almacenamiento privado
    storage_backend: StorageBackend = "local"
    storage_root: Path = Path("var/storage")

    # Salud
    readiness_timeout_seconds: float = Field(default=3.0, gt=0, le=30)

    @field_validator("secret_key")
    @classmethod
    def _validate_secret_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            msg = "SGA_SECRET_KEY debe tener al menos 32 caracteres."
            raise ValueError(msg)
        return value

    @field_validator("api_v1_prefix")
    @classmethod
    def _validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/") or value.endswith("/"):
            msg = "SGA_API_V1_PREFIX debe comenzar con '/' y no terminar con '/'."
            raise ValueError(msg)
        return value

    @field_validator("cors_origins", "trusted_hosts", mode="before")
    @classmethod
    def _split_comma_separated(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("cors_origins")
    @classmethod
    def _validate_cors_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            if origin == "*":
                continue
            if not origin.startswith(("http://", "https://")):
                msg = f"Origen CORS invalido: {origin!r}; debe incluir esquema."
                raise ValueError(msg)
            if origin.endswith("/"):
                msg = f"Origen CORS invalido: {origin!r}; no debe terminar en '/'."
                raise ValueError(msg)
        return origins

    @model_validator(mode="after")
    def _validate_cors_credentials(self) -> Self:
        if any(origin.strip() == "*" for origin in self.cors_origins):
            msg = "SGA_CORS_ORIGINS no puede contener '*' porque se usan credenciales"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _validate_production_rules(self) -> Self:
        if self.environment is not Environment.PRODUCTION:
            return self

        problems: list[str] = []
        if self.debug:
            problems.append("SGA_DEBUG debe ser false en produccion")
        if self.docs_enabled:
            problems.append("SGA_DOCS_ENABLED debe ser false en produccion")
        if not self.log_json:
            problems.append("SGA_LOG_JSON debe ser true en produccion")
        if not self.session_cookie_secure:
            problems.append("SGA_SESSION_COOKIE_SECURE debe ser true en produccion")
        if "testserver" in self.trusted_hosts:
            problems.append("SGA_TRUSTED_HOSTS no puede contener 'testserver' en produccion")
        if "*" in self.trusted_hosts:
            problems.append("SGA_TRUSTED_HOSTS no puede contener '*' en produccion")

        if problems:
            msg = "Configuracion de produccion invalida: " + "; ".join(problems)
            raise ValueError(msg)
        return self


def _safe_validation_summary(exc: ValidationError) -> str:
    lines = ["Configuracion SGA invalida:"]
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"])
        lines.append(f"- {location}: {error['msg']}")
    return "\n".join(lines)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve la configuracion validada, cacheada por proceso."""
    try:
        return Settings()  # pyright: ignore[reportCallIssue]
    except ValidationError as exc:
        raise RuntimeError(_safe_validation_summary(exc)) from None
