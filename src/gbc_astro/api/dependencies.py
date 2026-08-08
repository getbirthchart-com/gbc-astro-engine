"""Application dependencies and engine lifecycle helpers."""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import replace
from typing import Annotated

from fastapi import Depends, Request

from gbc_astro.engine import AstrologyEngine
from gbc_astro.houses.swiss import SwissHouseCalculator
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


def engine_for_zodiac(
    engine: AstrologyEngine,
    zodiac: str | None,
    ayanamsa: str | None,
) -> AstrologyEngine:
    """Return an engine configured for the requested zodiac.

    The zodiac is a property of the calculation profile, and a profile is
    immutable, so a sidereal request needs its own engine. The provider and
    house calculator are shared with the process engine, so this costs a
    dataclass copy rather than reopening the ephemeris.
    """
    if zodiac is None or zodiac == "tropical":
        return engine

    profile = replace(
        engine.profile,
        id=f"{engine.profile.id}+sidereal-{ayanamsa}",
        zodiac="sidereal",
        ayanamsa=ayanamsa,
    )
    return AstrologyEngine(
        provider=engine._get_provider(),
        profile=profile,
        house_calculator=engine._get_house_calculator(),
        relationship_profile=engine.relationship_profile,
        scoring_profile=engine.scoring_profile,
        transit_profile=engine.transit_profile,
        progression_profile=engine.progression_profile,
        solar_arc_profile=engine.solar_arc_profile,
        pattern_profile=engine.pattern_profile,
    )
