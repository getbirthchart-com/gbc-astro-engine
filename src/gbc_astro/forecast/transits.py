"""Transit snapshot: where the sky is now against a fixed natal chart.

The contrast with synastry matters. Two natal charts are two frozen instants and
share no timeline, which is why cross-aspect phase there is `indeterminate`. A
transit chart is not like that: the transiting bodies are genuinely moving while
the natal points stay put, so applying and separating describe something that is
actually happening. The phase here is physics, not convention.
"""

from __future__ import annotations

from datetime import datetime, timezone

from gbc_astro.aspects.engine import match_aspect_rule
from gbc_astro.astronomy.circular import normalize_longitude, shortest_angular_distance
from gbc_astro.astronomy.time import isoformat_z
from gbc_astro.constants import BODY_IDS, ENGINE_NAME, ENGINE_VERSION, TRANSIT_SCHEMA_VERSION
from gbc_astro.houses.base import assign_house
from gbc_astro.models.chart import NatalChart, WarningMessage
from gbc_astro.models.enums import AspectPhase
from gbc_astro.models.forecast import TransitAspect, TransitChart, TransitHousePlacement
from gbc_astro.models.position import BodyPosition
from gbc_astro.profiles.model import CalculationProfile
from gbc_astro.providers.base import EphemerisProvider
from gbc_astro.providers.normalization import normalize_body_position

# The step used to decide whether a transit is closing on an aspect or leaving
# it. Small enough that the answer is the instantaneous one, large enough to
# stay well clear of floating-point noise in the separation.
PHASE_TIMESTEP_DAYS = 1.0e-3


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


def calculate_transits(
    natal_chart: NatalChart,
    target_instant: datetime,
    provider: EphemerisProvider,
    profile: CalculationProfile,
    include_natal_chart: bool = False,
) -> TransitChart:
    """Positions at `target_instant`, aspected and housed against the natal chart."""
    if target_instant.tzinfo is None:
        raise ValueError("target_instant must be timezone-aware.")
    instant = target_instant.astimezone(timezone.utc)

    transit_bodies: dict[str, BodyPosition] = {}
    for body_id in BODY_IDS:
        if not provider.supports_body(body_id):
            continue
        transit_bodies[body_id] = normalize_body_position(
            body_id, provider.position(body_id, instant)
        )

    aspects: list[TransitAspect] = []
    for transit_id, transit_body in transit_bodies.items():
        for natal_id, natal_body in natal_chart.bodies.items():
            separation = shortest_angular_distance(
                transit_body.longitude, natal_body.longitude
            )
            matched = match_aspect_rule(separation, profile.aspect_profile)
            if matched is None:
                continue
            rule, orb = matched
            aspects.append(
                TransitAspect(
                    transit_body=transit_id,
                    natal_body=natal_id,
                    aspect_type=rule.aspect_type,
                    exact_angle=rule.exact_angle,
                    actual_angle=separation,
                    orb=orb,
                    phase=transit_phase(
                        transit_body,
                        natal_body.longitude,
                        rule.exact_angle,
                        orb,
                        profile.aspect_profile.exact_epsilon_deg,
                    ).value,
                )
            )

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
                    "Transit house placements were omitted because the natal chart has "
                    "no houses, which is the case when its birth time is unknown. "
                    "Transit positions and aspects are unaffected."
                ),
                fields_affected=("transitHousePlacements",),
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
            "aspectProfile": profile.aspect_profile.id,
            "zodiac": profile.zodiac,
            "natalHouseSystem": natal_chart.meta.house_system,
            "phaseBasis": "transit_motion_against_fixed_natal_point",
        },
        target_instant=isoformat_z(instant),
        transit_bodies=transit_bodies,
        transit_to_natal_aspects=tuple(aspects),
        transit_house_placements=tuple(placements),
        natal_chart=natal_chart if include_natal_chart else None,
        warnings=tuple(warnings),
    )
