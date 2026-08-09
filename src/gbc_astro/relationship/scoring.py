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
    DimensionScore,
    RelationshipScore,
    ScoreContribution,
    SynastryChart,
)
from gbc_astro.profiles.dimensions import (
    CONFLICT,
    DIMENSION_IDS,
    SYNASTRY_DIMENSION_PROFILE_V1,
    DimensionProfile,
)
from gbc_astro.profiles.model import RelationshipProfile
from gbc_astro.profiles.relationship_types import (
    GENERAL_V1,
    RelationshipTypeProfile,
)
from gbc_astro.profiles.scoring import ScoringProfile


def orb_factor(orb: float, maximum_orb: float, floor: float) -> float:
    """Full weight at an exact contact, falling linearly to `floor` at the orb limit."""
    if maximum_orb <= 0.0:
        return 1.0
    tightness = max(0.0, min(1.0, 1.0 - orb / maximum_orb))
    return floor + (1.0 - floor) * tightness


def _dimension_values(
    subject_a: str,
    subject_b: str,
    aspect_type: str,
    value: float,
    profile: DimensionProfile,
    relationship_type: RelationshipTypeProfile,
) -> dict[str, float]:
    """Split one contact's value across the dimensions its two ends speak to.

    Both ends contribute. A Moon-Mercury contact is heard by emotional life and
    by communication, and taking only one end would drop half of what the
    contact says. Weights are averaged rather than summed so that a contact
    between two bodies mapped to the same dimension does not outweigh itself.

    Hard aspects add to conflict on top of that, because friction is a property
    of the angle rather than of the bodies -- which is the one place the aspect
    is allowed to decide a dimension.
    """
    values: dict[str, float] = {}
    weights_a = profile.weights_for(subject_a)
    weights_b = profile.weights_for(subject_b)
    for dimension in DIMENSION_IDS:
        weight = (weights_a.get(dimension, 0.0) + weights_b.get(dimension, 0.0)) / 2.0
        if weight:
            values[dimension] = value * weight

    if aspect_type in profile.conflict_aspects:
        friction = abs(value) * profile.conflict_aspect_weight
        values[CONFLICT] = values.get(CONFLICT, 0.0) - friction

    # The relationship type reweights here, inside the contribution, rather than
    # afterwards on the dimension totals. Applied afterwards it would scale the
    # totals away from the contributions cited under them, and a dimension score
    # that is no longer the sum of its own evidence is exactly what the evidence
    # rule forbids.
    return {
        dimension: amount * relationship_type.weight_for(dimension)
        for dimension, amount in values.items()
    }


def _dimension_scores(
    contributions: list[ScoreContribution],
    relationship_type: RelationshipTypeProfile,
) -> tuple[DimensionScore, ...]:
    """Aggregate contributions per dimension, keeping the two signals apart.

    Every dimension is returned, including those no contact reached. An absent
    dimension reported as zero would be indistinguishable from a neutral one,
    and `contact_count` is what tells them apart.
    """
    scores: list[DimensionScore] = []
    for dimension in DIMENSION_IDS:
        supportive = 0.0
        challenging = 0.0
        evidence: list[str] = []
        for contribution in contributions:
            value = contribution.dimension_values.get(dimension)
            if value is None:
                continue
            evidence.append(contribution.evidence_id)
            if value > 0.0:
                supportive += value
            else:
                challenging += value
        scores.append(
            DimensionScore(
                dimension=dimension,
                supportive=supportive,
                challenging=challenging,
                activity=supportive - challenging,
                contact_count=len(evidence),
                profile_weight=relationship_type.weight_for(dimension),
                evidence_ids=tuple(sorted(set(evidence))),
            )
        )
    return tuple(scores)


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
    dimension_profile: DimensionProfile = SYNASTRY_DIMENSION_PROFILE_V1,
    relationship_type: RelationshipTypeProfile = GENERAL_V1,
) -> RelationshipScore:
    # The profile that PRODUCED these contacts, not the natal one. Orb tightness
    # is a fraction of the orb a contact was allowed, so dividing by a different
    # profile's limit scores a near-miss as though it were close: a sextile at
    # 2.86 degrees sits at 95% of the synastry limit and would read as 57% of the
    # natal one. Cross aspects and angle contacts both come from here.
    maximum_orbs = {
        rule.aspect_type: rule.orb
        for rule in relationship_profile.synastry_aspect_profile.rules
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
        value = aspect_weight * pair_weight * tightness
        contributions.append(
            ScoreContribution(
                kind="cross_aspect",
                evidence_id=aspect.id,
                subject_a=f"A.{aspect.body_a}",
                subject_b=f"B.{aspect.body_b}",
                aspect_type=aspect.aspect_type,
                orb=aspect.orb,
                aspect_weight=aspect_weight,
                pair_weight=pair_weight,
                orb_factor=tightness,
                value=value,
                dimension_values=_dimension_values(
                    aspect.body_a,
                    aspect.body_b,
                    aspect.aspect_type,
                    value,
                    dimension_profile,
                    relationship_type,
                ),
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
        value = aspect_weight * pair_weight * tightness
        contributions.append(
            ScoreContribution(
                kind="angle_interaction",
                evidence_id=interaction.id,
                subject_a=f"{interaction.body_chart}.{interaction.body}",
                subject_b=f"{interaction.angle_chart}.{interaction.angle}",
                aspect_type=interaction.aspect_type,
                orb=interaction.orb,
                aspect_weight=aspect_weight,
                pair_weight=pair_weight,
                orb_factor=tightness,
                value=value,
                dimension_values=_dimension_values(
                    interaction.body,
                    interaction.angle,
                    interaction.aspect_type,
                    value,
                    dimension_profile,
                    relationship_type,
                ),
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
        dimensions=_dimension_scores(contributions, relationship_type),
        dimension_profile=dimension_profile.id,
        dimension_profile_version=dimension_profile.version,
        relationship_type=relationship_type.id,
        relationship_type_version=relationship_type.version,
        profile_detail=scoring_profile.to_dict(),
        dimension_profile_detail=dimension_profile.to_dict(),
        relationship_type_detail=relationship_type.to_dict(),
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
