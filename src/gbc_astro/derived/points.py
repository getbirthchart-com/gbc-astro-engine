"""Vertex, antivertex, Part of Fortune and south node.

All four are positions derived from things the chart already has, so none of
them touches an ephemeris. Two of the four need a birth time and say so.

Zodiac, which is where this would otherwise go wrong
---------------------------------------------------
The engine has been bitten repeatedly by a value calculated in the tropical
frame meeting a chart that has already been rotated into a sidereal one. These
points split cleanly into two cases and the difference is worth stating rather
than rediscovering:

* the **vertex** comes from Swiss Ephemeris, which answers tropically, so it is
  rotated -- but upstream, with the rest of its `HouseCalculation`, so that the
  object is never half one frame and half the other.
* the **Part of Fortune** and the **south node** are computed from longitudes
  the chart already holds, and the ayanamsa cancels through the arithmetic.
  `(Asc - a) + (Moon - a) - (Sun - a)` is `Asc + Moon - Sun - a`, which is the
  sidereal Lot exactly. Rotating them again would double-count it.

So the two are computed at different stages, and the tests pin both.
"""

from __future__ import annotations

from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.models.position import BodyPosition, DerivedPoint
from gbc_astro.profiles.points import SECT_REVERSING, PointProfile
from gbc_astro.zodiac.tropical import longitude_to_tropical

VERTEX = "vertex"
ANTIVERTEX = "antivertex"
PART_OF_FORTUNE = "part_of_fortune"
SOUTH_NODE = "south_node"


def _point(
    point_id: str,
    longitude: float,
    method: str,
    requires_birth_time: bool,
    house: int | None = None,
    alternative_longitude: float | None = None,
) -> DerivedPoint:
    zodiac = longitude_to_tropical(normalize_longitude(longitude))
    return DerivedPoint(
        point_id=point_id,
        longitude=zodiac.longitude,
        sign=zodiac.sign,
        degree_in_sign=zodiac.degree_in_sign,
        house=house,
        method=method,
        requires_birth_time=requires_birth_time,
        alternative_longitude=alternative_longitude,
    )


def is_day_chart(sun: BodyPosition, ascendant_longitude: float) -> bool:
    """True when the Sun is above the horizon.

    Measured against the horizon, not the clock. Houses run forward in zodiacal
    longitude from the Ascendant, so the first six -- Ascendant round to the
    Descendant by way of the IC -- are the half of the chart *below* the
    horizon. The Sun is therefore up when its distance ahead of the Ascendant is
    180 degrees or more.

    Getting this backwards is silent: it produces a well-formed Lot of Fortune
    at the reflection of the right one, on exactly the charts where the two
    conventions disagree.
    """
    return normalize_longitude(sun.longitude - ascendant_longitude) >= 180.0


def part_of_fortune(
    sun: BodyPosition,
    moon: BodyPosition,
    ascendant_longitude: float,
    profile: PointProfile,
) -> DerivedPoint:
    """The Lot of Fortune, under the profile's sect rule.

    By day both conventions agree. By night they give two points reflected about
    the Ascendant, so the one not used is published alongside: a user comparing
    against another program would otherwise read the difference as a defect.
    """
    day = is_day_chart(sun, ascendant_longitude)
    day_formula = ascendant_longitude + moon.longitude - sun.longitude
    night_formula = ascendant_longitude + sun.longitude - moon.longitude

    reverses = profile.part_of_fortune_sect == SECT_REVERSING
    if day or not reverses:
        chosen, other = day_formula, night_formula
        method = "ascendant_plus_moon_minus_sun"
    else:
        chosen, other = night_formula, day_formula
        method = "ascendant_plus_sun_minus_moon"

    return _point(
        PART_OF_FORTUNE,
        chosen,
        method,
        requires_birth_time=True,
        alternative_longitude=(
            None if day else normalize_longitude(other)
        ),
    )


def vertex_points(
    vertex: float,
    profile: PointProfile,
) -> list[DerivedPoint]:
    """The vertex and its opposite.

    The vertex arrives already in the chart's zodiac: a `HouseCalculation` is
    rotated whole for a sidereal chart, angles and cusps and vertex together, so
    that no single tropical value survives inside an otherwise sidereal object.
    Rotating again here would count the ayanamsa twice.
    """
    points: list[DerivedPoint] = []
    rotated = normalize_longitude(vertex)
    if profile.include_vertex:
        points.append(
            _point(
                VERTEX,
                rotated,
                "prime_vertical_ecliptic_intersection_west",
                requires_birth_time=True,
            )
        )
    if profile.include_antivertex:
        points.append(
            _point(
                ANTIVERTEX,
                rotated + 180.0,
                "vertex_opposed",
                requires_birth_time=True,
            )
        )
    return points


def south_node(node: BodyPosition) -> DerivedPoint:
    """The lunar node opposed. Needs no birth time and no decision."""
    return _point(
        SOUTH_NODE,
        node.longitude + 180.0,
        f"{node.body_id}_opposed",
        requires_birth_time=False,
    )
