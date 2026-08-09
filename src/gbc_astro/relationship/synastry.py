"""Synastry: cross aspects, house overlays and angle interactions.

Takes two already-calculated natal charts rather than raw birth data, so both
sides are guaranteed to have been built under the same zodiac and profile
semantics, and neither chart is silently recomputed.

Where a chart has no birth time it has no houses and no angles. The directions
that depend on them are omitted and a warning names them, never approximated.
"""

from __future__ import annotations

from gbc_astro.aspects.engine import aspect_phase, match_aspect_rule
from gbc_astro.astronomy.circular import shortest_angular_distance
from gbc_astro.constants import ENGINE_NAME, ENGINE_VERSION, SYNASTRY_SCHEMA_VERSION
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.houses.base import assign_house
from gbc_astro.models.chart import NatalChart, WarningMessage
from gbc_astro.models.enums import AspectPhase
from gbc_astro.models.position import BodyPosition
from gbc_astro.models.relationship import (
    CHART_A,
    CHART_B,
    AngleInteraction,
    CrossAspect,
    HouseOverlay,
    RelationshipMeta,
    SynastryChart,
)
from gbc_astro.profiles.model import RelationshipProfile


def calculate_cross_aspects(
    chart_a: NatalChart,
    chart_b: NatalChart,
    profile: RelationshipProfile,
) -> tuple[CrossAspect, ...]:
    """Every configured A body against every configured B body.

    Unlike natal aspects this is the full product, not combinations: A.sun to
    B.sun is a real synastry contact, and A.sun to B.moon is distinct from
    A.moon to B.sun.
    """
    aspects: list[CrossAspect] = []
    for body_a_id in profile.synastry_bodies:
        body_a = chart_a.bodies.get(body_a_id)
        if body_a is None:
            continue
        for body_b_id in profile.synastry_bodies:
            body_b = chart_b.bodies.get(body_b_id)
            if body_b is None:
                continue
            separation = shortest_angular_distance(body_a.longitude, body_b.longitude)
            matched = match_aspect_rule(separation, profile.synastry_aspect_profile)
            if matched is None:
                continue
            rule, orb = matched
            aspects.append(
                CrossAspect(
                    body_a=body_a_id,
                    body_b=body_b_id,
                    aspect_type=rule.aspect_type,
                    exact_angle=rule.exact_angle,
                    actual_angle=separation,
                    orb=orb,
                    phase=_cross_aspect_phase(body_a, body_b, rule.exact_angle, orb, profile),
                )
            )
    return tuple(aspects)


def _cross_aspect_phase(
    body_a: BodyPosition,
    body_b: BodyPosition,
    exact_angle: float,
    orb: float,
    profile: RelationshipProfile,
) -> str:
    """Phase for a cross aspect, according to the profile's declared policy.

    The default is `indeterminate`: applying and separating describe motion
    along a shared timeline, and two natal charts are frozen instants belonging
    to different people. `natal_speed_convention` opts into the traditional
    reading that runs the two natal speeds through the natal phase logic. That
    is a convention rather than physics, and the chart's warnings say so
    whenever it is switched on. For a physically real answer, use a Davison
    chart, which is an actual instant with actual motion.
    """
    if profile.cross_aspect_phase_policy != "natal_speed_convention":
        return AspectPhase.INDETERMINATE.value
    return aspect_phase(
        body_a, body_b, exact_angle, orb, profile.synastry_aspect_profile.exact_epsilon_deg
    ).value


def calculate_house_overlays(
    body_chart: NatalChart,
    house_chart: NatalChart,
    body_chart_id: str,
    house_chart_id: str,
    profile: RelationshipProfile,
) -> tuple[HouseOverlay, ...]:
    """Place one chart's bodies in the other chart's houses."""
    if not house_chart.houses:
        return ()
    overlays: list[HouseOverlay] = []
    for body_id in profile.synastry_bodies:
        body = body_chart.bodies.get(body_id)
        if body is None:
            continue
        overlays.append(
            HouseOverlay(
                body=body_id,
                body_chart=body_chart_id,
                house_chart=house_chart_id,
                house=assign_house(body.longitude, house_chart.houses),
                body_longitude=body.longitude,
            )
        )
    return tuple(overlays)


def calculate_angle_interactions(
    chart_a: NatalChart,
    chart_b: NatalChart,
    profile: RelationshipProfile,
) -> tuple[AngleInteraction, ...]:
    """Aspects between one chart's bodies and the other chart's angles, both ways."""
    interactions: list[AngleInteraction] = []
    for body_chart, angle_chart, body_chart_id, angle_chart_id in (
        (chart_a, chart_b, CHART_A, CHART_B),
        (chart_b, chart_a, CHART_B, CHART_A),
    ):
        if not angle_chart.angles:
            continue
        for body_id in profile.synastry_bodies:
            body = body_chart.bodies.get(body_id)
            if body is None:
                continue
            for angle_id in profile.synastry_angles:
                angle = angle_chart.angles.get(angle_id)
                if angle is None:
                    continue
                separation = shortest_angular_distance(body.longitude, angle.longitude)
                matched = match_aspect_rule(separation, profile.synastry_aspect_profile)
                if matched is None:
                    continue
                rule, orb = matched
                interactions.append(
                    AngleInteraction(
                        body=body_id,
                        body_chart=body_chart_id,
                        angle=angle_id,
                        angle_chart=angle_chart_id,
                        aspect_type=rule.aspect_type,
                        exact_angle=rule.exact_angle,
                        actual_angle=separation,
                        orb=orb,
                    )
                )
    return tuple(interactions)


def calculate_synastry(
    chart_a: NatalChart,
    chart_b: NatalChart,
    profile: RelationshipProfile,
) -> SynastryChart:
    _assert_comparable(chart_a, chart_b)

    warnings: list[WarningMessage] = []
    missing_houses = [
        name
        for name, chart in ((CHART_A, chart_a), (CHART_B, chart_b))
        if not chart.houses
    ]
    if missing_houses:
        affected: list[str] = []
        if CHART_A in missing_houses:
            affected.append("bBodiesInAHouses")
        if CHART_B in missing_houses:
            affected.append("aBodiesInBHouses")
        warnings.append(
            WarningMessage(
                code="SYNASTRY_HOUSE_OVERLAY_UNAVAILABLE",
                severity="warning",
                message=(
                    "House overlays were omitted because chart "
                    f"{' and '.join(missing_houses)} has no houses. A chart without a "
                    "known birth time has no house cusps, and no substitute was used."
                ),
                fields_affected=tuple(affected),
            )
        )

    missing_angles = [
        name
        for name, chart in ((CHART_A, chart_a), (CHART_B, chart_b))
        if not chart.angles
    ]
    if missing_angles:
        warnings.append(
            WarningMessage(
                code="SYNASTRY_ANGLE_INTERACTIONS_PARTIAL",
                severity="warning",
                message=(
                    "Angle interactions against chart "
                    f"{' and '.join(missing_angles)} were omitted because that chart "
                    "has no angles without a known birth time."
                ),
                fields_affected=("angleInteractions",),
            )
        )

    if profile.cross_aspect_phase_policy == "natal_speed_convention":
        warnings.append(
            WarningMessage(
                code="SYNASTRY_PHASE_BY_CONVENTION",
                severity="warning",
                message=(
                    "Cross-aspect phases were produced from the two natal speeds under "
                    "the traditional synastry convention. This is a convention, not "
                    "physics: the two charts are frozen instants belonging to different "
                    "people and share no timeline along which anything applies or "
                    "separates. For a physically real phase, use a Davison chart."
                ),
                fields_affected=("crossAspects",),
            )
        )
    else:
        warnings.append(
            WarningMessage(
                code="SYNASTRY_PHASE_INDETERMINATE",
                severity="info",
                message=(
                    "Cross aspects report phase 'indeterminate'. Applying and separating "
                    "describe motion along a shared timeline, which two natal charts do "
                    "not share. Set the profile's cross_aspect_phase_policy to "
                    "'natal_speed_convention' to opt into the traditional convention, or "
                    "use a Davison chart for a physically real phase."
                ),
                fields_affected=("crossAspects",),
            )
        )

    return SynastryChart(
        schema_version=SYNASTRY_SCHEMA_VERSION,
        meta=RelationshipMeta(
            schema_version=SYNASTRY_SCHEMA_VERSION,
            engine=ENGINE_NAME,
            engine_version=ENGINE_VERSION,
            relationship_profile=profile.id,
            aspect_profile=profile.synastry_aspect_profile.id,
            zodiac=chart_a.meta.zodiac,
            chart_a_schema_version=chart_a.schema_version,
            chart_b_schema_version=chart_b.schema_version,
            cross_aspect_phase_policy=profile.cross_aspect_phase_policy,
        ),
        chart_a=chart_a,
        chart_b=chart_b,
        cross_aspects=calculate_cross_aspects(chart_a, chart_b, profile),
        a_bodies_in_b_houses=calculate_house_overlays(
            chart_a, chart_b, CHART_A, CHART_B, profile
        ),
        b_bodies_in_a_houses=calculate_house_overlays(
            chart_b, chart_a, CHART_B, CHART_A, profile
        ),
        angle_interactions=calculate_angle_interactions(chart_a, chart_b, profile),
        warnings=tuple(warnings),
    )


def _assert_comparable(chart_a: NatalChart, chart_b: NatalChart) -> None:
    """Refuse to compare charts built under different semantics.

    Cross aspects between a tropical and a sidereal chart, or between charts on
    different schema versions, would be arithmetic on incompatible frames.
    """
    if chart_a.meta.zodiac != chart_b.meta.zodiac:
        raise InvalidCalculationProfileError(
            "Synastry requires both charts to use the same zodiac.",
            {"chartAZodiac": chart_a.meta.zodiac, "chartBZodiac": chart_b.meta.zodiac},
        )
    if chart_a.schema_version != chart_b.schema_version:
        raise InvalidCalculationProfileError(
            "Synastry requires both charts to use the same schema version.",
            {
                "chartASchemaVersion": chart_a.schema_version,
                "chartBSchemaVersion": chart_b.schema_version,
            },
        )
