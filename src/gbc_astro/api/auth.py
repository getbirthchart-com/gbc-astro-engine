"""Internal shared-secret gate for server-to-server callers.

The engine is reachable from Vercel over the public internet. It must not
become a free astrology API. When ``GBC_ASTRO_API_SECRET`` (or the alias
``ASTROLOGY_API_SECRET``) is set, every non-probe route requires:

    Authorization: Bearer <secret>

``/health`` and ``/ready`` stay public so orchestrators can probe without
credentials. When the secret is unset the gate is off — local tests and a
laptop uvicorn keep working. Set ``GBC_ASTRO_REQUIRE_SECRET=1`` in production
so a missing secret is 401 instead of an open calculator.
"""

from __future__ import annotations

import hmac
import os

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from gbc_astro.api.errors import error_envelope

PUBLIC_PATHS = frozenset({
    "/health",
    "/ready",
    "/docs",
    "/docs/",
    "/redoc",
    "/redoc/",
    "/openapi.json",
})


def configured_secret() -> str:
    return (
        os.environ.get("GBC_ASTRO_API_SECRET", "").strip()
        or os.environ.get("ASTROLOGY_API_SECRET", "").strip()
    )


def require_secret() -> bool:
    raw = os.environ.get("GBC_ASTRO_REQUIRE_SECRET", "").strip().lower()
    return raw in {"1", "true", "yes"}


def _bearer_token(header: str | None) -> str:
    if not header:
        return ""
    prefix = "bearer "
    if header.lower().startswith(prefix):
        return header[len(prefix) :].strip()
    return ""


def secrets_match(provided: str, expected: str) -> bool:
    provided_b = provided.encode("utf-8")
    expected_b = expected.encode("utf-8")
    if len(provided_b) != len(expected_b):
        hmac.compare_digest(expected_b, expected_b)
        return False
    return hmac.compare_digest(provided_b, expected_b)


class InternalSecretMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path.rstrip("/") or "/"
        if path in {"/health", "/ready"} or path in PUBLIC_PATHS:
            return await call_next(request)
        if path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        expected = configured_secret()
        if not expected:
            if require_secret():
                payload = error_envelope(
                    code="UNAUTHORIZED",
                    message="Missing or invalid internal API credential.",
                )
                return JSONResponse(status_code=401, content=payload)
            return await call_next(request)

        provided = _bearer_token(request.headers.get("authorization"))
        if not secrets_match(provided, expected):
            payload = error_envelope(
                code="UNAUTHORIZED",
                message="Missing or invalid internal API credential.",
            )
            return JSONResponse(status_code=401, content=payload)

        return await call_next(request)
