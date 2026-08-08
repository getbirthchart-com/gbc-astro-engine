"""HTTP error mapping for gbc_astro domain exceptions."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from gbc_astro.errors import (
    AmbiguousLocalTimeError,
    EphemerisOutOfRangeError,
    GbcAstroError,
    HouseCalculationUnavailableError,
    InvalidCalculationProfileError,
    InvalidCoordinateError,
    NonexistentLocalTimeError,
    ProviderDependencyError,
    UnknownBirthTimeError,
    UnknownTimezoneError,
    UnsupportedBodyError,
)

logger = logging.getLogger("gbc_astro.api")

# Domain error → HTTP status. Stable `error.code` is the client switch key.
STATUS_BY_ERROR: dict[type[GbcAstroError], int] = {
    AmbiguousLocalTimeError: 409,
    NonexistentLocalTimeError: 400,
    InvalidCoordinateError: 400,
    UnknownTimezoneError: 400,
    UnknownBirthTimeError: 400,
    InvalidCalculationProfileError: 400,
    HouseCalculationUnavailableError: 400,
    EphemerisOutOfRangeError: 400,
    UnsupportedBodyError: 500,
    ProviderDependencyError: 503,
}

FIELD_HINTS: dict[str, str] = {
    "AMBIGUOUS_LOCAL_TIME": "local_time",
    "NONEXISTENT_LOCAL_TIME": "local_time",
    "INVALID_COORDINATE": "latitude",
    "UNKNOWN_TIMEZONE": "timezone",
    "UNKNOWN_BIRTH_TIME": "local_time",
    "INVALID_CALCULATION_PROFILE": "house_system",
}


def error_envelope(
    *,
    code: str,
    message: str,
    field: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "field": field,
            "details": details or {},
        }
    }


def _jsonable_validation_issues(errors: list[Any]) -> list[dict[str, Any]]:
    """Strip non-JSON values (e.g. exception objects) from Pydantic error dicts."""

    cleaned: list[dict[str, Any]] = []
    for item in errors:
        entry: dict[str, Any] = {
            "type": item.get("type"),
            "loc": list(item.get("loc", ())),
            "msg": item.get("msg"),
        }
        input_value = item.get("input")
        if isinstance(input_value, (str, int, float, bool)) or input_value is None:
            entry["input"] = input_value
        else:
            entry["input"] = str(input_value)
        cleaned.append(entry)
    return cleaned


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(GbcAstroError)
    async def handle_gbc_error(_request: Request, exc: GbcAstroError) -> JSONResponse:
        status = STATUS_BY_ERROR.get(type(exc), 400)
        field = FIELD_HINTS.get(exc.code)
        payload = error_envelope(
            code=exc.code,
            message=exc.message,
            field=field,
            details=dict(exc.details),
        )
        logger.info(
            "domain_error code=%s status=%s",
            exc.code,
            status,
            extra={"error_code": exc.code, "http_status": status},
        )
        return JSONResponse(status_code=status, content=payload)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = exc.errors()
        field: str | None = None
        if errors:
            loc = errors[0].get("loc", ())
            # Skip leading "body"
            parts = [str(p) for p in loc if p != "body"]
            field = ".".join(parts) if parts else None
        message = errors[0].get("msg", "Request validation failed") if errors else (
            "Request validation failed"
        )
        # Pydantic v2 often prefixes with "Value error, "
        if isinstance(message, str) and message.startswith("Value error, "):
            message = message[len("Value error, ") :]
        payload = error_envelope(
            code="REQUEST_VALIDATION_ERROR",
            message=str(message),
            field=field,
            details={"issues": _jsonable_validation_issues(list(errors))},
        )
        return JSONResponse(status_code=422, content=payload)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail
        message = detail if isinstance(detail, str) else "HTTP error"
        payload = error_envelope(
            code="HTTP_ERROR",
            message=message,
            details={"status": exc.status_code},
        )
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(Exception)
    async def handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unexpected_error type=%s", type(exc).__name__)
        payload = error_envelope(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred while calculating the chart.",
        )
        return JSONResponse(status_code=500, content=payload)
