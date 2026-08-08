"""HTTP routes for the v1.0 professional modules.

Everything the engine can do is reachable here. Anything it can do that is not
routed is, for a product whose frontend speaks only HTTP, effectively not
implemented -- which is exactly what these routes exist to fix.

Grouping follows the shape of the answer rather than the name of the technique:
constructions that return a chart sit under `/v1/charts`, time-directed ones
under `/v1/forecast`, derived analysis under `/v1/analysis`, geography under
`/v1/maps`, and bulk data on its own.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from gbc_astro.api.dependencies import EngineDep, engine_for_zodiac
from gbc_astro.api.models import (
    ApiErrorEnvelope,
    AstrocartographyRequest,
    DirectionRequest,
    EphemerisRequest,
    NatalChartRequest,
    PatternRequest,
    RelocationRequest,
    TransformRequest,
)
from gbc_astro.constants import BODY_IDS
from gbc_astro.engine import AstrologyEngine
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.houses.systems import HOUSE_SYSTEMS
from gbc_astro.models.chart import NatalChart
from gbc_astro.profiles.ayanamsa import AYANAMSA_PROFILES
from gbc_astro.providers.asteroids import OPTIONAL_BODIES

logger = logging.getLogger("gbc_astro.api")

charts = APIRouter(prefix="/v1/charts", tags=["charts"])
forecast = APIRouter(prefix="/v1/forecast", tags=["forecast"])
analysis = APIRouter(prefix="/v1/analysis", tags=["analysis"])
maps = APIRouter(prefix="/v1/maps", tags=["maps"])
data = APIRouter(prefix="/v1", tags=["data"])

_ERRORS: dict[int | str, dict[str, Any]] = {
    400: {"model": ApiErrorEnvelope},
    409: {"model": ApiErrorEnvelope},
    422: {"model": ApiErrorEnvelope},
    503: {"model": ApiErrorEnvelope},
    500: {"model": ApiErrorEnvelope},
}


def _build(
    engine: AstrologyEngine, request: NatalChartRequest
) -> tuple[AstrologyEngine, NatalChart]:
    """Resolve the zodiac, then cast the chart. Returns both, since transforms need the engine."""
    configured = engine_for_zodiac(
        engine,
        request.zodiac.value if request.zodiac else None,
        request.ayanamsa.value if request.ayanamsa else None,
    )
    chart = configured.natal(
        local_datetime=request.to_engine_local_datetime(),
        timezone=request.timezone,
        latitude=request.latitude,
        longitude=request.longitude,
        altitude_m=request.altitude_m,
        house_system=request.house_system.value if request.house_system else None,
        unknown_time=request.unknown_time,
        fold=request.fold,
    )
    return configured, chart


def _instant(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidCalculationProfileError(
            f"{field} is not a valid ISO 8601 instant.", {"value": value}
        ) from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _ok(payload: dict[str, Any], label: str, started: float) -> JSONResponse:
    logger.info("%s_ok duration_ms=%.1f", label, (time.perf_counter() - started) * 1000.0)
    return JSONResponse(content=payload)


@charts.post(
    "/draconic",
    summary="Re-zero the zodiac on the lunar node",
    response_description="The node lands on exactly 0 degrees Aries by construction.",
    responses=_ERRORS,
)
def calculate_draconic(body: TransformRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    configured, chart = _build(engine, body.natal)
    return _ok(configured.draconic(chart).to_dict(), "draconic", started)


@charts.post(
    "/harmonic",
    summary="The harmonic-n chart",
    response_description=(
        "Every longitude multiplied by n. Aspects are recomputed, not carried "
        "over: collapsing an aspect family onto conjunctions is the technique."
    ),
    responses=_ERRORS,
)
def calculate_harmonic(body: TransformRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    if body.harmonic is None:
        raise InvalidCalculationProfileError(
            "harmonic is required for this transform.", {"field": "harmonic"}
        )
    configured, chart = _build(engine, body.natal)
    return _ok(configured.harmonic(chart, body.harmonic).to_dict(), "harmonic", started)


@charts.post(
    "/relocated",
    summary="Recast the same birth moment for a different place",
    response_description=(
        "Body longitudes are unchanged, so aspects are identical. Only the "
        "angles, cusps and house placements differ."
    ),
    responses=_ERRORS,
)
def calculate_relocated(body: RelocationRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    configured, chart = _build(engine, body.natal)
    result = configured.relocate(
        chart,
        body.latitude,
        body.longitude,
        house_system=body.house_system.value if body.house_system else None,
    )
    return _ok(result.to_dict(), "relocated", started)


@forecast.post(
    "/progressions",
    summary="Secondary progressions: one day of motion per year of life",
    response_description="An ordinary chart cast for the progressed instant.",
    responses=_ERRORS,
)
def calculate_progressions(body: DirectionRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    configured, chart = _build(engine, body.natal)
    result = configured.progressions(chart, _instant(body.target_instant, "target_instant"))
    return _ok(result.to_dict(), "progressions", started)


@forecast.post(
    "/solar-arc",
    summary="Direct every natal point by the progressed Sun's travel",
    response_description=(
        "A rotation: directed points hold their natal aspects exactly, so only "
        "contacts to the natal chart carry information."
    ),
    responses=_ERRORS,
)
def calculate_solar_arc(body: DirectionRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    configured, chart = _build(engine, body.natal)
    result = configured.solar_arc(chart, _instant(body.target_instant, "target_instant"))
    return _ok(result.to_dict(), "solar_arc", started)


@analysis.post(
    "/patterns",
    summary="Named configurations in a chart",
    response_description=(
        "Stelliums, grand trines, T-squares, grand crosses, yods and kites, with "
        "the widest leg orb of each."
    ),
    responses=_ERRORS,
)
def calculate_patterns(body: PatternRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    configured, chart = _build(engine, body.natal)
    found = configured.patterns(chart)
    payload = {
        "profile": configured.pattern_profile.to_dict(),
        "patternCount": len(found),
        "patterns": [pattern.to_dict() for pattern in found],
    }
    return _ok(payload, "patterns", started)


@maps.post(
    "/astrocartography",
    summary="Where each body sits on an angle across the Earth",
    response_description=(
        "In-mundo lines: the body actually crosses the meridian or horizon. MC "
        "and IC are meridians, Ascendant and Descendant are curves."
    ),
    responses=_ERRORS,
)
def calculate_astrocartography(
    body: AstrocartographyRequest, engine: EngineDep
) -> JSONResponse:
    started = time.perf_counter()
    if body.latitude_max <= body.latitude_min:
        raise InvalidCalculationProfileError(
            "latitude_max must be greater than latitude_min.",
            {"latitudeMin": body.latitude_min, "latitudeMax": body.latitude_max},
        )
    configured, chart = _build(engine, body.natal)
    try:
        result = configured.astrocartography(
            chart,
            bodies=tuple(body.bodies) if body.bodies else None,
            latitude_range=(body.latitude_min, body.latitude_max),
            latitude_step=body.latitude_step,
        )
    except ValueError as exc:
        raise InvalidCalculationProfileError(str(exc), {"field": "latitude_step"}) from exc
    return _ok(result, "astrocartography", started)


@data.post(
    "/ephemeris",
    summary="A table of positions over a range",
    response_description=(
        "Each row is exactly what a single-instant call returns; this is a "
        "convenience, not a second calculation path."
    ),
    responses=_ERRORS,
)
def generate_ephemeris_table(body: EphemerisRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    try:
        result = engine.ephemeris(
            tuple(body.bodies),
            _instant(body.start, "start"),
            _instant(body.end, "end"),
            timedelta(seconds=body.step_seconds),
            max_rows=body.max_rows,
        )
    except ValueError as exc:
        raise InvalidCalculationProfileError(str(exc), {"field": "range"}) from exc
    return _ok(result, "ephemeris", started)


@data.get(
    "/capabilities",
    summary="What this installation can actually calculate",
    response_description=(
        "Bodies, house systems and ayanamsas, with optional bodies probed rather "
        "than assumed. Ask here instead of discovering through an error."
    ),
)
def capabilities(engine: EngineDep) -> JSONResponse:
    optional = engine.optional_bodies()
    payload: dict[str, Any] = {
        "coreBodies": list(BODY_IDS),
        "optionalBodies": [item.to_dict() for item in optional],
        "numberedAsteroidFormat": "asteroid_<number>",
        "houseSystems": [profile.to_dict() for profile in HOUSE_SYSTEMS.values()],
        "ayanamsas": [profile.to_dict() for profile in AYANAMSA_PROFILES.values()],
        "optionalBodyNames": sorted(OPTIONAL_BODIES),
    }
    return JSONResponse(content=payload)
