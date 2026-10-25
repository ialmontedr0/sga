from __future__ import annotations

from enum import StrEnum
from typing import Any, cast

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "validation_error"
    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    CONFLICT = "conflict"
    RATE_LIMITED = "rate_limited"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL_ERROR = "internal_error"


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AppError(Exception):
    """Error de aplicacion con codigo estable y estado HTTP asociado."""

    status_code: int = 400
    code: ErrorCode = ErrorCode.BAD_REQUEST

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class UnauthorizedError(AppError):
    status_code = 401
    code = ErrorCode.UNAUTHORIZED


class ForbiddenError(AppError):
    status_code = 403
    code = ErrorCode.FORBIDDEN


class NotFoundError(AppError):
    status_code = 404
    code = ErrorCode.NOT_FOUND


class ConflictError(AppError):
    status_code = 409
    code = ErrorCode.CONFLICT


class InvalidParameterError(AppError):
    status_code = 422
    code = ErrorCode.VALIDATION_ERROR


class RateLimitedError(AppError):
    status_code = 429
    code = ErrorCode.RATE_LIMITED


class ServiceUnavailableError(AppError):
    status_code = 503
    code = ErrorCode.SERVICE_UNAVAILABLE


class InternalError(AppError):
    status_code = 500
    code = ErrorCode.INTERNAL_ERROR


logger = structlog.get_logger(__name__)

_HTTP_STATUS_TO_CODE: dict[int, ErrorCode] = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    409: ErrorCode.CONFLICT,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMITED,
    503: ErrorCode.SERVICE_UNAVAILABLE,
}


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else None


def _error_response(
    *,
    status_code: int,
    code: ErrorCode,
    message: str,
    request_id: str | None,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorDetail(
            code=code.value,
            message=message,
            details=details,
            request_id=request_id,
        )
    ).model_dump(mode="json")
    return JSONResponse(status_code=status_code, content=payload)


def _serialize_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for error in exc.errors():
        serialized.append(
            {
                "location": list(error.get("loc", ())),
                "message": error.get("msg", "Valor invalido."),
                "type": error.get("type", "value_error"),
            }
        )
    return serialized


async def app_error_handler(request: Request, exc: Exception) -> Response:
    app_error = cast(AppError, exc)
    if app_error.status_code >= 500:
        logger.error(
            "application_error",
            status_code=app_error.status_code,
            error_code=app_error.code.value,
            path=request.url.path,
            method=request.method,
        )
    else:
        logger.warning(
            "application_error",
            status_code=app_error.status_code,
            error_code=app_error.code.value,
            path=request.url.path,
            method=request.method,
        )
    return _error_response(
        status_code=app_error.status_code,
        code=app_error.code,
        message=app_error.message,
        request_id=_request_id(request),
        details=app_error.details,
    )


async def validation_exception_handler(request: Request, exc: Exception) -> Response:
    validation_error = cast(RequestValidationError, exc)
    return _error_response(
        status_code=422,
        code=ErrorCode.VALIDATION_ERROR,
        message="Los datos enviados no son validos.",
        request_id=_request_id(request),
        details={"errors": _serialize_validation_errors(validation_error)},
    )


async def http_exception_handler(request: Request, exc: Exception) -> Response:
    http_error = cast(StarletteHTTPException, exc)
    detail = cast(object, http_error.detail)
    if http_error.status_code >= 500:
        message = "Error interno del servidor."
    elif isinstance(detail, str):
        message = detail
    else:
        message = "Error en la solicitud."
    default_code = (
        ErrorCode.INTERNAL_ERROR if http_error.status_code >= 500 else ErrorCode.BAD_REQUEST
    )
    code = _HTTP_STATUS_TO_CODE.get(http_error.status_code, default_code)
    return _error_response(
        status_code=http_error.status_code,
        code=code,
        message=message,
        request_id=_request_id(request),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
        exc_info=exc,
    )
    return _error_response(
        status_code=500,
        code=ErrorCode.INTERNAL_ERROR,
        message="Error interno del servidor.",
        request_id=_request_id(request),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
