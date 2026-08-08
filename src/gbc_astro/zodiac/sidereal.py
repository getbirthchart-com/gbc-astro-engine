"""Sidereal zodiac mapping.

A sidereal chart is a tropical chart rotated backwards by the ayanamsa. Every
longitude shifts by the same amount at a given instant, which has one consequence
worth stating: relationships *between* points are untouched. Aspects, house
assignments and the angular distance between any two bodies are identical in
both zodiacs. Only the sign and degree labels change.

That is why this is applied as a transform over a completed tropical chart
rather than threaded through the calculation. The validated tropical math runs
unchanged and the rotation happens once, at the end.
"""

from __future__ import annotations

import os
from importlib import import_module
from types import ModuleType

from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.errors import InvalidCalculationProfileError, ProviderDependencyError
from gbc_astro.models.position import ZodiacPosition
from gbc_astro.profiles.ayanamsa import AYANAMSA_PROFILES, AyanamsaProfile
from gbc_astro.zodiac.tropical import longitude_to_tropical


def resolve_ayanamsa_profile(ayanamsa_id: str) -> AyanamsaProfile:
    profile = AYANAMSA_PROFILES.get(ayanamsa_id)
    if profile is None:
        raise InvalidCalculationProfileError(
            "Unknown ayanamsa. Sidereal charts require a named, supported ayanamsa; "
            "no default is substituted because the schools disagree by degrees.",
            {"ayanamsa": ayanamsa_id, "supported": sorted(AYANAMSA_PROFILES)},
        )
    return profile


class AyanamsaCalculator:
    """Resolves the ayanamsa in degrees for an instant, via Swiss Ephemeris."""

    id = "swisseph-ayanamsa"

    def __init__(self, ephemeris_path: str | None = None) -> None:
        self._swe = _load_swisseph()
        path = ephemeris_path or os.environ.get("GBC_SWISS_EPHE_PATH")
        if path:
            self._swe.set_ephe_path(path)

    def value(self, julian_day: float, profile: AyanamsaProfile) -> float:
        mode = getattr(self._swe, profile.swisseph_mode, None)
        if mode is None:
            raise InvalidCalculationProfileError(
                "This Swiss Ephemeris build does not provide the requested sidereal mode.",
                {"ayanamsa": profile.id, "mode": profile.swisseph_mode},
            )
        self._swe.set_sid_mode(mode, 0, 0)
        return float(self._swe.get_ayanamsa_ut(julian_day))


def longitude_to_sidereal(tropical_longitude: float, ayanamsa: float) -> ZodiacPosition:
    """Rotate a tropical longitude into the sidereal zodiac."""
    return longitude_to_tropical(normalize_longitude(tropical_longitude - ayanamsa))


def _load_swisseph() -> ModuleType:
    try:
        return import_module("swisseph")
    except ImportError as exc:
        raise ProviderDependencyError(
            "Sidereal charts require the optional 'pyswisseph' dependency.",
            {"install": 'python -m pip install "gbc-astro[swiss]"'},
        ) from exc
