"""Independent astrology-geometry reference.

VALIDATION ONLY. Nothing in the calculation path may import this module.

Purpose
-------
`gbc_astro.houses.swiss` delegates Ascendant, Midheaven and Placidus cusps to
Swiss Ephemeris. That path cannot validate itself, and neither can any reference
that is itself backed by Swiss Ephemeris -- which covers most public astrology
libraries and calculator sites. `docs/HOUSE_REFERENCE_METHODOLOGY.md` therefore
requires a separately implemented reference.

This module is that second implementation. It shares no code with Swiss
Ephemeris. It takes only two astronomical inputs from Skyfield -- Greenwich
apparent sidereal time and the true obliquity of the ecliptic -- and derives
every angle and cusp from first principles by solving the defining spherical
relation numerically.

Method
------
An ecliptic point of longitude `lam` has equatorial coordinates

    ra  = atan2(sin(lam) * cos(eps), cos(lam))
    dec = asin(sin(lam) * sin(eps))

and local hour angle `H = RAMC - ra`, where `RAMC = GAST + geographic longitude`.

Rather than evaluating published closed-form cusp formulae -- whose quadrant and
sign conventions are the usual source of silent error -- each angle and cusp is
defined by the condition it must satisfy and located by bracketing plus
bisection:

* Midheaven: the ecliptic point whose right ascension equals RAMC (`H = 0`).
* Ascendant: the ecliptic point on the horizon, `sin(alt) = 0`, restricted to
  the rising (eastern) semicircle `H in (-180, 0)`.
* Placidus cusps: the ecliptic point that has traversed a fixed fraction of its
  semi-diurnal arc `SD = acos(-tan(phi) * tan(dec))`, or of its semi-nocturnal
  arc `SN = 180 - SD`:

      cusp 11: H = -(1/3) * SD          cusp 2: H = -180 + (2/3) * SN
      cusp 12: H = -(2/3) * SD          cusp 3: H = -180 + (1/3) * SN
      cusp  1: H = -SD  (the Ascendant) cusp 4: H = -180  (the IC)

  Cusps 4-9 are the opposing points of cusps 10-3.

Where `|tan(phi) * tan(dec)| > 1` the body is circumpolar, the semi-diurnal arc
does not exist, and Placidus is mathematically undefined. That case raises
`GeometryUndefinedError` so the caller can classify and exclude it rather than
silently comparing a different house system, as the spec requires.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from gbc_astro.errors import ProviderDependencyError

__all__ = [
    "GeometryReference",
    "GeometryUndefinedError",
    "ReferenceGeometry",
]

# Scan step for root bracketing, in degrees of ecliptic longitude. Small enough
# that no cusp condition changes sign twice inside one step at any latitude the
# corpus covers, large enough to keep 500+ cases fast.
_SCAN_STEP_DEG = 0.25

# A sign change spanning more than this is a wrap discontinuity in the residual,
# not a root.
_DISCONTINUITY_DEG = 90.0

_BISECTION_ITERATIONS = 80


class GeometryUndefinedError(RuntimeError):
    """Raised when the requested geometry does not exist for the input."""


@dataclass(frozen=True)
class ReferenceGeometry:
    """Independently derived angles and Placidus cusps, in degrees."""

    ascendant: float
    midheaven: float
    descendant: float
    imum_coeli: float
    cusps: tuple[float, ...]
    ramc: float
    obliquity: float

    def as_chart_fragment(self) -> dict[str, Any]:
        """Shape the result like the canonical chart, for the differential comparator."""
        return {
            "angles": {
                "ascendant": {"longitude": self.ascendant},
                "mc": {"longitude": self.midheaven},
                "descendant": {"longitude": self.descendant},
                "ic": {"longitude": self.imum_coeli},
            },
            "houses": [
                {"number": index + 1, "cuspLongitude": cusp}
                for index, cusp in enumerate(self.cusps)
            ],
        }


def _norm360(degrees: float) -> float:
    return degrees % 360.0


def _norm180(degrees: float) -> float:
    """Wrap to (-180, 180]."""
    wrapped = (degrees + 180.0) % 360.0 - 180.0
    return 180.0 if wrapped == -180.0 else wrapped


def _right_ascension(lam_deg: float, eps_deg: float) -> float:
    lam = math.radians(lam_deg)
    eps = math.radians(eps_deg)
    return _norm360(math.degrees(math.atan2(math.sin(lam) * math.cos(eps), math.cos(lam))))


def _declination(lam_deg: float, eps_deg: float) -> float:
    lam = math.radians(lam_deg)
    eps = math.radians(eps_deg)
    return math.degrees(math.asin(math.sin(lam) * math.sin(eps)))


def _semi_diurnal_arc(dec_deg: float, lat_deg: float) -> float:
    """Semi-diurnal arc in degrees, or raise if the point is circumpolar."""
    argument = -math.tan(math.radians(lat_deg)) * math.tan(math.radians(dec_deg))
    if abs(argument) > 1.0:
        raise GeometryUndefinedError(
            "Semi-diurnal arc is undefined: the ecliptic point is circumpolar at this latitude."
        )
    return math.degrees(math.acos(argument))


def _solve(residual: Callable[[float], float], start_deg: float = 0.0) -> float:
    """Locate the unique ecliptic longitude where `residual` crosses zero.

    Scans a full circle from `start_deg`, discards sign changes that are wrap
    discontinuities rather than roots, then bisects. Raises if the condition has
    no root or more than one.
    """
    brackets: list[tuple[float, float]] = []
    steps = int(round(360.0 / _SCAN_STEP_DEG))

    previous_lam = start_deg
    try:
        previous_value = residual(previous_lam)
    except GeometryUndefinedError:
        previous_value = math.nan

    for index in range(1, steps + 1):
        current_lam = start_deg + index * _SCAN_STEP_DEG
        try:
            current_value = residual(current_lam)
        except GeometryUndefinedError:
            current_value = math.nan

        if not (math.isnan(previous_value) or math.isnan(current_value)):
            if previous_value == 0.0:
                brackets.append((previous_lam, previous_lam))
            elif (
                previous_value < 0.0 < current_value or current_value < 0.0 < previous_value
            ) and abs(current_value - previous_value) < _DISCONTINUITY_DEG:
                brackets.append((previous_lam, current_lam))

        previous_lam, previous_value = current_lam, current_value

    if not brackets:
        raise GeometryUndefinedError("Geometry condition has no solution for this input.")
    if len(brackets) > 1:
        raise GeometryUndefinedError(
            f"Geometry condition is ambiguous: {len(brackets)} roots found."
        )

    low, high = brackets[0]
    if low == high:
        return _norm360(low)

    low_value = residual(low)
    for _ in range(_BISECTION_ITERATIONS):
        middle = (low + high) / 2.0
        middle_value = residual(middle)
        if middle_value == 0.0:
            return _norm360(middle)
        if (low_value < 0.0) != (middle_value < 0.0):
            high = middle
        else:
            low, low_value = middle, middle_value
    return _norm360((low + high) / 2.0)


class GeometryReference:
    """Second, independent implementation of ASC/MC and Placidus cusps."""

    id = "gbc-independent-geometry"
    version = "1.0.0"
    method = "skyfield-gast+true-obliquity/numeric-placidus"

    def __init__(self) -> None:
        try:
            skyfield_api = import_module("skyfield.api")
            self._nutationlib = import_module("skyfield.nutationlib")
        except ImportError as exc:
            raise ProviderDependencyError(
                "Independent geometry validation requires the optional 'skyfield' dependency.",
                {"install": 'python -m pip install "gbc-astro[validation]"'},
            ) from exc
        self._timescale = skyfield_api.load.timescale()

    def sidereal_time_and_obliquity(self, julian_day_ut: float) -> tuple[float, float]:
        """Return (Greenwich apparent sidereal time in degrees, true obliquity in degrees).

        Both come from Skyfield, which resolves them from IAU nutation series and
        has no dependency on Swiss Ephemeris. The engine's Julian Day is UT, and
        Swiss Ephemeris likewise treats its `houses_ex` argument as UT, so both
        sides derive sidereal time from the same time argument.
        """
        instant = self._timescale.ut1_jd(julian_day_ut)
        gast_degrees = float(instant.gast) * 15.0
        true_obliquity = float(self._nutationlib.earth_tilt(instant)[1])
        return _norm360(gast_degrees), true_obliquity

    def calculate(
        self,
        julian_day_ut: float,
        latitude: float,
        longitude: float,
    ) -> ReferenceGeometry:
        gast, eps = self.sidereal_time_and_obliquity(julian_day_ut)
        ramc = _norm360(gast + longitude)

        midheaven = self._midheaven(ramc, eps)
        ascendant = self._ascendant(ramc, eps, latitude)
        cusps = self._placidus_cusps(ramc, eps, latitude, ascendant, midheaven)

        return ReferenceGeometry(
            ascendant=ascendant,
            midheaven=midheaven,
            descendant=_norm360(ascendant + 180.0),
            imum_coeli=_norm360(midheaven + 180.0),
            cusps=cusps,
            ramc=ramc,
            obliquity=eps,
        )

    def _midheaven(self, ramc: float, eps: float) -> float:
        """The ecliptic point whose right ascension equals RAMC."""
        candidate = _norm360(
            math.degrees(
                math.atan2(
                    math.sin(math.radians(ramc)),
                    math.cos(math.radians(ramc)) * math.cos(math.radians(eps)),
                )
            )
        )
        # atan2 resolves the quadrant, but assert the defining property rather
        # than trusting it: the opposing point has RA = RAMC + 180.
        if abs(_norm180(_right_ascension(candidate, eps) - ramc)) > 1e-6:
            candidate = _norm360(candidate + 180.0)
        return candidate

    def _ascendant(self, ramc: float, eps: float, latitude: float) -> float:
        """The ecliptic point on the horizon in the rising semicircle."""
        phi = math.radians(latitude)

        def residual(lam: float) -> float:
            dec = math.radians(_declination(lam, eps))
            hour_angle = _norm180(ramc - _right_ascension(lam, eps))
            if not -180.0 < hour_angle < 0.0:
                # Setting half of the horizon: not the Ascendant.
                raise GeometryUndefinedError("Outside the rising semicircle.")
            sin_altitude = math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(
                math.radians(hour_angle)
            )
            return math.degrees(math.asin(max(-1.0, min(1.0, sin_altitude))))

        return _solve(residual)

    def _placidus_cusps(
        self,
        ramc: float,
        eps: float,
        latitude: float,
        ascendant: float,
        midheaven: float,
    ) -> tuple[float, ...]:
        cusp_11 = self._placidus_cusp(ramc, eps, latitude, diurnal=True, fraction=1.0 / 3.0)
        cusp_12 = self._placidus_cusp(ramc, eps, latitude, diurnal=True, fraction=2.0 / 3.0)
        cusp_2 = self._placidus_cusp(ramc, eps, latitude, diurnal=False, fraction=2.0 / 3.0)
        cusp_3 = self._placidus_cusp(ramc, eps, latitude, diurnal=False, fraction=1.0 / 3.0)

        cusps = (
            ascendant,
            cusp_2,
            cusp_3,
            _norm360(midheaven + 180.0),
            _norm360(cusp_11 + 180.0),
            _norm360(cusp_12 + 180.0),
            _norm360(ascendant + 180.0),
            _norm360(cusp_2 + 180.0),
            _norm360(cusp_3 + 180.0),
            midheaven,
            cusp_11,
            cusp_12,
        )
        _assert_monotonic(cusps)
        return cusps

    def _placidus_cusp(
        self,
        ramc: float,
        eps: float,
        latitude: float,
        diurnal: bool,
        fraction: float,
    ) -> float:
        """Locate the cusp at `fraction` of the semi-diurnal or semi-nocturnal arc."""

        def residual(lam: float) -> float:
            dec = _declination(lam, eps)
            semi_diurnal = _semi_diurnal_arc(dec, latitude)
            if diurnal:
                target = -fraction * semi_diurnal
            else:
                target = -180.0 + fraction * (180.0 - semi_diurnal)
            hour_angle = _norm180(ramc - _right_ascension(lam, eps))
            return _norm180(hour_angle - target)

        return _solve(residual)


def _assert_monotonic(cusps: tuple[float, ...]) -> None:
    """House cusps must advance in zodiacal order around the full circle."""
    total = 0.0
    for index in range(12):
        step = _norm360(cusps[(index + 1) % 12] - cusps[index])
        if step <= 0.0 or step >= 180.0:
            raise GeometryUndefinedError(
                f"Cusp sequence is not monotonic at house {index + 1}: step {step:.6f} deg."
            )
        total += step
    if abs(total - 360.0) > 1e-6:
        raise GeometryUndefinedError(f"Cusp sequence does not close the circle: {total:.6f} deg.")


def porphyry_cusps(ascendant: float, midheaven: float) -> tuple[float, ...]:
    """Porphyry cusps from the angles alone.

    Definition: trisect the ecliptic arc from the Midheaven to the Ascendant,
    and the arc from the Ascendant to the Imum Coeli. Nothing else is involved,
    which is why Porphyry is defined at every latitude and why it can be derived
    here without any spherical trigonometry at all.
    """
    upper = (ascendant - midheaven) % 360.0
    lower = ((midheaven + 180.0) - ascendant) % 360.0
    first_six = {
        10: midheaven,
        11: _norm360(midheaven + upper / 3.0),
        12: _norm360(midheaven + 2.0 * upper / 3.0),
        1: ascendant,
        2: _norm360(ascendant + lower / 3.0),
        3: _norm360(ascendant + 2.0 * lower / 3.0),
    }
    cusps = dict(first_six)
    for number, longitude in first_six.items():
        opposite = number + 6 if number <= 6 else number - 6
        cusps[opposite] = _norm360(longitude + 180.0)
    return tuple(cusps[number] for number in range(1, 13))


def meridian_cusps(ramc: float, obliquity: float) -> tuple[float, ...]:
    """Meridian (axial rotation) cusps.

    Definition: cusp k is the ecliptic point whose right ascension is
    `RAMC + 30 * (k - 10)`. Cusp 10 is therefore the Midheaven by construction,
    and the horizon plays no part -- which is why cusp 1 is the East Point
    rather than the Ascendant.
    """
    cusps: list[float] = []
    for number in range(1, 13):
        right_ascension = _norm360(ramc + 30.0 * (number - 10))
        radians = math.radians(right_ascension)
        longitude = _norm360(
            math.degrees(
                math.atan2(
                    math.sin(radians),
                    math.cos(radians) * math.cos(math.radians(obliquity)),
                )
            )
        )
        # atan2 resolves the quadrant, but assert the defining property rather
        # than trusting it: the opposing point has RA + 180.
        if abs(_norm180(_right_ascension(longitude, obliquity) - right_ascension)) > 1e-6:
            longitude = _norm360(longitude + 180.0)
        cusps.append(longitude)
    return tuple(cusps)
