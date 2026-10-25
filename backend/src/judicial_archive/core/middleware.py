from __future__ import annotations

import re
from uuid import uuid4

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


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


## USO EN CUALQUIER MODULO
## import structlog
## logger = structlog.get_logger(__name__)
## logger.info("box_created", box_id=str(box.id), box_number=box.number)

# Formato de error
""" {
  "error": {
    "code": "not_found",
    "message": "La caja solicitada no existe.",
    "details": null,
    "request_id": "5f0f0e8c9a4b4f0e8f0a9b8c7d6e5f4a"
  }
} """
