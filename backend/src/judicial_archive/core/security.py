from __future__ import annotations

import hashlib
import hmac
import secrets

import structlog
from pwdlib import PasswordHash

_MIN_TOKEN_BYTES = 32
_MAX_PASSWORD_LENGTH = 1024

_hasher = PasswordHash.recommended()

logger = structlog.get_logger(__name__)


def hash_password(password: str) -> str:
    """Genera un hash Argon2id de la contrasena."""
    if not password:
        msg = "La contrasena no puede estar vacia."
        raise ValueError(msg)
    if len(password) > _MAX_PASSWORD_LENGTH:
        msg = f"La contrasena supera el maximo de {_MAX_PASSWORD_LENGTH} caracteres."
        raise ValueError(msg)
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica una contrasena sin propagar errores de formato del hash."""
    if not password or not password_hash:
        return False
    if len(password) > _MAX_PASSWORD_LENGTH:
        return False
    try:
        return _hasher.verify(password, password_hash)
    except Exception as exc:
        logger.warning("password_verification_failed", error_type=type(exc).__name__)
        return False


def generate_opaque_token(nbytes: int = _MIN_TOKEN_BYTES) -> str:
    """Genera un token opaco criptograficamente seguro."""
    if nbytes < _MIN_TOKEN_BYTES:
        msg = f"El token debe tener al menos {_MIN_TOKEN_BYTES} bytes de entropia."
        raise ValueError(msg)
    return secrets.token_urlsafe(nbytes)


def hash_opaque_token(token: str) -> str:
    """Devuelve el hash SHA-256 hexadecimal de un token de alta entropia."""
    if not token:
        msg = "El token no puede estar vacio."
        raise ValueError(msg)
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_opaque_token(token: str, token_hash: str) -> bool:
    """Compara un token con su hash en tiempo constante."""
    if not token or not token_hash:
        return False
    return hmac.compare_digest(hash_opaque_token(token), token_hash)
