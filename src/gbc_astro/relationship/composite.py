"""Composite chart: shortest-arc midpoints of two natal charts.

The one thing a composite chart must get right is circular arithmetic. Averaging
359 degrees and 1 degree linearly gives 180, which is the opposite side of the
zodiac from the correct answer of 0. Every position here goes through
`shortest_arc_midpoint`.

Two positions exactly 180 degrees apart have two equally valid midpoints, 180
degrees apart from each other. `shortest_arc_midpoint` returns one of them
deterministically; this module additionally flags the position as ambiguous so
a caller is never misled into treating an arbitrary choice as the answer.

Geometry
--------
Angles and houses are *derived*, not averaged. The common shortcut is to take
the midpoint of each angle separately, which yields an Ascendant and a Midheaven
that do not hold the relationship a real chart's angles do. Instead:

    composite MC = shortest-arc midpoint of the two Midheavens
    ARMC         = right ascension of that Midheaven
    cusps        = houses from ARMC at a reference latitude

A composite chart has no instant, but obliquity needs one, so the profile
declares which to use: the midpoint of the two Julian Days, the same instant a
Davison chart is built at. The reference latitude is the plain mean of the two
birth latitudes, since latitude does not wrap.

Everything the construction rests on -- position method, angle method, house
method, house system, reference latitude, obliquity epoch -- is named in the
profile and echoed in `meta`, so a chart can always be traced back to the
methodology that produced it.
"""

from __future__ import annotations

import math

from gbc_astro.aspects.engine import calculate_aspects
from gbc_astro.astronomy.circular import (
    normalize_longitude,
    shortest_angular_distance,
    shortest_arc_midpoint,
)
from gbc_astro.constants import COMPOSITE_SCHEMA_VERSION, ENGINE_NAME, ENGINE_VERSION
from gbc_astro.errors import HouseCalculationUnavailableError, InvalidCalculationProfileError
from gbc_astro.houses.base import ArmcHouseCalculator, HouseCalculation, assign_house
from gbc_astro.models.chart import NatalChart, WarningMessage
from gbc_astro.models.position import BodyPosition
from gbc_astro.models.relationship import (
    CompositeChart,
    CompositeMidpoint,
    RelationshipMeta,
)
from gbc_astro.profiles.model import RelationshipProfile
from gbc_astro.zodiac.tropical import longitude_to_tropical

# A separation this close to 180 degrees makes the midpoint ambiguous. Chosen so
# that ordinary floating-point noise never trips it but a genuine opposition,
# which astrologers care about, always does.
OPPOSITION_AMBIGUITY_EPSILON_DEG = 1e-6


def is_ambiguous_midpoint(longitude_a: float, longitude_b: float) -> bool:
    """True when the two longitudes are opposite and the midpoint is not unique."""
    separation = shortest_angular_distance(longitude_a, longitude_b)
    return abs(separation - 180.0) <= OPPOSITION_AMBIGUITY_EPSILON_DEG


def right_ascension_of(longitude_deg: float, obliquity_deg: float) -> float:
    """Right ascension of an ecliptic-longitude point on the ecliptic itself.

    Used to recover ARMC from the composite Midheaven. Going forward from
    longitude to right ascension is unambiguous, so no quadrant correction is
    needed: the Midheaven is by definition the ecliptic point whose right
    ascension is the ARMC.
    """
    longitude = math.radians(longitude_deg)
    obliquity = math.radians(obliquity_deg)
    return normalize_longitude(
        math.degrees(
            math.atan2(math.sin(longitude) * math.cos(obliquity), math.cos(longitude))
        )
    )


def calculate_composite(
    chart_a: NatalChart,
    chart_b: NatalChart,
    profile: RelationshipProfile,
    house_calculator: ArmcHouseCalculator | None = None,
) -> CompositeChart:
    _assert_comparable(chart_a, chart_b)

    bodies: dict[str, BodyPosition] = {}
    midpoints: list[CompositeMidpoint] = []
    ambiguous_bodies: list[str] = []

    for body_id in profile.synastry_bodies:
        body_a = chart_a.bodies.get(body_id)
        body_b = chart_b.bodies.get(body_id)
        if body_a is None or body_b is None:
            continue

        longitude = shortest_arc_midpoint(body_a.longitude, body_b.longitude)
        ambiguous = is_ambiguous_midpoint(body_a.longitude, body_b.longitude)
        if ambiguous:
            ambiguous_bodies.append(body_id)

        zodiac = longitude_to_tropical(longitude)
        bodies[body_id] = BodyPosition(
            body_id=body_id,
            longitude=zodiac.longitude,
            # The midpoint of two ecliptic latitudes is a defensible construction
            # in the same sense as the longitude midpoint.
            latitude=(body_a.latitude + body_b.latitude) / 2.0,
            # A composite chart is not an instant, so it has no distance, no
            # speed, and therefore no retrograde state. These stay null rather
            # than carrying a meaningless average. A Davison chart is an actual
            # instant and does carry them.
            distance=None,
            speed_longitude=None,
            retrograde=None,
            sign=zodiac.sign,
            degree_in_sign=zodiac.degree_in_sign,
            house=None,
        )
        midpoints.append(
            CompositeMidpoint(
                body_id=body_id,
                longitude_a=body_a.longitude,
                longitude_b=body_b.longitude,
                separation=shortest_angular_distance(body_a.longitude, body_b.longitude),
                ambiguous=ambiguous,
            )
        )

    geometry, geometry_warnings = _composite_geometry(
        chart_a, chart_b, profile, house_calculator
    )
    if geometry is not None:
        bodies = {
            body_id: _with_house(body, assign_house(body.longitude, geometry.houses))
            for body_id, body in bodies.items()
        }

    warnings: list[WarningMessage] = list(geometry_warnings)
    if ambiguous_bodies:
        warnings.append(
            WarningMessage(
                code="COMPOSITE_MIDPOINT_AMBIGUOUS",
                severity="warning",
                message=(
                    "These bodies are exactly opposite between the two charts, so the "
                    "midpoint is not unique: two points 180 degrees apart are equally "
                    f"valid. A deterministic choice was made for {', '.join(ambiguous_bodies)}. "
                    "See the `midpoints` entries flagged `ambiguous`."
                ),
                fields_affected=tuple(f"bodies.{body}" for body in ambiguous_bodies),
            )
        )

    return CompositeChart(
        schema_version=COMPOSITE_SCHEMA_VERSION,
        meta=RelationshipMeta(
            schema_version=COMPOSITE_SCHEMA_VERSION,
            engine=ENGINE_NAME,
            engine_version=ENGINE_VERSION,
            relationship_profile=profile.id,
            aspect_profile=profile.aspect_profile.id,
            zodiac=chart_a.meta.zodiac,
            chart_a_schema_version=chart_a.schema_version,
            chart_b_schema_version=chart_b.schema_version,
            composite_position_method=profile.composite_position_method,
            composite_angle_method=profile.composite_angle_method if geometry else None,
            composite_house_method=profile.composite_house_method if geometry else None,
            composite_house_system=profile.composite_house_system if geometry else None,
            composite_reference_latitude_method=(
                profile.composite_reference_latitude_method if geometry else None
            ),
            composite_obliquity_epoch=(
                profile.composite_obliquity_epoch if geometry else None
            ),
            house_algorithm_version=geometry.algorithm_version if geometry else None,
        ),
        bodies=bodies,
        angles=geometry.angles if geometry else {},
        houses=geometry.houses if geometry else (),
        aspects=calculate_aspects(
            bodies, profile.aspect_profile, profile.synastry_bodies
        ),
        midpoints=tuple(midpoints),
        warnings=tuple(warnings),
    )


def _composite_geometry(
    chart_a: NatalChart,
    chart_b: NatalChart,
    profile: RelationshipProfile,
    house_calculator: ArmcHouseCalculator | None,
) -> tuple[HouseCalculation | None, list[WarningMessage]]:
    """Derive composite angles and cusps from the midpoint Midheaven."""
    warnings: list[WarningMessage] = []
    if profile.composite_house_method is None:
        warnings.append(
            WarningMessage(
                code="COMPOSITE_HOUSES_UNAVAILABLE",
                severity="info",
                message=(
                    "This profile defines no composite house method, so no angles, no "
                    "house cusps and no body house assignments are produced."
                ),
                fields_affected=("angles", "houses", "bodies.*.house"),
            )
        )
        return None, warnings

    mc_a = chart_a.angles.get("mc")
    mc_b = chart_b.angles.get("mc")
    if mc_a is None or mc_b is None:
        warnings.append(
            WarningMessage(
                code="COMPOSITE_ANGLES_UNAVAILABLE",
                severity="warning",
                message=(
                    "Composite angles and houses were omitted because at least one "
                    "chart has no Midheaven, which is the case when its birth time is "
                    "unknown. No substitute reference was used."
                ),
                fields_affected=("angles", "houses", "bodies.*.house"),
            )
        )
        return None, warnings

    if house_calculator is None:
        from gbc_astro.houses.swiss import SwissHouseCalculator

        house_calculator = SwissHouseCalculator()

    midheaven = shortest_arc_midpoint(mc_a.longitude, mc_b.longitude)
    midpoint_julian_day = (chart_a.subject.julian_day + chart_b.subject.julian_day) / 2.0
    obliquity = house_calculator.obliquity(midpoint_julian_day)
    # Latitude does not wrap, so the plain mean is correct. Longitude is not
    # needed: ARMC already carries the whole of the composite's orientation.
    reference_latitude = (chart_a.subject.latitude + chart_b.subject.latitude) / 2.0

    try:
        geometry = house_calculator.calculate_from_armc(
            armc=right_ascension_of(midheaven, obliquity),
            latitude=reference_latitude,
            obliquity=obliquity,
            house_system=profile.composite_house_system,
        )
    except HouseCalculationUnavailableError as exc:
        warnings.append(
            WarningMessage(
                code="COMPOSITE_HOUSES_UNAVAILABLE",
                severity="warning",
                message=(
                    "Composite houses were omitted: "
                    f"{profile.composite_house_system} has no solution at the "
                    f"reference latitude {reference_latitude:.4f}. "
                    f"{exc.message} No other house system was substituted."
                ),
                fields_affected=("angles", "houses", "bodies.*.house"),
            )
        )
        return None, warnings

    if is_ambiguous_midpoint(mc_a.longitude, mc_b.longitude):
        warnings.append(
            WarningMessage(
                code="COMPOSITE_MIDHEAVEN_AMBIGUOUS",
                severity="warning",
                message=(
                    "The two Midheavens are exactly opposite, so the composite "
                    "Midheaven is not unique and every angle and cusp derived from it "
                    "inherits that choice. Two whole chart orientations 180 degrees "
                    "apart are equally valid here."
                ),
                fields_affected=("angles", "houses"),
            )
        )
    return geometry, warnings


def _with_house(body: BodyPosition, house: int) -> BodyPosition:
    return BodyPosition(
        body_id=body.body_id,
        longitude=body.longitude,
        latitude=body.latitude,
        distance=body.distance,
        speed_longitude=body.speed_longitude,
        retrograde=body.retrograde,
        sign=body.sign,
        degree_in_sign=body.degree_in_sign,
        house=house,
    )


def _assert_comparable(chart_a: NatalChart, chart_b: NatalChart) -> None:
    if chart_a.meta.zodiac != chart_b.meta.zodiac:
        raise InvalidCalculationProfileError(
            "A composite chart requires both charts to use the same zodiac.",
            {"chartAZodiac": chart_a.meta.zodiac, "chartBZodiac": chart_b.meta.zodiac},
        )
    if chart_a.schema_version != chart_b.schema_version:
        raise InvalidCalculationProfileError(
            "A composite chart requires both charts to use the same schema version.",
            {
                "chartASchemaVersion": chart_a.schema_version,
                "chartBSchemaVersion": chart_b.schema_version,
            },
        )
