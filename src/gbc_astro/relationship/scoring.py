"""Relationship scoring from a synastry chart.

Every number this produces is traceable: each contact contributes one line
recording the aspect, the two bodies, the orb, the three factors that were
multiplied, and the result. The totals are just sums of those lines, so a caller
can always show its work instead of presenting a figure that arrived from
nowhere.

Reported as three totals rather than one:

* `supportive` -- everything that scored positive
* `challenging` -- everything that scored negative
* `activity` -- their combined magnitude

Activity is the headline number. A couple with many hard contacts can be
strongly bound while a couple with a few mild easy ones can be forgettable, and
a single net figure erases that distinction. `balance` is still reported, but it
is the less informative of the two.

No percentage is produced. A percentage implies an absolute scale, and there is
no defensible answer to what a hundred percent would be.
"""

from __future__ import annotations

from gbc_astro.constants import ENGINE_NAME, ENGINE_VERSION, SCORE_SCHEMA_VERSION
from gbc_astro.models.relationship import (
    AngleInteraction,
    RelationshipScore,
    ScoreContribution,
    SynastryChart,
)
from gbc_astro.profiles.model import RelationshipProfile
from gbc_astro.profiles.scoring import ScoringProfile


def orb_factor(orb: float, maximum_orb: float, floor: float) -> float:
    """Full weight at an exact contact, falling linearly to `floor` at the orb limit."""
    if maximum_orb <= 0.0:
        return 1.0
    tightness = max(0.0, min(1.0, 1.0 - orb / maximum_orb))
    return floor + (1.0 - floor) * tightness


def _one_contact_per_axis(
    synastry: SynastryChart,
    scoring_profile: ScoringProfile,
) -> list[AngleInteraction]:
    """Collapse each body-to-axis contact to a single scored line.

    The Descendant is exactly opposite the Ascendant and the IC exactly opposite
    the Midheaven, so every contact to one end is mirrored at the other: a square
    to the Ascendant is a square to the Descendant, and a conjunction to the
    Descendant is an opposition to the Ascendant. Scoring both would count one
    geometric fact twice, and in the conjunction case would score it as a
    positive and a negative simultaneously.

    The surviving contact is the conjunction when either end has one -- being
    conjunct the Descendant is its own thing, not a weak opposition -- and
    otherwise the axis's declared primary end.
    """
    grouped: dict[tuple[str, str, str, str], list[AngleInteraction]] = {}
    for interaction in synastry.angle_interactions:
        axis = scoring_profile.angle_axis_of.get(interaction.angle, interaction.angle)
        key = (interaction.body_chart, interaction.body, interaction.angle_chart, axis)
        grouped.setdefault(key, []).append(interaction)

    chosen: list[AngleInteraction] = []
    for (_chart, _body, _angle_chart, axis), candidates in grouped.items():
        if len(candidates) == 1:
            chosen.append(candidates[0])
            continue
        conjunctions = [item for item in candidates if item.aspect_type == "conjunction"]
        if conjunctions:
            chosen.append(conjunctions[0])
            continue
        primary = scoring_profile.angle_axis_primary_end.get(axis)
        preferred = [item for item in candidates if item.angle == primary]
        chosen.append(preferred[0] if preferred else candidates[0])
    return chosen


def calculate_relationship_score(
    synastry: SynastryChart,
    relationship_profile: RelationshipProfile,
    scoring_profile: ScoringProfile,
) -> RelationshipScore:
    maximum_orbs = {
        rule.aspect_type: rule.orb for rule in relationship_profile.aspect_profile.rules
    }
    contributions: list[ScoreContribution] = []

    for aspect in synastry.cross_aspects:
        aspect_weight = scoring_profile.aspect_weights.get(aspect.aspect_type)
        if aspect_weight is None:
            continue
        weight_a = scoring_profile.body_weights.get(aspect.body_a)
        weight_b = scoring_profile.body_weights.get(aspect.body_b)
        if weight_a is None or weight_b is None:
            continue

        pair_weight = ((weight_a + weight_b) / 2.0) * scoring_profile.pair_bonus(
            aspect.body_a, aspect.body_b
        )
        tightness = orb_factor(
            aspect.orb,
            maximum_orbs.get(aspect.aspect_type, 0.0),
            scoring_profile.orb_floor,
        )
        contributions.append(
            ScoreContribution(
                kind="cross_aspect",
                subject_a=f"A.{aspect.body_a}",
                subject_b=f"B.{aspect.body_b}",
                aspect_type=aspect.aspect_type,
                orb=aspect.orb,
                aspect_weight=aspect_weight,
                pair_weight=pair_weight,
                orb_factor=tightness,
                value=aspect_weight * pair_weight * tightness,
            )
        )

    for interaction in _one_contact_per_axis(synastry, scoring_profile):
        aspect_weight = scoring_profile.aspect_weights.get(interaction.aspect_type)
        body_weight = scoring_profile.body_weights.get(interaction.body)
        angle_weight = scoring_profile.angle_weights.get(interaction.angle)
        if aspect_weight is None or body_weight is None or angle_weight is None:
            continue

        pair_weight = (body_weight + angle_weight) / 2.0
        tightness = orb_factor(
            interaction.orb,
            maximum_orbs.get(interaction.aspect_type, 0.0),
            scoring_profile.orb_floor,
        )
        contributions.append(
            ScoreContribution(
                kind="angle_interaction",
                subject_a=f"{interaction.body_chart}.{interaction.body}",
                subject_b=f"{interaction.angle_chart}.{interaction.angle}",
                aspect_type=interaction.aspect_type,
                orb=interaction.orb,
                aspect_weight=aspect_weight,
                pair_weight=pair_weight,
                orb_factor=tightness,
                value=aspect_weight * pair_weight * tightness,
            )
        )

    supportive = sum(item.value for item in contributions if item.value > 0.0)
    challenging = sum(item.value for item in contributions if item.value < 0.0)
    activity = supportive - challenging
    balance = supportive + challenging

    ordered = tuple(sorted(contributions, key=lambda item: -abs(item.value)))
    return RelationshipScore(
        schema_version=SCORE_SCHEMA_VERSION,
        engine=ENGINE_NAME,
        engine_version=ENGINE_VERSION,
        scoring_profile=scoring_profile.id,
        scoring_profile_version=scoring_profile.version,
        supportive=supportive,
        challenging=challenging,
        activity=activity,
        balance=balance,
        activity_band=scoring_profile.band_for(activity, scoring_profile.activity_bands),
        balance_band=scoring_profile.band_for(balance, scoring_profile.balance_bands),
        contribution_count=len(ordered),
        contributions=ordered,
        profile_detail=scoring_profile.to_dict(),
        notes=(
            "Activity is the headline figure: a strongly bound relationship can be "
            "full of hard contacts, and a forgettable one full of mild easy ones, "
            "which a single net figure would hide.",
            "No percentage is produced. A percentage implies an absolute scale, and "
            "there is no defensible answer to what one hundred percent would mean.",
            "The weights are GetBirthChart's editorial opinion, not a measurement. "
            "Unlike every other calculation in this engine, a score has no "
            "independent reference it can be validated against.",
            "House overlays are not scored in this version. Each additional factor "
            "adds another set of editorial weights, and overlays would need their "
            "own defensible table rather than an assumed one.",
        ),
    )
