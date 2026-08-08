"""Synastry and composite HTTP routes — thin transport over the engine.

Both build each side with `AstrologyEngine.natal(...)` first, so the two charts
are guaranteed to share zodiac and schema semantics before they are combined.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from gbc_astro.api.dependencies import EngineDep, engine_for_zodiac
from gbc_astro.api.models import ApiErrorEnvelope, NatalChartRequest, RelationshipRequest
from gbc_astro.engine import AstrologyEngine
from gbc_astro.models.chart import NatalChart

logger = logging.getLogger("gbc_astro.api")

router = APIRouter(prefix="/v1/charts", tags=["charts"])

_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ApiErrorEnvelope},
    409: {"model": ApiErrorEnvelope},
    422: {"model": ApiErrorEnvelope},
    503: {"model": ApiErrorEnvelope},
    500: {"model": ApiErrorEnvelope},
}


def _natal(engine: AstrologyEngine, request: NatalChartRequest) -> NatalChart:
    engine = engine_for_zodiac(
        engine,
        request.zodiac.value if request.zodiac else None,
        request.ayanamsa.value if request.ayanamsa else None,
    )
    return engine.natal(
        local_datetime=request.to_engine_local_datetime(),
        timezone=request.timezone,
        latitude=request.latitude,
        longitude=request.longitude,
        altitude_m=request.altitude_m,
        house_system=request.house_system.value if request.house_system else None,
        unknown_time=request.unknown_time,
        fold=request.fold,
    )


@router.post(
    "/synastry",
    summary="Calculate a synastry chart",
    response_description=(
        "Canonical synastry JSON: cross aspects, two-way house overlays and "
        "angle interactions, returned directly rather than wrapped."
    ),
    responses=_ERROR_RESPONSES,
)
def calculate_synastry(body: RelationshipRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    result = engine.synastry(_natal(engine, body.chart_a), _natal(engine, body.chart_b))
    logger.info("synastry_ok duration_ms=%.1f", (time.perf_counter() - started) * 1000.0)
    payload: dict[str, Any] = result.to_dict()
    return JSONResponse(content=payload)


@router.post(
    "/compatibility",
    summary="Score a relationship under a versioned scoring profile",
    response_description=(
        "Three totals -- supportive, challenging and activity -- with every "
        "contact that produced them. Deliberately not a percentage."
    ),
    responses=_ERROR_RESPONSES,
)
def calculate_compatibility(body: RelationshipRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    result = engine.compatibility(_natal(engine, body.chart_a), _natal(engine, body.chart_b))
    logger.info("compatibility_ok duration_ms=%.1f", (time.perf_counter() - started) * 1000.0)
    payload: dict[str, Any] = result.to_dict()
    return JSONResponse(content=payload)


@router.post(
    "/davison",
    summary="Calculate a Davison relationship chart",
    response_description=(
        "Canonical Davison JSON: an ordinary chart for the midpoint moment and "
        "midpoint place of the two births, so its speeds, houses and "
        "applying/separating phases are real rather than constructed."
    ),
    responses=_ERROR_RESPONSES,
)
def calculate_davison(body: RelationshipRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    result = engine.davison(_natal(engine, body.chart_a), _natal(engine, body.chart_b))
    logger.info("davison_ok duration_ms=%.1f", (time.perf_counter() - started) * 1000.0)
    payload: dict[str, Any] = result.to_dict()
    return JSONResponse(content=payload)


@router.post(
    "/composite",
    summary="Calculate a composite chart",
    response_description=(
        "Canonical composite JSON: shortest-arc midpoint positions, with the "
        "methodology named under meta and any ambiguity reported in warnings."
    ),
    responses=_ERROR_RESPONSES,
)
def calculate_composite(body: RelationshipRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    result = engine.composite(_natal(engine, body.chart_a), _natal(engine, body.chart_b))
    logger.info("composite_ok duration_ms=%.1f", (time.perf_counter() - started) * 1000.0)
    payload: dict[str, Any] = result.to_dict()
    return JSONResponse(content=payload)
