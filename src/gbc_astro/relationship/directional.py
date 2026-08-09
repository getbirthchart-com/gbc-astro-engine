"""Ruler interactions and directional themes: views, never new evidence.

Both structures here are ways of *reading* facts the synastry result already
contains. Neither produces geometry, and neither is scored.

Why that matters more than it sounds
------------------------------------
"A's seventh-house ruler conjunct B's Venus" is not a new contact. If Mercury
rules A's seventh, it is the cross aspect `a.mercury.conjunction.b.venus`,
which is already in the result and already scored. Emitting it again as a
ruler interaction with its own evidence id would put the same geometry into the
scoring twice -- exactly the double-count the lunar node fix removed in S1, in a
new place.

So every ruler interaction cites the id of the underlying fact rather than
minting one, and the scoring layer never sees these at all. A caller that wants
to show "your seventh-house ruler meets their Venus" gets the framing; the
number behind it is still the one contact, counted once.

What is genuinely directional, and what is not
----------------------------------------------
House overlays and angle contacts are directional facts. A's Sun in B's seventh
house is a statement about A acting on B's field, and the reverse is a different
statement about different territory.

A cross aspect is **not** directional. `a.sun.trine.b.moon` and
`b.moon.trine.a.sun` are one geometric relation described twice; the A and B in
the id say whose planet is whose, not which way influence runs. Grouping cross
aspects into directional themes would claim a direction the geometry does not
have -- the same error the engine already refuses when it reports cross-aspect
phase as `indeterminate` rather than borrowing natal speeds.

Directional themes are therefore built from overlays and angle contacts only,
and the omission is deliberate rather than an oversight.
"""

from __future__ import annotations

from gbc_astro.models.chart import NatalChart
from gbc_astro.models.relationship import (
    CHART_A,
    CHART_B,
    DirectionalTheme,
    RulerInteraction,
    SynastryChart,
)
from gbc_astro.profiles.dimensions import DIMENSION_IDS, DimensionProfile

A_TO_B = "A_TO_B"
B_TO_A = "B_TO_A"


def _direction(source_chart: str) -> str:
    return A_TO_B if source_chart == CHART_A else B_TO_A


def ruler_interactions(
    synastry: SynastryChart,
    chart_a: NatalChart,
    chart_b: NatalChart,
) -> tuple[RulerInteraction, ...]:
    """Each chart's house rulers, and what they meet in the other chart.

    Two kinds, both citing the fact they reframe:

    * the ruler aspects one of the other chart's bodies -- an existing cross
      aspect
    * the ruler falls in one of the other chart's houses -- an existing overlay

    A chart with no birth time has no houses and therefore no house rulers, so
    it contributes nothing in that direction. Nothing is substituted.
    """
    interactions: list[RulerInteraction] = []

    for source, target, source_label, target_label in (
        (chart_a, chart_b, CHART_A, CHART_B),
        (chart_b, chart_a, CHART_B, CHART_A),
    ):
        rulers = {
            ruler.house: ruler.ruler.body_id for ruler in source.derived.house_rulers
        }
        if not rulers:
            continue

        by_body: dict[str, list[int]] = {}
        for house, body_id in rulers.items():
            by_body.setdefault(body_id, []).append(house)

        for aspect in synastry.cross_aspects:
            ruler_body = aspect.body_a if source_label == CHART_A else aspect.body_b
            other_body = aspect.body_b if source_label == CHART_A else aspect.body_a
            for house in by_body.get(ruler_body, ()):
                interactions.append(
                    RulerInteraction(
                        direction=_direction(source_label),
                        house=house,
                        ruler=ruler_body,
                        kind="aspect",
                        target=other_body,
                        aspect_type=aspect.aspect_type,
                        orb=aspect.orb,
                        evidence_id=aspect.id,
                    )
                )

        overlays = (
            synastry.a_bodies_in_b_houses
            if source_label == CHART_A
            else synastry.b_bodies_in_a_houses
        )
        for overlay in overlays:
            for house in by_body.get(overlay.body, ()):
                interactions.append(
                    RulerInteraction(
                        direction=_direction(source_label),
                        house=house,
                        ruler=overlay.body,
                        kind="overlay",
                        target=f"house_{overlay.house}",
                        aspect_type=None,
                        orb=None,
                        evidence_id=overlay.id,
                    )
                )
        # `target_label` is unused deliberately: the direction already names the
        # receiving chart, and repeating it in every row would be noise.
        del target, target_label

    return tuple(sorted(interactions, key=lambda item: item.id))


def directional_themes(
    synastry: SynastryChart,
    profile: DimensionProfile,
) -> tuple[DirectionalTheme, ...]:
    """Group the directional facts by which way they run and what they touch.

    Only overlays and angle contacts take part. A cross aspect is a mutual
    relation and has no direction of influence to group by; including it would
    assert one.

    Every dimension is emitted for both directions even when empty, for the same
    reason dimension scores are: an absent theme and a neutral one are different
    statements, and a caller has to be able to tell them apart.
    """
    buckets: dict[tuple[str, str], list[str]] = {
        (direction, dimension): []
        for direction in (A_TO_B, B_TO_A)
        for dimension in DIMENSION_IDS
    }

    for overlay in synastry.a_bodies_in_b_houses + synastry.b_bodies_in_a_houses:
        direction = _direction(overlay.body_chart)
        for dimension in profile.weights_for(overlay.body):
            buckets[(direction, dimension)].append(overlay.id)

    for interaction in synastry.angle_interactions:
        direction = _direction(interaction.body_chart)
        # Both ends speak: the travelling body and the angle it lands on.
        dimensions = set(profile.weights_for(interaction.body)) | set(
            profile.weights_for(interaction.angle)
        )
        for dimension in dimensions:
            buckets[(direction, dimension)].append(interaction.id)

    return tuple(
        DirectionalTheme(
            direction=direction,
            theme=dimension,
            contact_count=len(evidence),
            evidence_ids=tuple(sorted(set(evidence))),
        )
        for (direction, dimension), evidence in buckets.items()
    )
