"""Named configurations between two charts.

Every pattern here cites the contacts it is built from and adds nothing to the
score. Those contacts are already scored once as themselves; scoring the pattern
as well would count the same geometry a second time for having been noticed --
the double-count this codebase has now removed three times in other guises.

One family cites nothing, and correctly
--------------------------------------
A stellium is defined by bodies sharing a **sign**, not by an aspect between
them. Four planets can sit inside one sign spanning twenty degrees with no
conjunction between any A body and any B body inside the synastry orb, so there
is no contact to cite. The pattern is real and its evidence is the sign
membership, which travels in `members` and `detail.sign`.

Every other family is built from contacts and cites them. A test pins that:
only a cross stellium may carry an empty evidence list.

Cross configurations reuse the natal detector
---------------------------------------------
A grand trine is a grand trine whether its three legs belong to one person or
two. Rather than reimplement the geometry, both charts' bodies are merged into
one dictionary with each id prefixed by its owner, and the validated natal
detector is run over that with a profile whose participating bodies are the
prefixed names.

The result is then filtered to figures that actually span both people. A figure
lying entirely inside one chart is that person's natal pattern, is already
reported on their chart, and repeating it here as a relationship fact would be
saying something about the pair that is only true of one of them.
"""

from __future__ import annotations

import dataclasses

from gbc_astro.derived.patterns import find_patterns
from gbc_astro.models.chart import NatalChart
from gbc_astro.models.position import BodyPosition
from gbc_astro.models.relationship import RelationshipPattern, SynastryChart
from gbc_astro.profiles.pattern import PatternProfile
from gbc_astro.profiles.relationship_patterns import RelationshipPatternProfile

CHART_PREFIXES = ("A", "B")


def _merged_bodies(
    chart_a: NatalChart, chart_b: NatalChart, bodies: tuple[str, ...]
) -> dict[str, BodyPosition]:
    merged: dict[str, BodyPosition] = {}
    for prefix, chart in zip(CHART_PREFIXES, (chart_a, chart_b), strict=True):
        for body_id in bodies:
            body = chart.bodies.get(body_id)
            if body is not None:
                merged[f"{prefix}.{body_id}"] = body
    return merged


def _legs_across_charts(
    members: tuple[str, ...], contacts: dict[tuple[str, str], str]
) -> tuple[str, ...]:
    """The cross aspects that form this figure's legs between the two charts.

    A figure spanning two people has legs of two kinds. Those between A and B
    are cross aspects and already have evidence ids, so the pattern cites them.
    Those inside one chart are that person's own natal aspects and belong to
    their chart, not to the pair -- they are not cited here, which is why a
    configuration's evidence list is shorter than its leg count.
    """
    found: list[str] = []
    for first in members:
        for second in members:
            owner_a, body_a = first.split(".", 1)
            owner_b, body_b = second.split(".", 1)
            if owner_a != "A" or owner_b != "B":
                continue
            evidence_id = contacts.get((body_a, body_b))
            if evidence_id is not None:
                found.append(evidence_id)
    return tuple(sorted(set(found)))


def cross_configurations(
    chart_a: NatalChart,
    chart_b: NatalChart,
    bodies: tuple[str, ...],
    natal_pattern_profile: PatternProfile,
    profile: RelationshipPatternProfile,
    contacts: dict[tuple[str, str], str],
) -> list[RelationshipPattern]:
    """Grand trines, T-squares and the rest, formed across the two charts."""
    if not profile.include_cross_configurations:
        return []

    merged = _merged_bodies(chart_a, chart_b, bodies)
    prefixed_profile = dataclasses.replace(
        natal_pattern_profile,
        id=f"{natal_pattern_profile.id}:cross",
        participating_bodies=tuple(merged),
        leg_orbs={
            aspect: orb * profile.cross_leg_orb_scale
            for aspect, orb in natal_pattern_profile.leg_orbs.items()
        },
        stellium_minimum_bodies=profile.cross_stellium_minimum_bodies,
    )

    found: list[RelationshipPattern] = []
    for pattern in find_patterns(merged, prefixed_profile):
        if pattern.pattern_type in profile.excluded_cross_configurations:
            continue
        owners = [member.split(".", 1)[0] for member in pattern.bodies]
        minimum = profile.cross_configuration_minimum_per_chart
        if any(owners.count(prefix) < minimum for prefix in CHART_PREFIXES):
            continue
        found.append(
            RelationshipPattern(
                pattern_type=f"cross_{pattern.pattern_type}",
                members=tuple(pattern.bodies),
                evidence_ids=_legs_across_charts(pattern.bodies, contacts),
                detail={
                    "maxLegOrb": pattern.max_leg_orb,
                    "natalPatternType": pattern.pattern_type,
                    **pattern.detail,
                },
            )
        )
    return found


def _contact_bodies(synastry: SynastryChart) -> list[tuple[str, str, str]]:
    """Every cross aspect as (A body, B body, evidence id)."""
    return [
        (aspect.body_a, aspect.body_b, aspect.id)
        for aspect in synastry.cross_aspects
    ]


def body_emphasis(
    synastry: SynastryChart, profile: RelationshipPatternProfile
) -> list[RelationshipPattern]:
    """A body that keeps turning up in the contacts between these two."""
    evidence: dict[str, list[str]] = {}
    for body_a, body_b, evidence_id in _contact_bodies(synastry):
        for body in {body_a, body_b}:
            if body in profile.emphasis_bodies:
                evidence.setdefault(body, []).append(evidence_id)

    return [
        RelationshipPattern(
            pattern_type="body_emphasis",
            members=(body,),
            evidence_ids=tuple(sorted(set(ids))),
            detail={"contactCount": len(set(ids))},
        )
        for body, ids in sorted(evidence.items())
        if len(set(ids)) >= profile.emphasis_minimum_contacts
    ]


def pair_clusters(
    synastry: SynastryChart, profile: RelationshipPatternProfile
) -> list[RelationshipPattern]:
    """Repeated contact between two named groups, counted both ways round."""
    patterns: list[RelationshipPattern] = []
    for cluster in profile.clusters:
        evidence = [
            evidence_id
            for body_a, body_b, evidence_id in _contact_bodies(synastry)
            if (body_a in cluster.left and body_b in cluster.right)
            or (body_a in cluster.right and body_b in cluster.left)
        ]
        unique = sorted(set(evidence))
        if len(unique) >= cluster.minimum_contacts:
            patterns.append(
                RelationshipPattern(
                    pattern_type="pair_cluster",
                    members=(cluster.id,),
                    evidence_ids=tuple(unique),
                    detail={"contactCount": len(unique)},
                )
            )
    return patterns


def mutual_activations(synastry: SynastryChart) -> list[RelationshipPattern]:
    """The same two bodies aspecting each other both ways round.

    A's Venus on B's Mars *and* B's Venus on A's Mars is a reciprocal structure,
    not two unrelated contacts, so it is named rather than left to be spotted in
    a list.
    """
    by_pair: dict[tuple[str, str], list[str]] = {}
    for body_a, body_b, evidence_id in _contact_bodies(synastry):
        by_pair.setdefault((body_a, body_b), []).append(evidence_id)

    patterns: list[RelationshipPattern] = []
    for (body_a, body_b), forward in sorted(by_pair.items()):
        if body_a == body_b:
            # Same body both sides is one contact, not a reciprocal pair.
            continue
        backward = by_pair.get((body_b, body_a))
        if backward is None or body_a > body_b:
            continue
        patterns.append(
            RelationshipPattern(
                pattern_type="mutual_activation",
                members=(body_a, body_b),
                evidence_ids=tuple(sorted(set(forward) | set(backward))),
                detail={"contactCount": len(set(forward) | set(backward))},
            )
        )
    return patterns


def angular_activation(
    synastry: SynastryChart, profile: RelationshipPatternProfile
) -> list[RelationshipPattern]:
    """Planets repeatedly landing on the other person's horizon and meridian."""
    evidence = sorted({contact.id for contact in synastry.angle_interactions})
    if len(evidence) < profile.angular_minimum_contacts:
        return []
    return [
        RelationshipPattern(
            pattern_type="angular_activation",
            members=("angles",),
            evidence_ids=tuple(evidence),
            detail={"contactCount": len(evidence)},
        )
    ]


def find_relationship_patterns(
    synastry: SynastryChart,
    chart_a: NatalChart,
    chart_b: NatalChart,
    bodies: tuple[str, ...],
    natal_pattern_profile: PatternProfile,
    profile: RelationshipPatternProfile,
) -> tuple[RelationshipPattern, ...]:
    contacts = {
        (aspect.body_a, aspect.body_b): aspect.id for aspect in synastry.cross_aspects
    }
    found = [
        *cross_configurations(
            chart_a, chart_b, bodies, natal_pattern_profile, profile, contacts
        ),
        *body_emphasis(synastry, profile),
        *pair_clusters(synastry, profile),
        *mutual_activations(synastry),
        *angular_activation(synastry, profile),
    ]
    # Sorted by id so the order never depends on iteration or chance.
    return tuple(sorted(found, key=lambda pattern: pattern.id))
