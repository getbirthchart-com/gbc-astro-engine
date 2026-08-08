"""Composite chart: shortest-arc midpoints of two natal charts.

The one thing a composite chart must get right is circular arithmetic. Averaging
359 degrees and 1 degree linearly gives 180, which is the opposite side of the
zodiac from the correct answer of 0. Every position here goes through
`shortest_arc_midpoint`.

Two positions exactly 180 degrees apart have two equally valid midpoints, 180
degrees apart from each other. `shortest_arc_midpoint` returns one of them
deterministically; this module additionally flags the position as ambiguous so
a caller is never misled into treating an arbitrary choice as the answer.
"""

from __future__ import annotations

from gbc_astro.aspects.engine import calculate_aspects
from gbc_astro.astronomy.circular import shortest_angular_distance, shortest_arc_midpoint
from gbc_astro.constants import COMPOSITE_SCHEMA_VERSION, ENGINE_NAME, ENGINE_VERSION
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.models.chart import NatalChart, WarningMessage
from gbc_astro.models.position import AnglePosition, BodyPosition
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


def calculate_composite(
    chart_a: NatalChart,
    chart_b: NatalChart,
    profile: RelationshipProfile,
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
            # than carrying a meaningless average.
            distance=None,
            speed_longitude=None,
            retrograde=None,
            sign=zodiac.sign,
            degree_in_sign=zodiac.degree_in_sign,
            # Houses require a house method, which this profile does not define.
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

    angles, angle_warnings = _composite_angles(chart_a, chart_b, profile)

    warnings: list[WarningMessage] = list(angle_warnings)
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
    if profile.composite_house_method is None:
        warnings.append(
            WarningMessage(
                code="COMPOSITE_HOUSES_UNAVAILABLE",
                severity="info",
                message=(
                    "This profile defines no composite house method, so no house cusps "
                    "and no body house assignments are produced. Deriving them would "
                    "require a reference time and place that a composite chart does "
                    "not have."
                ),
                fields_affected=("houses", "bodies.*.house"),
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
            composite_angle_method=profile.composite_angle_method if angles else None,
            composite_house_method=profile.composite_house_method,
        ),
        bodies=bodies,
        angles=angles,
        aspects=calculate_aspects(bodies, profile.aspect_profile),
        midpoints=tuple(midpoints),
        warnings=tuple(warnings),
    )


def _composite_angles(
    chart_a: NatalChart,
    chart_b: NatalChart,
    profile: RelationshipProfile,
) -> tuple[dict[str, AnglePosition], list[WarningMessage]]:
    warnings: list[WarningMessage] = []
    if profile.composite_angle_method is None:
        return {}, warnings
    if not chart_a.angles or not chart_b.angles:
        warnings.append(
            WarningMessage(
                code="COMPOSITE_ANGLES_UNAVAILABLE",
                severity="warning",
                message=(
                    "Composite angles were omitted because at least one chart has no "
                    "angles, which is the case when its birth time is unknown."
                ),
                fields_affected=("angles",),
            )
        )
        return {}, warnings

    angles: dict[str, AnglePosition] = {}
    for angle_id in profile.synastry_angles:
        angle_a = chart_a.angles.get(angle_id)
        angle_b = chart_b.angles.get(angle_id)
        if angle_a is None or angle_b is None:
            continue
        zodiac = longitude_to_tropical(
            shortest_arc_midpoint(angle_a.longitude, angle_b.longitude)
        )
        angles[angle_id] = AnglePosition(
            longitude=zodiac.longitude,
            sign=zodiac.sign,
            degree_in_sign=zodiac.degree_in_sign,
        )

    if angles:
        warnings.append(
            WarningMessage(
                code="COMPOSITE_ANGLES_NOT_MUTUALLY_CONSISTENT",
                severity="info",
                message=(
                    "Composite angles are the midpoints of each chart's angles, taken "
                    "independently. They therefore need not hold the geometric "
                    "relationship that a real chart's angles do, and the Descendant "
                    "and IC are midpoints in their own right rather than the exact "
                    "opposites of the Ascendant and Midheaven."
                ),
                fields_affected=("angles",),
            )
        )
    return angles, warnings


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
