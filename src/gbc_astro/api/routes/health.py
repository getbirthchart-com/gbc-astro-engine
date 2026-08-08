"""Liveness and readiness endpoints.

`/health` is liveness: is the process up. It performs no calculation and must
stay cheap enough to poll frequently.

`/ready` is readiness: can this instance actually serve a chart. It probes the
ephemeris provider, because a container without its data files starts perfectly
and then fails every single chart request. Keeping the two separate means an
orchestrator restarts a hung process but refuses to route traffic to a
misprovisioned one.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from gbc_astro.api.dependencies import API_VERSION
from gbc_astro.api.models import HealthResponse, ReadinessResponse
from gbc_astro.constants import ENGINE_NAME, ENGINE_VERSION, SCHEMA_VERSION

logger = logging.getLogger("gbc_astro.api")

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health",
)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        engine=ENGINE_NAME,
        engine_version=ENGINE_VERSION,
        schema_version=SCHEMA_VERSION,
        api_version=API_VERSION,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Service readiness",
    response_description=(
        "Whether this instance can calculate a chart. Returns 503 when ephemeris "
        "data is missing or the provider dependency is absent."
    ),
    responses={503: {"model": ReadinessResponse}},
)
def ready() -> JSONResponse:
    """Probe the ephemeris provider with a real calculation.

    `degraded` means optional bodies are unavailable -- typically Chiron without
    `seas_18.se1` -- while the core chart still calculates. It is reported as
    healthy so a partial provision does not take the service down, but it is
    visible so it does not go unnoticed either.
    """
    base: dict[str, Any] = {
        "engine": ENGINE_NAME,
        "engineVersion": ENGINE_VERSION,
        "apiVersion": API_VERSION,
    }

    try:
        from gbc_astro.providers.swiss import SwissEphemerisProvider

        report = SwissEphemerisProvider().health_check()
    except Exception as exc:  # provider dependency or data entirely absent
        logger.warning("readiness_failed error=%s", exc)
        return JSONResponse(
            status_code=503,
            content={**base, "status": "not_ready", "detail": str(exc)},
        )

    manifest = cast(dict[str, Any], report.get("manifest", {}))
    missing = list(manifest.get("missingRequiredData", []))
    unavailable = list(cast(list[str], report.get("unavailableCapabilities", [])))

    payload: dict[str, Any] = {
        **base,
        "status": "ready" if not unavailable else "degraded",
        "provider": report.get("provider"),
        "providerVersion": report.get("providerVersion"),
        "ephemerisPath": report.get("ephemerisPath"),
        "unavailableCapabilities": unavailable,
        "missingRequiredData": missing,
    }
    if missing:
        payload["status"] = "not_ready"
        payload["detail"] = (
            "Required Swiss Ephemeris data files are missing; see "
            "docs/PRODUCTION_EPHEMERIS_SETUP.md."
        )
        return JSONResponse(status_code=503, content=payload)

    return JSONResponse(status_code=200, content=payload)
