"""Natal chart HTTP route — thin transport over AstrologyEngine.natal."""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from gbc_astro.api.dependencies import EngineDep, engine_for_zodiac
from gbc_astro.api.models import ApiErrorEnvelope, NatalChartRequest

logger = logging.getLogger("gbc_astro.api")

router = APIRouter(prefix="/v1/charts", tags=["charts"])


@router.post(
    "/natal",
    summary="Calculate a natal chart",
    response_description="Canonical natal chart JSON from AstrologyEngine.natal(...).",
    responses={
        200: {
            "description": (
                "Canonical natal chart object (NatalChart.to_dict()). "
                "Returned directly — not wrapped in a {chart: ...} envelope."
            ),
            "content": {
                "application/json": {
                    "example": {
                        "schemaVersion": "1.0.0",
                        "meta": {
                            "engine": "gbc-astro",
                            "engineVersion": "1.0.0",
                            "calculationProfile": "western-modern-v1",
                            "houseSystem": "placidus",
                            "zodiac": "tropical",
                        },
                        "subject": {
                            "localDateTime": "1996-06-14T04:12:00",
                            "timezone": "Europe/Lisbon",
                            "birthTimeKnown": True,
                        },
                        "angles": {},
                        "bodies": {},
                        "houses": [],
                        "aspects": [],
                        "derived": {},
                        "warnings": [],
                    }
                }
            },
        },
        400: {"model": ApiErrorEnvelope},
        409: {"model": ApiErrorEnvelope},
        422: {"model": ApiErrorEnvelope},
        503: {"model": ApiErrorEnvelope},
        500: {"model": ApiErrorEnvelope},
    },
)
def calculate_natal(body: NatalChartRequest, engine: EngineDep) -> JSONResponse:
    """Call the existing AstrologyEngine.natal(...) and return canonical JSON."""

    started = time.perf_counter()
    engine = engine_for_zodiac(
        engine,
        body.zodiac.value if body.zodiac else None,
        body.ayanamsa.value if body.ayanamsa else None,
    )
    chart = engine.natal(
        local_datetime=body.to_engine_local_datetime(),
        timezone=body.timezone,
        latitude=body.latitude,
        longitude=body.longitude,
        altitude_m=body.altitude_m,
        house_system=body.house_system.value if body.house_system else None,
        unknown_time=body.unknown_time,
        fold=body.fold,
    )
    duration_ms = (time.perf_counter() - started) * 1000.0
    logger.info(
        "natal_ok duration_ms=%.1f unknown_time=%s house_system=%s",
        duration_ms,
        body.unknown_time,
        body.house_system.value if body.house_system else "default",
    )
    payload: dict[str, Any] = chart.to_dict()
    return JSONResponse(content=payload)
