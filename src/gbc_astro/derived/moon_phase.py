"""Moon phase primitives."""

from __future__ import annotations

from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.models.chart import MoonPhase
from gbc_astro.models.position import BodyPosition

_PHASES = (
    ("new", 0.0),
    ("waxing_crescent", 45.0),
    ("first_quarter", 90.0),
    ("waxing_gibbous", 135.0),
    ("full", 180.0),
    ("waning_gibbous", 225.0),
    ("last_quarter", 270.0),
    ("waning_crescent", 315.0),
)


def calculate_moon_phase(sun: BodyPosition, moon: BodyPosition) -> MoonPhase:
    phase_angle = normalize_longitude(moon.longitude - sun.longitude)
    name = _phase_name(phase_angle)
    waxing = None if phase_angle in (0.0, 180.0) else phase_angle < 180.0
    return MoonPhase(phase_angle=phase_angle, name=name, waxing=waxing)


def _phase_name(phase_angle: float) -> str:
    # Eight 45-degree sectors centered on the named phase points.
    sector = int(((phase_angle + 22.5) % 360.0) // 45.0)
    return _PHASES[sector][0]

