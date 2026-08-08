"""Transit snapshot: where the sky is now against a fixed natal chart.

The contrast with synastry matters. Two natal charts are two frozen instants and
share no timeline, which is why cross-aspect phase there is `indeterminate`. A
transit chart is not like that: the transiting bodies are genuinely moving while
the natal points stay put, so applying and separating describe something that is
actually happening. The phase here is physics, not convention.

Orbs come from `TRANSIT_ASPECT_PROFILE_V1`, not from the natal profile. Natal
orbs are right for reading a birth chart and wrong for "what is happening now" --
they leave three to four dozen aspects active at every moment, which is no basis
for surfacing a meaningful few. See `gbc_astro.profiles.transit` for the
measurements behind the chosen values.

Ranking is a product relevance ordering with every weight published in the
result. It is not a claim about astrological truth, and no model of any kind is
involved in producing it.
"""

from __future__ import annotations

from datetime import datetime, timezone

from gbc_astro.aspects.engine import match_aspect_rule
from gbc_astro.astronomy.circular import normalize_longitude, shortest_angular_distance
from gbc_astro.astronomy.time import isoformat_z
from gbc_astro.constants import ENGINE_NAME, ENGINE_VERSION, TRANSIT_SCHEMA_VERSION
from gbc_astro.houses.base import assign_house
from gbc_astro.models.chart import NatalChart, WarningMessage
from gbc_astro.models.enums import AspectPhase
from gbc_astro.models.forecast import TransitAspect, TransitChart, TransitHousePlacement
from gbc_astro.models.position import BodyPosition
from gbc_astro.profiles.model import CalculationProfile
from gbc_astro.profiles.transit import TRANSIT_PROFILE_V1, TransitProfile
from gbc_astro.providers.base import EphemerisProvider
from gbc_astro.providers.normalization import normalize_body_position
from gbc_astro.zodiac.tropical import longitude_to_tropical

# The step used to decide whether a transit is closing on an aspect or leaving
# it. Small enough that the answer is the instantaneous one, large enough to
# stay well clear of floating-point noise in the separation.
PHASE_TIMESTEP_DAYS = 1.0e-3

NATAL_TARGET_BODY = "body"
NATAL_TARGET_ANGLE = "angle"


def transit_phase(
    transit_body: BodyPosition,
    natal_longitude: float,
    exact_angle: float,
    current_orb: float,
    exact_epsilon_deg: float,
) -> AspectPhase:
    """Whether the transit is closing on exactness or moving away from it.

    Only the transiting body moves: the natal point is fixed by definition, so
    unlike the natal case there is no relative motion to work out, just the
    transit's own.
    """
    if current_orb <= exact_epsilon_deg:
        return AspectPhase.EXACT
    if transit_body.speed_longitude is None:
        return AspectPhase.INDETERMINATE

    future_longitude = normalize_longitude(
        transit_body.longitude + transit_body.speed_longitude * PHASE_TIMESTEP_DAYS
    )
    future_orb = abs(
        shortest_angular_distance(future_longitude, natal_longitude) - exact_angle
    )
    if future_orb + exact_epsilon_deg < current_orb:
        return AspectPhase.APPLYING
    if future_orb > current_orb + exact_epsilon_deg:
        return AspectPhase.SEPARATING
    return AspectPhase.INDETERMINATE


def _shift(body: BodyPosition, offset: float) -> BodyPosition:
    """Rotate one transit position into the chart's zodiac."""
    zodiac = longitude_to_tropical(normalize_longitude(body.longitude - offset))
    return BodyPosition(
        body_id=body.body_id,
        longitude=zodiac.longitude,
        latitude=body.latitude,
        distance=body.distance,
        speed_longitude=body.speed_longitude,
        retrograde=body.retrograde,
        sign=zodiac.sign,
        degree_in_sign=zodiac.degree_in_sign,
        house=body.house,
    )


def rank_score(
    aspect: TransitAspect,
    maximum_orb: float,
    profile: TransitProfile,
) -> float:
    """Relevance score for one transit contact.

    Four published factors multiplied: what the aspect is, how slow the
    transiting body is, how central the natal target is, and how exact the
    contact is, with a small multiplier for direction of travel.
    """
    ranking = profile.ranking
    aspect_weight = ranking.aspect_weights.get(aspect.aspect_type, 0.0)
    body_weight = ranking.transiting_body_weights.get(aspect.transit_body, 0.0)
    target_weight = ranking.natal_target_weights.get(aspect.natal_body, 0.0)
    phase_multiplier = ranking.phase_multipliers.get(aspect.phase, 1.0)

    if maximum_orb <= 0.0:
        exactness = 1.0
    else:
        tightness = max(0.0, min(1.0, 1.0 - aspect.orb / maximum_orb))
        exactness = ranking.exactness_floor + (1.0 - ranking.exactness_floor) * tightness

    return aspect_weight * body_weight * target_weight * exactness * phase_multiplier


def _ranked(
    aspects: list[TransitAspect],
    maximum_orbs: dict[str, float],
    profile: TransitProfile,
) -> tuple[TransitAspect, ...]:
    """Score, sort and stamp a rank onto every aspect.

    The tie-breaker is explicit and by name, so two runs of the same input
    always produce the same order. Nothing here depends on dictionary or set
    iteration order.
    """
    scored = [
        (
            rank_score(aspect, maximum_orbs.get(aspect.aspect_type, 0.0), profile),
            aspect,
        )
        for aspect in aspects
    ]
    scored.sort(
        key=lambda item: (
            -item[0],
            item[1].transit_body,
            item[1].natal_body,
            item[1].aspect_type,
        )
    )
    return tuple(
        TransitAspect(
            transit_body=aspect.transit_body,
            natal_body=aspect.natal_body,
            natal_target_kind=aspect.natal_target_kind,
            aspect_type=aspect.aspect_type,
            exact_angle=aspect.exact_angle,
            actual_angle=aspect.actual_angle,
            orb=aspect.orb,
            phase=aspect.phase,
            score=score,
            rank=position,
        )
        for position, (score, aspect) in enumerate(scored, start=1)
    )


def _natal_targets(
    natal_chart: NatalChart,
    profile: TransitProfile,
) -> list[tuple[str, str, float]]:
    """Natal points a transit may aspect, as (id, kind, longitude).

    Angles are included only when the chart has them, which is only when the
    birth time is known. Nothing is substituted when they are absent.
    """
    targets: list[tuple[str, str, float]] = []
    for body_id in profile.natal_body_targets:
        body = natal_chart.bodies.get(body_id)
        if body is not None:
            targets.append((body_id, NATAL_TARGET_BODY, body.longitude))
    for angle_id in profile.natal_angle_targets:
        angle = natal_chart.angles.get(angle_id)
        if angle is not None:
            targets.append((angle_id, NATAL_TARGET_ANGLE, angle.longitude))
    return targets


def calculate_transits(
    natal_chart: NatalChart,
    target_instant: datetime,
    provider: EphemerisProvider,
    profile: CalculationProfile,
    transit_profile: TransitProfile = TRANSIT_PROFILE_V1,
    top_count: int | None = None,
    include_natal_chart: bool = False,
    zodiac_offset: float = 0.0,
) -> TransitChart:
    """Positions at `target_instant`, aspected and housed against the natal chart.

    `zodiac_offset` moves the transit positions into the natal chart's zodiac.
    The provider always answers tropically, so without it a sidereal natal chart
    would be aspected against tropical transits and every contact would be out
    by the whole ayanamsa.
    """
    if target_instant.tzinfo is None:
        raise ValueError("target_instant must be timezone-aware.")
    instant = target_instant.astimezone(timezone.utc)
    aspect_profile = transit_profile.aspect_profile

    transit_bodies: dict[str, BodyPosition] = {}
    for body_id in transit_profile.transiting_bodies:
        if not provider.supports_body(body_id):
            continue
        position = normalize_body_position(
            body_id, provider.position(body_id, instant)
        )
        transit_bodies[body_id] = (
            position if zodiac_offset == 0.0 else _shift(position, zodiac_offset)
        )

    targets = _natal_targets(natal_chart, transit_profile)
    aspects: list[TransitAspect] = []
    for transit_id, transit_body in transit_bodies.items():
        for target_id, target_kind, target_longitude in targets:
            separation = shortest_angular_distance(
                transit_body.longitude, target_longitude
            )
            matched = match_aspect_rule(separation, aspect_profile)
            if matched is None:
                continue
            rule, orb = matched
            aspects.append(
                TransitAspect(
                    transit_body=transit_id,
                    natal_body=target_id,
                    natal_target_kind=target_kind,
                    aspect_type=rule.aspect_type,
                    exact_angle=rule.exact_angle,
                    actual_angle=separation,
                    orb=orb,
                    phase=transit_phase(
                        transit_body,
                        target_longitude,
                        rule.exact_angle,
                        orb,
                        aspect_profile.exact_epsilon_deg,
                    ).value,
                )
            )

    maximum_orbs = {rule.aspect_type: rule.orb for rule in aspect_profile.rules}
    ranked = _ranked(aspects, maximum_orbs, transit_profile)
    top = ranked[: (transit_profile.ranking.default_top_count if top_count is None else top_count)]

    warnings: list[WarningMessage] = []
    placements: list[TransitHousePlacement] = []
    if natal_chart.houses:
        placements = [
            TransitHousePlacement(
                transit_body=transit_id,
                natal_house=assign_house(transit_body.longitude, natal_chart.houses),
                longitude=transit_body.longitude,
            )
            for transit_id, transit_body in transit_bodies.items()
        ]
    else:
        warnings.append(
            WarningMessage(
                code="TRANSIT_HOUSE_PLACEMENT_UNAVAILABLE",
                severity="warning",
                message=(
                    "Transit house placements and natal angle targets were omitted "
                    "because the natal chart has no houses or angles, which is the "
                    "case when its birth time is unknown. Planet-to-planet transits "
                    "are unaffected and no substitute reference was used."
                ),
                fields_affected=("transitHousePlacements", "transitToNatalAspects"),
            )
        )

    return TransitChart(
        schema_version=TRANSIT_SCHEMA_VERSION,
        meta={
            "engine": ENGINE_NAME,
            "engineVersion": ENGINE_VERSION,
            "ephemerisProvider": provider.id,
            "ephemerisDataVersion": provider.data_version,
            "calculationProfile": profile.id,
            "transitAspectProfile": aspect_profile.id,
            "transitAspectProfileVersion": aspect_profile.version,
            "rankingProfile": transit_profile.ranking.id,
            "rankingProfileVersion": transit_profile.ranking.version,
            "rankingProfileDetail": transit_profile.ranking.to_dict(),
            "zodiac": profile.zodiac,
            "ayanamsa": profile.ayanamsa,
            "zodiacOffsetDegrees": zodiac_offset,
            "natalHouseSystem": natal_chart.meta.house_system,
            "phaseBasis": "transit_motion_against_fixed_natal_point",
            "natalAngleTargetsIncluded": any(
                kind == NATAL_TARGET_ANGLE for _id, kind, _lon in targets
            ),
        },
        target_instant=isoformat_z(instant),
        transit_bodies=transit_bodies,
        transit_to_natal_aspects=ranked,
        top_aspects=top,
        transit_house_placements=tuple(placements),
        natal_chart=natal_chart if include_natal_chart else None,
        warnings=tuple(warnings),
    )
