"""Cross-chart contacts to the derived points.

Which points take part, and why only two
----------------------------------------
The chart publishes four derived points, and two of them carry no geometry of
their own:

    south_node - true_node = 180.000000
    antivertex - vertex    = 180.000000

Because they are exact reflections, every contact they could form is a contact
the other end already forms with the aspect reflected. Measured on a real pair,
the separation from B's Sun to A's south node and to A's north node sum to
exactly 180 degrees, every time. Letting both ends contact would report one
piece of geometry twice under two names -- the same double-count the lunar node
fix removed in S1 and the ruler interactions avoided in S5.

So the vertex and the Lot of Fortune form contacts; the antivertex and the south
node do not. This is the same collapse the scoring already applies to the
Ascendant/Descendant and Midheaven/IC axes.

Orb, and an honest empty section
--------------------------------
A computed point is not a body. It has no disc, no orb of influence in the
traditional sense, and a contact to it is a much weaker claim than a
planet-to-planet aspect at the same separation. Measured over thirty pairs,
counting both directions across twelve bodies:

    conjunction + opposition, orb 2.0    mean 1.2 contacts   12 of 30 pairs have none
    all five aspects,         orb 2.0    mean 4.1 contacts    1 of 30 pairs has none

Widening to all five aspects would fill the section for almost everyone. It was
not done. A trine to a calculated point at two degrees is a weak claim, and
padding a section so that it is never empty is how a product ends up asserting
things it does not mean. Forty percent of pairs having no notable point contact
is the honest answer, and the empty list says so.

Not scored, deliberately
------------------------
These contacts are reported and not fed into the compatibility score, the same
status house overlays have. Scoring them would require weights for the vertex
and the Lot relative to the planets, and that is another table of editorial
numbers with nothing to validate it against. The roadmap allows an explicit
no-scoring status and this takes it; `scored` is published as false rather than
left to be inferred.
"""

from __future__ import annotations

from gbc_astro.astronomy.circular import shortest_angular_distance
from gbc_astro.models.chart import NatalChart
from gbc_astro.models.relationship import CHART_A, CHART_B, PointContact

# The two points that carry independent geometry. The antivertex and the south
# node are their exact reflections and would duplicate every contact.
CONTACTING_POINTS: tuple[str, ...] = ("vertex", "part_of_fortune")

# Conjunction and opposition only. See the module docstring for the measurement
# behind not widening this.
POINT_ASPECTS: dict[str, float] = {"conjunction": 0.0, "opposition": 180.0}

POINT_ORB = 2.0


def calculate_point_contacts(
    chart_a: NatalChart,
    chart_b: NatalChart,
    bodies: tuple[str, ...],
) -> tuple[PointContact, ...]:
    """Each chart's derived points against the other chart's bodies.

    Directional: A's Lot of Fortune meeting B's Venus is a different statement
    from B's Lot meeting A's Venus, and both are reported.

    A chart with no birth time has no vertex and no Lot, so it contributes
    nothing in that direction and nothing is substituted.
    """
    contacts: list[PointContact] = []

    for source, target, source_label, target_label in (
        (chart_a, chart_b, CHART_A, CHART_B),
        (chart_b, chart_a, CHART_B, CHART_A),
    ):
        for point_id in CONTACTING_POINTS:
            point = source.points.get(point_id)
            if point is None:
                continue
            for body_id in bodies:
                body = target.bodies.get(body_id)
                if body is None:
                    continue
                separation = shortest_angular_distance(point.longitude, body.longitude)
                for aspect_type, exact_angle in POINT_ASPECTS.items():
                    orb = abs(separation - exact_angle)
                    if orb > POINT_ORB:
                        continue
                    contacts.append(
                        PointContact(
                            point=point_id,
                            point_chart=source_label,
                            body=body_id,
                            body_chart=target_label,
                            aspect_type=aspect_type,
                            exact_angle=exact_angle,
                            actual_angle=separation,
                            orb=orb,
                        )
                    )

    return tuple(sorted(contacts, key=lambda item: (item.id, item.orb)))
