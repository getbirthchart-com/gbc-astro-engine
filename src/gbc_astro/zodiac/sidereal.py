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
import threading
from importlib import import_module
from types import ModuleType

from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.errors import InvalidCalculationProfileError, ProviderDependencyError
from gbc_astro.models.position import ZodiacPosition
from gbc_astro.profiles.ayanamsa import AYANAMSA_PROFILES, AyanamsaProfile
from gbc_astro.zodiac.tropical import longitude_to_tropical

# Swiss Ephemeris keeps the sidereal mode in process-global state, so selecting
# a mode and reading the ayanamsa are two separate calls against one shared
# variable. FastAPI runs synchronous handlers in a threadpool, so two requests
# for different ayanamsas genuinely interleave: measured under forced GIL
# switching, 1.4% of calls returned another thread's value -- a Lahiri request
# answered with Raman, 1.45 degrees out, enough to move a planet into the
# neighbouring sign. Silently wrong output, not a crash.
#
# The lock is module-level rather than per-instance because the state it guards
# belongs to the library, not to any one calculator.
_SID_MODE_LOCK = threading.Lock()


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
        self.ephemeris_path = ephemeris_path or os.environ.get("GBC_SWISS_EPHE_PATH")
        self._bind_ephe_path()

    def _bind_ephe_path(self) -> None:
        """Re-apply the data path on the calling thread. See SwissEphemerisProvider."""
        if self.ephemeris_path:
            self._swe.set_ephe_path(self.ephemeris_path)

    def value(self, julian_day: float, profile: AyanamsaProfile) -> float:
        mode = getattr(self._swe, profile.swisseph_mode, None)
        if mode is None:
            raise InvalidCalculationProfileError(
                "This Swiss Ephemeris build does not provide the requested sidereal mode.",
                {"ayanamsa": profile.id, "mode": profile.swisseph_mode},
            )
        # Select-then-read must be atomic against every other thread in the
        # process, including ones using a different calculator instance.
        with _SID_MODE_LOCK:
            self._bind_ephe_path()
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
            "Sidereal charts require the 'pyswisseph' dependency.",
            {"install": "python -m pip install gbc-astro"},
        ) from exc
