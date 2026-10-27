"""Structured errors: a handled failure answers `{"error": {"code", "message", "fields"?}}`.

Other HTTP errors keep FastAPI's `{"detail"}` shape.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ExceptionHandler

FIELD_MESSAGE_TYPE = "field_message"
VALIDATION_MESSAGE = "Проверьте поля формы"
NOT_FOUND_MESSAGE = "Не найдено"
FALLBACK_FIELD_MESSAGE = "Проверьте поле"
# Used when a field is missing or of the wrong type, before any field validator could speak.
FIELD_MESSAGES = {
    "organization_name": "Укажите название организации",
    "name": "Укажите имя",
    "email": "Укажите корректный email",
    "password": "Пароль должен быть от 10 до 128 символов",
}


class ErrorBody(BaseModel):
    """The error of a failed request."""

    code: str
    message: str
    fields: dict[str, str] | None = None


class ErrorResponse(BaseModel):
    """The body of every failed request."""

    error: ErrorBody


@dataclass(frozen=True)
class HttpError:
    """How a domain error is answered: the status, the machine code and the Russian message."""

    status_code: int
    code: str
    message: str


class NotFound(Exception):
    """The entity does not exist or is outside the caller's scope."""


NOT_FOUND = HttpError(404, "not_found", NOT_FOUND_MESSAGE)


def error_responses(
    *statuses: int,
) -> dict[int | str, dict[str, Any]]:  # FastAPI types `responses` with Any
    """The `responses` argument of a route: these statuses answer with `ErrorResponse`."""
    return {status: {"model": ErrorResponse} for status in statuses}


def _json(status_code: int, body: ErrorBody) -> JSONResponse:
    payload = ErrorResponse(error=body).model_dump(exclude_none=True)
    return JSONResponse(status_code=status_code, content=payload)


def _answer(error: HttpError) -> JSONResponse:
    return _json(error.status_code, ErrorBody(code=error.code, message=error.message))


def _field_name(location: tuple[int | str, ...]) -> str:
    parts = [str(part) for part in location if part not in ("body", "query")]
    return parts[0] if parts else "body"


async def _handle_validation_error(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise TypeError("handler registered for another exception type")
    fields: dict[str, str] = {}
    for error in exc.errors():
        name = _field_name(tuple(error["loc"]))
        if name in fields:
            continue
        if error["type"] == FIELD_MESSAGE_TYPE:
            fields[name] = error["msg"]
        else:
            fields[name] = FIELD_MESSAGES.get(name, FALLBACK_FIELD_MESSAGE)
    body = ErrorBody(code="validation_failed", message=VALIDATION_MESSAGE, fields=fields)
    return _json(422, body)


async def _handle_http_error(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        raise TypeError("handler registered for another exception type")
    if exc.status_code == NOT_FOUND.status_code:
        return _answer(NOT_FOUND)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


async def _handle_not_found(_request: Request, _exc: Exception) -> JSONResponse:
    return _answer(NOT_FOUND)


def register_domain_errors(app: FastAPI, mapping: Mapping[type[Exception], HttpError]) -> None:
    """Answer each domain error type of a module with its HTTP error (owned by its router)."""

    def make_handler(error: HttpError) -> ExceptionHandler:
        async def handle(_request: Request, _exc: Exception) -> JSONResponse:
            return _answer(error)

        return handle

    for error_type, error in mapping.items():
        app.add_exception_handler(error_type, make_handler(error))


def register_error_handlers(app: FastAPI) -> None:
    """Install the handlers that give every error its common shape."""
    app.add_exception_handler(NotFound, _handle_not_found)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)
