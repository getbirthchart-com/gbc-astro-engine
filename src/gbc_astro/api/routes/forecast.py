"""Forecast HTTP routes: transits, returns and event search."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from gbc_astro.api.dependencies import EngineDep
from gbc_astro.api.models import (
    ApiErrorEnvelope,
    EventSearchRequest,
    NatalChartRequest,
    ReturnRequest,
    TransitRequest,
)
from gbc_astro.engine import AstrologyEngine
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.models.chart import NatalChart

logger = logging.getLogger("gbc_astro.api")

router = APIRouter(prefix="/v1/forecast", tags=["forecast"])

_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ApiErrorEnvelope},
    409: {"model": ApiErrorEnvelope},
    422: {"model": ApiErrorEnvelope},
    503: {"model": ApiErrorEnvelope},
    500: {"model": ApiErrorEnvelope},
}


def _natal(engine: AstrologyEngine, request: NatalChartRequest) -> NatalChart:
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


def _instant(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidCalculationProfileError(
            f"{field} is not a valid ISO 8601 instant.", {"value": value}
        ) from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@router.post(
    "/transits",
    summary="Calculate a transit snapshot against a natal chart",
    response_description=(
        "Transit positions, transit-to-natal aspects with real applying and "
        "separating phases, and transit placements in the natal houses."
    ),
    responses=_ERROR_RESPONSES,
)
def calculate_transits(body: TransitRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    result = engine.transits(
        _natal(engine, body.natal),
        _instant(body.target_instant, "target_instant"),
        top_count=body.top,
        include_natal_chart=body.include_natal_chart,
    )
    logger.info("transits_ok duration_ms=%.1f", (time.perf_counter() - started) * 1000.0)
    payload: dict[str, Any] = result.to_dict()
    return JSONResponse(content=payload)


@router.post(
    "/returns",
    summary="Find every exact planetary return in a window",
    response_description=(
        "All exact returns, not the first. A body stationing near its natal "
        "degree returns three times and every one is reported."
    ),
    responses=_ERROR_RESPONSES,
)
def calculate_returns(body: ReturnRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    result = engine.returns(
        _natal(engine, body.natal),
        body.body,
        _instant(body.window_start, "window_start"),
        _instant(body.window_end, "window_end"),
        include_charts=body.include_charts,
    )
    logger.info("returns_ok duration_ms=%.1f", (time.perf_counter() - started) * 1000.0)
    payload: dict[str, Any] = result.to_dict()
    return JSONResponse(content=payload)


@router.post(
    "/events",
    summary="Locate ingresses, stations, exact longitudes or exact aspects",
    response_description=(
        "Events located by bracketed root finding refined by bisection, with the "
        "achieved precision reported per event."
    ),
    responses=_ERROR_RESPONSES,
)
def search_events(body: EventSearchRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    result = engine.search_events(
        event_type=body.event_type,
        body=body.body,
        start=_instant(body.start, "start"),
        end=_instant(body.end, "end"),
        target_longitude=body.target_longitude,
        aspect_angle=body.aspect_angle,
    )
    logger.info("events_ok duration_ms=%.1f", (time.perf_counter() - started) * 1000.0)
    payload: dict[str, Any] = result.to_dict()
    return JSONResponse(content=payload)
