"""Application dependencies and engine lifecycle helpers."""

from __future__ import annotations

import os
from collections.abc import Iterator
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
