"""Health endpoint — cheap liveness, no natal calculation."""

from __future__ import annotations

from fastapi import APIRouter

from gbc_astro.api.dependencies import API_VERSION
from gbc_astro.api.models import HealthResponse
from gbc_astro.constants import ENGINE_NAME, ENGINE_VERSION, SCHEMA_VERSION

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
