from __future__ import annotations

import re
from collections.abc import Sequence
from uuid import uuid4

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.middleware.trustedhost import parse_host_header  # type: ignore[attr-defined]
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from judicial_archive.core.config import Settings
from judicial_archive.core.errors import ErrorCode, build_error_response
from judicial_archive.core.security import constant_time_compare

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


class RequestContextMiddleware:
    """Middleware ASGI puro que asigna y propaga un request-id seguro."""

    def __init__(self, app: ASGIApp, *, header_name: str = "X-Request-ID") -> None:
        self.app = app
        self.header_name = header_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        incoming = headers.get(self.header_name)
        request_id = (
            incoming if incoming and _REQUEST_ID_PATTERN.fullmatch(incoming) else uuid4().hex
        )

        state = scope.setdefault("state", {})
        state["request_id"] = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_wrapped(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers[self.header_name] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapped)
        finally:
            structlog.contextvars.clear_contextvars()


class TrustedHostMiddleware:
    """Valida el encabezado Host y responde con el sobre comun de errores."""

    def __init__(self, app: ASGIApp, *, allowed_hosts: Sequence[str]) -> None:
        if not allowed_hosts:
            allowed_hosts = ["*"]

        for pattern in allowed_hosts:
            if "*" in pattern[1:]:
                raise ValueError("Solo se permite un comodin inicial en los hosts.")
            if pattern.startswith("*") and pattern != "*" and not pattern.startswith("*."):
                raise ValueError("El comodin de host debe tener la forma '*.dominio'.")

        self.app = app
        self.allowed_hosts = [pattern.lower() for pattern in allowed_hosts]
        self.allow_any = "*" in allowed_hosts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.allow_any or scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        parsed_host = parse_host_header(Headers(scope=scope).get("host"))
        if parsed_host is None:
            await self._reject(scope, receive, send)
            return

        host = parsed_host.host.lower()
        if any(
            host == pattern or (pattern.startswith("*") and host.endswith(pattern[1:]))
            for pattern in self.allowed_hosts
        ):
            await self.app(scope, receive, send)
            return

        await self._reject(scope, receive, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        state = scope.get("state")
        request_id = state.get("request_id") if isinstance(state, dict) else None
        response: Response = build_error_response(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="El host de la peticion no esta permitido.",
            request_id=request_id if isinstance(request_id, str) else None,
        )
        await response(scope, receive, send)


class RequestBodyLimitMiddleware:
    """Rechaza peticiones cuya longitud declarada supera el limite."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_bytes: int,
        exempt_path_prefixes: tuple[str, ...] = (),
    ) -> None:
        self.app = app
        self.max_bytes = max_bytes
        self.exempt_path_prefixes = exempt_path_prefixes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path", ""))
        if any(path.startswith(prefix) for prefix in self.exempt_path_prefixes):
            await self.app(scope, receive, send)
            return

        content_length = Headers(scope=scope).get("content-length")
        if content_length is None:
            await self.app(scope, receive, send)
            return

        try:
            declared = int(content_length)
        except ValueError:
            await self._reject(
                scope,
                receive,
                send,
                status_code=400,
                code=ErrorCode.BAD_REQUEST,
                message="El encabezado Content-Length no es valido.",
            )
            return

        if declared < 0:
            await self._reject(
                scope,
                receive,
                send,
                status_code=400,
                code=ErrorCode.BAD_REQUEST,
                message="El encabezado Content-Length no es valido.",
            )
            return

        if declared > self.max_bytes:
            await self._reject(
                scope,
                receive,
                send,
                status_code=413,
                code=ErrorCode.PAYLOAD_TOO_LARGE,
                message="La peticion excede el tamano permitido.",
                details={"max_bytes": self.max_bytes},
            )
            return

        await self.app(scope, receive, send)

    async def _reject(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        *,
        status_code: int,
        code: ErrorCode,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        state = scope.get("state")
        request_id = state.get("request_id") if isinstance(state, dict) else None
        response: Response = build_error_response(
            status_code=status_code,
            code=code,
            message=message,
            request_id=request_id if isinstance(request_id, str) else None,
            details=details,
        )
        await response(scope, receive, send)


class CSRFMiddleware:
    """Valida double-sumbit cookie en metodos no idempotentes."""

    def __init__(
        self, app: ASGIApp, *, settings: Settings, exempt_paths: tuple[str, ...] = ()
    ) -> None:
        self.app = app
        self.settings = settings
        self.exempt_paths = frozenset(exempt_paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.settings.auth_csrf_enabled:
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method", "GET")).upper()
        path = str(scope.get("path", ""))
        if method in _SAFE_METHODS or path in self.exempt_paths:
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        cookie_token = request.cookies.get(self.settings.auth_csrf_cookie_name)
        header_token = request.headers.get(self.settings.auth_csrf_header_name)

        if (
            not cookie_token
            or not header_token
            or not constant_time_compare(cookie_token, header_token)
        ):
            await self._reject(scope, receive, send)
            return

        await self.app(scope, receive, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        state = scope.get("state")
        request_id = state.get("request_id") if isinstance(state, dict) else None
        response: Response = build_error_response(
            status_code=403,
            code=ErrorCode.FORBIDDEN,
            message="Token CSRF ausente o invalido.",
            request_id=request_id if isinstance(request_id, str) else None,
            details={"reason": "csrf"},
        )
        await response(scope, receive, send)
