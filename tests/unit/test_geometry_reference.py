"""Tests for the independent geometry reference.

These assert the reference against its own defining properties, never against
Swiss Ephemeris. Agreement between the two is the subject of the differential
gate (`gbc validate geometry-parity`), not of these unit tests -- checking the
reference against the implementation it exists to validate would defeat its
purpose.
"""

from __future__ import annotations

import math

import pytest

from gbc_astro.validation.geometry import (
    GeometryReference,
    GeometryUndefinedError,
    _declination,
    _norm180,
    _right_ascension,
    _semi_diurnal_arc,
)

skyfield = pytest.importorskip("skyfield", reason="Independent geometry reference needs skyfield")

# 1990-06-21T12:00:00Z and 1990-12-21T00:00:00Z.
SOLSTICE_JD = 2448064.0
WINTER_JD = 2448246.5


@pytest.fixture(scope="module")
def reference() -> GeometryReference:
    return GeometryReference()


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (0.0, 0.0),
        (21.0285, 105.8542),
        (-33.8688, 151.2093),
        (51.5074, -0.1278),
        (-1.2921, 36.8219),
        (64.1466, -21.9426),
    ],
)
def test_midheaven_right_ascension_equals_ramc(
    reference: GeometryReference, latitude: float, longitude: float
) -> None:
    """The MC is defined as the ecliptic point whose RA is the RAMC."""
    geometry = reference.calculate(SOLSTICE_JD, latitude, longitude)
    right_ascension = _right_ascension(geometry.midheaven, geometry.obliquity)
    assert abs(_norm180(right_ascension - geometry.ramc)) < 1e-9


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (0.0, 0.0),
        (21.0285, 105.8542),
        (-33.8688, 151.2093),
        (51.5074, -0.1278),
        (64.1466, -21.9426),
    ],
)
def test_ascendant_lies_on_the_horizon_and_is_rising(
    reference: GeometryReference, latitude: float, longitude: float
) -> None:
    """The ASC has zero altitude and sits in the eastern (rising) semicircle."""
    geometry = reference.calculate(SOLSTICE_JD, latitude, longitude)
    declination = math.radians(_declination(geometry.ascendant, geometry.obliquity))
    hour_angle = _norm180(geometry.ramc - _right_ascension(geometry.ascendant, geometry.obliquity))
    phi = math.radians(latitude)
    sin_altitude = math.sin(phi) * math.sin(declination) + math.cos(phi) * math.cos(
        declination
    ) * math.cos(math.radians(hour_angle))

    assert abs(math.degrees(math.asin(sin_altitude))) < 1e-9
    assert -180.0 < hour_angle < 0.0


def test_cusps_advance_in_zodiacal_order_and_close_the_circle(
    reference: GeometryReference,
) -> None:
    geometry = reference.calculate(WINTER_JD, 40.7128, -74.0060)
    total = 0.0
    for index in range(12):
        step = (geometry.cusps[(index + 1) % 12] - geometry.cusps[index]) % 360.0
        assert 0.0 < step < 180.0
        total += step
    assert abs(total - 360.0) < 1e-6


def test_angles_are_opposing_pairs(reference: GeometryReference) -> None:
    geometry = reference.calculate(WINTER_JD, 35.6762, 139.6503)
    assert abs(_norm180(geometry.descendant - geometry.ascendant - 180.0)) < 1e-9
    assert abs(_norm180(geometry.imum_coeli - geometry.midheaven - 180.0)) < 1e-9
    assert abs(_norm180(geometry.cusps[0] - geometry.ascendant)) < 1e-9
    assert abs(_norm180(geometry.cusps[9] - geometry.midheaven)) < 1e-9


def test_placidus_cusps_sit_at_their_defining_arc_fraction(
    reference: GeometryReference,
) -> None:
    """Cusp 11 is 1/3 and cusp 12 is 2/3 of the semi-diurnal arc before culmination."""
    latitude = 40.7128
    geometry = reference.calculate(WINTER_JD, latitude, -74.0060)

    for cusp_index, fraction in ((10, 1.0 / 3.0), (11, 2.0 / 3.0)):
        longitude = geometry.cusps[cusp_index]
        declination = _declination(longitude, geometry.obliquity)
        semi_diurnal = _semi_diurnal_arc(declination, latitude)
        hour_angle = _norm180(geometry.ramc - _right_ascension(longitude, geometry.obliquity))
        assert abs(hour_angle - (-fraction * semi_diurnal)) < 1e-6


def test_semi_diurnal_arc_undefined_when_circumpolar() -> None:
    with pytest.raises(GeometryUndefinedError):
        _semi_diurnal_arc(dec_deg=23.44, lat_deg=80.0)


def test_placidus_undefined_beyond_polar_circle(reference: GeometryReference) -> None:
    """Above the polar circle at solstice some cusps have no solution at all."""
    with pytest.raises(GeometryUndefinedError):
        reference.calculate(SOLSTICE_JD, 78.2232, 15.6267)


def test_sidereal_time_advances_with_the_day(reference: GeometryReference) -> None:
    """A sidereal day is shorter than a solar day by about 3m56s (~0.9856 deg)."""
    first, _ = reference.sidereal_time_and_obliquity(SOLSTICE_JD)
    second, _ = reference.sidereal_time_and_obliquity(SOLSTICE_JD + 1.0)
    assert abs(_norm180(second - first) - 0.9856) < 0.01


def test_obliquity_is_within_the_modern_range(reference: GeometryReference) -> None:
    _, obliquity = reference.sidereal_time_and_obliquity(SOLSTICE_JD)
    assert 23.4 < obliquity < 23.5
