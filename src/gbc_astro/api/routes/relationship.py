"""Synastry and composite HTTP routes — thin transport over the engine.

Both build each side with `AstrologyEngine.natal(...)` first, so the two charts
are guaranteed to share zodiac and schema semantics before they are combined.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from gbc_astro.api.dependencies import EngineDep, engine_for_zodiac
from gbc_astro.api.models import ApiErrorEnvelope, NatalChartRequest, RelationshipRequest
from gbc_astro.api.responses import (
    CompatibilityResponse,
    CompositeChartResponse,
    CompositeTransitResponse,
    DavisonChartResponse,
    EvidenceContextResponse,
    ProgressedSynastryResponse,
    RelationshipTransitResponse,
    ReportOutlineResponse,
    SynastryResponse,
)
from gbc_astro.engine import AstrologyEngine
from gbc_astro.errors import InvalidCalculationProfileError
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
    responses={**_ERROR_RESPONSES, 200: {"model": SynastryResponse}},
)
def calculate_synastry(body: RelationshipRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    result = engine.synastry(_natal(engine, body.chart_a), _natal(engine, body.chart_b))
    logger.info("synastry_ok duration_ms=%.1f", (time.perf_counter() - started) * 1000.0)
    payload: dict[str, Any] = result.to_dict()
    return JSONResponse(content=payload)


def _instant(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidCalculationProfileError(
            f"{field} is not a valid ISO 8601 instant.", {"value": value}
        ) from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _target(body: RelationshipRequest) -> datetime:
    if not body.target_instant:
        raise InvalidCalculationProfileError(
            "target_instant is required for a timing calculation. The engine "
            "never assumes the current moment.",
            {"field": "target_instant"},
        )
    return _instant(body.target_instant, "target_instant")


@router.post(
    "/timing/transits",
    summary="What is active between two people at an instant",
    response_description=(
        "Both natal transit charts, kept whole and separate, plus every "
        "synastry contact whose body is currently being transited."
    ),
    responses={**_ERROR_RESPONSES, 200: {"model": RelationshipTransitResponse}},
)
def relationship_transits(body: RelationshipRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    result = engine.relationship_transits(
        _natal(engine, body.chart_a), _natal(engine, body.chart_b), _target(body)
    )
    logger.info(
        "relationship_transits_ok duration_ms=%.1f",
        (time.perf_counter() - started) * 1000.0,
    )
    payload: dict[str, Any] = result.to_dict()
    return JSONResponse(content=payload)


@router.post(
    "/timing/composite-transits",
    summary="Transits against the composite chart",
    response_description=(
        "A statement about the relationship rather than about either person, "
        "so it is kept apart from the two natal transit charts."
    ),
    responses={**_ERROR_RESPONSES, 200: {"model": CompositeTransitResponse}},
)
def composite_transits(body: RelationshipRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    result = engine.composite_transits(
        _natal(engine, body.chart_a), _natal(engine, body.chart_b), _target(body)
    )
    logger.info(
        "composite_transits_ok duration_ms=%.1f",
        (time.perf_counter() - started) * 1000.0,
    )
    payload: dict[str, Any] = result.to_dict()
    return JSONResponse(content=payload)


@router.post(
    "/timing/progressed",
    summary="The three progressed comparisons, grouped by direction",
    response_description=(
        "Progressed A to natal B, natal A to progressed B and progressed A to "
        "progressed B. Three different questions, never pooled."
    ),
    responses={**_ERROR_RESPONSES, 200: {"model": ProgressedSynastryResponse}},
)
def progressed_synastry(body: RelationshipRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    result = engine.progressed_synastry(
        _natal(engine, body.chart_a), _natal(engine, body.chart_b), _target(body)
    )
    logger.info(
        "progressed_synastry_ok duration_ms=%.1f",
        (time.perf_counter() - started) * 1000.0,
    )
    payload: dict[str, Any] = result.to_dict()
    return JSONResponse(content=payload)


@router.post(
    "/timing/progressed-composite",
    summary="Progress each chart, then compose",
    response_description=(
        "A composite chart has no instant of its own to progress from, so each "
        "natal chart is progressed first and the composite recomputed."
    ),
    responses={**_ERROR_RESPONSES, 200: {"model": CompositeChartResponse}},
)
def progressed_composite(body: RelationshipRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    result = engine.progressed_composite(
        _natal(engine, body.chart_a), _natal(engine, body.chart_b), _target(body)
    )
    logger.info(
        "progressed_composite_ok duration_ms=%.1f",
        (time.perf_counter() - started) * 1000.0,
    )
    payload: dict[str, Any] = result.to_dict()
    return JSONResponse(content=payload)


@router.post(
    "/evidence",
    summary="A bounded evidence context for one topic",
    response_description=(
        "Evidence ids, how many were available, and whether the list was cut. "
        "Facts and identifiers only -- no prose is produced and no model is "
        "called."
    ),
    responses={**_ERROR_RESPONSES, 200: {"model": EvidenceContextResponse}},
)
def build_evidence(body: RelationshipRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    result = engine.evidence_context(
        _natal(engine, body.chart_a),
        _natal(engine, body.chart_b),
        body.topic.value if body.topic else "overall",
        body.relationship_type.value if body.relationship_type else None,
    )
    logger.info("evidence_ok duration_ms=%.1f", (time.perf_counter() - started) * 1000.0)
    payload: dict[str, Any] = result.to_dict()
    return JSONResponse(content=payload)


@router.post(
    "/report-outline",
    summary="Section identifiers in order, with the evidence each rests on",
    response_description=(
        "A structure for something else to render. A section with no evidence "
        "is returned as unavailable with the reason rather than dropped."
    ),
    responses={**_ERROR_RESPONSES, 200: {"model": ReportOutlineResponse}},
)
def build_outline(body: RelationshipRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    result = engine.report_outline(
        _natal(engine, body.chart_a),
        _natal(engine, body.chart_b),
        body.relationship_type.value if body.relationship_type else None,
    )
    logger.info("outline_ok duration_ms=%.1f", (time.perf_counter() - started) * 1000.0)
    payload: dict[str, Any] = result.to_dict()
    return JSONResponse(content=payload)


@router.post(
    "/compatibility",
    summary="Score a relationship under a versioned scoring profile",
    response_description=(
        "Three totals -- supportive, challenging and activity -- with every "
        "contact that produced them. Deliberately not a percentage."
    ),
    responses={**_ERROR_RESPONSES, 200: {"model": CompatibilityResponse}},
)
def calculate_compatibility(body: RelationshipRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    result = engine.compatibility(
        _natal(engine, body.chart_a),
        _natal(engine, body.chart_b),
        body.relationship_type.value if body.relationship_type else None,
    )
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
    responses={**_ERROR_RESPONSES, 200: {"model": DavisonChartResponse}},
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
    responses={**_ERROR_RESPONSES, 200: {"model": CompositeChartResponse}},
)
def calculate_composite(body: RelationshipRequest, engine: EngineDep) -> JSONResponse:
    started = time.perf_counter()
    result = engine.composite(_natal(engine, body.chart_a), _natal(engine, body.chart_b))
    logger.info("composite_ok duration_ms=%.1f", (time.perf_counter() - started) * 1000.0)
    payload: dict[str, Any] = result.to_dict()
    return JSONResponse(content=payload)
