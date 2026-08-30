"""Application dependencies and engine lifecycle helpers."""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request

from gbc_astro.api.models import NatalChartRequest
from gbc_astro.engine import AstrologyEngine
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.models.chart import NatalChart
from gbc_astro.providers.swiss import SwissEphemerisProvider

API_VERSION = "v1"


def build_engine() -> AstrologyEngine:
    """Construct a reusable AstrologyEngine for the process.

    Uses GBC_SWISS_EPHE_PATH when set; otherwise defaults to the engine's
    standard Swiss provider initialization.
    """

    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    if path:
        return AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
    return AstrologyEngine()


def get_engine(request: Request) -> Iterator[AstrologyEngine]:
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        engine = build_engine()
        request.app.state.engine = engine
    yield engine


EngineDep = Annotated[AstrologyEngine, Depends(get_engine)]


def engine_for_settings(
    engine: AstrologyEngine,
    *,
    zodiac: str | None = None,
    ayanamsa: str | None = None,
    house_system: str | None = None,
    node_type: str | None = None,
    aspect_preset: str | None = None,
    custom_aspect_rules: list[dict[str, object]] | None = None,
    additional_points: list[str] | None = None,
) -> AstrologyEngine:
    """Return an engine configured for the requested public settings."""

    return engine.with_settings(
        zodiac=zodiac,
        ayanamsa=ayanamsa,
        house_system=house_system,
        node_type=node_type,
        aspect_preset=aspect_preset,
        custom_aspect_rules=custom_aspect_rules,
        additional_points=additional_points,
    )


def engine_for_zodiac(
    engine: AstrologyEngine,
    zodiac: str | None,
    ayanamsa: str | None,
) -> AstrologyEngine:
    """Return an engine configured for the requested zodiac.

    Thin wrapper over `engine_for_settings`. Kept so existing call sites and
    the sidereal HTTP path do not fork a second construction helper.
    """

    return engine_for_settings(engine, zodiac=zodiac, ayanamsa=ayanamsa)


def natal_from_request(
    engine: AstrologyEngine, request: NatalChartRequest
) -> tuple[AstrologyEngine, NatalChart]:
    """Resolve public natal settings, then cast the chart."""

    house_system = request.house_system.value if request.house_system else None
    custom_aspect_rules = None
    if request.custom_aspect_rules is not None:
        custom_aspect_rules = [item.model_dump() for item in request.custom_aspect_rules]
    configured = engine_for_settings(
        engine,
        zodiac=request.zodiac.value if request.zodiac else None,
        ayanamsa=request.ayanamsa.value if request.ayanamsa else None,
        house_system=house_system,
        node_type=request.node_type,
        aspect_preset=request.aspect_preset,
        custom_aspect_rules=custom_aspect_rules,
        additional_points=request.additional_points,
    )
    chart = configured.natal(
        local_datetime=request.to_engine_local_datetime(),
        timezone=request.timezone,
        latitude=request.latitude,
        longitude=request.longitude,
        altitude_m=request.altitude_m,
        house_system=house_system,
        unknown_time=request.unknown_time,
        fold=request.fold,
    )
    return configured, chart
