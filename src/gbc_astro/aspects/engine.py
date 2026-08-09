"""Profile-driven aspect classification."""

from __future__ import annotations

from itertools import combinations

from gbc_astro.astronomy.circular import normalize_longitude, shortest_angular_distance
from gbc_astro.models.aspect import Aspect
from gbc_astro.models.enums import AspectPhase
from gbc_astro.models.position import BodyPosition
from gbc_astro.profiles.model import AspectProfile, AspectRule


def match_aspect_rule(
    separation: float,
    profile: AspectProfile,
) -> tuple[AspectRule, float] | None:
    """Return the tightest profile rule that `separation` satisfies, with its orb.

    Shared by natal aspects and the relationship module so both classify against
    the same profile with identical tie-breaking.
    """
    best_rule: AspectRule | None = None
    best_orb: float | None = None
    for rule in profile.rules:
        orb = abs(separation - rule.exact_angle)
        if orb <= rule.orb and (best_orb is None or orb < best_orb):
            best_rule = rule
            best_orb = orb
    if best_rule is None or best_orb is None:
        return None
    return best_rule, best_orb


def classify_aspect(
    body_a: BodyPosition,
    body_b: BodyPosition,
    profile: AspectProfile,
) -> Aspect | None:
    actual_angle = shortest_angular_distance(body_a.longitude, body_b.longitude)
    matched = match_aspect_rule(actual_angle, profile)
    if matched is None:
        return None
    best_rule, best_orb = matched

    phase = aspect_phase(
        body_a,
        body_b,
        best_rule.exact_angle,
        best_orb,
        profile.exact_epsilon_deg,
    )
    return Aspect(
        body_a=body_a.body_id,
        body_b=body_b.body_id,
        aspect_type=best_rule.aspect_type,
        exact_angle=best_rule.exact_angle,
        actual_angle=actual_angle,
        orb=best_orb,
        phase=phase.value,
    )


def calculate_aspects(
    bodies: dict[str, BodyPosition],
    profile: AspectProfile,
    eligible_bodies: tuple[str, ...] = (),
) -> tuple[Aspect, ...]:
    """Every aspect among the eligible bodies.

    `eligible_bodies` is narrower than what the chart reports. A chart carries
    both the true and the mean lunar node so a caller can have either, but they
    are one point computed two ways: aspecting both doubles every node contact
    and yields a permanent "node conjunct node" that is true of every chart and
    says nothing. Empty means no filtering, which is what a direct caller
    testing the aspect engine itself wants.
    """
    selected = (
        bodies
        if not eligible_bodies
        else {
            body_id: body
            for body_id, body in bodies.items()
            if body_id in eligible_bodies
        }
    )
    aspects = []
    for body_a, body_b in combinations(selected.values(), 2):
        aspect = classify_aspect(body_a, body_b, profile)
        if aspect is not None:
            aspects.append(aspect)
    return tuple(aspects)


def aspect_phase(
    body_a: BodyPosition,
    body_b: BodyPosition,
    exact_angle: float,
    current_orb: float,
    exact_epsilon_deg: float,
) -> AspectPhase:
    if current_orb <= exact_epsilon_deg:
        return AspectPhase.EXACT
    if body_a.speed_longitude is None or body_b.speed_longitude is None:
        return AspectPhase.INDETERMINATE

    # Compare the absolute orb after a short deterministic timestep. This uses
    # relative angular motion and avoids relying on naive longitude ordering.
    timestep_days = 1e-3
    future_a = normalize_longitude(body_a.longitude + body_a.speed_longitude * timestep_days)
    future_b = normalize_longitude(body_b.longitude + body_b.speed_longitude * timestep_days)
    future_separation = shortest_angular_distance(future_a, future_b)
    future_orb = abs(future_separation - exact_angle)
    if future_orb + exact_epsilon_deg < current_orb:
        return AspectPhase.APPLYING
    if future_orb > current_orb + exact_epsilon_deg:
        return AspectPhase.SEPARATING
    return AspectPhase.INDETERMINATE
