"""Versioned profile for named configurations between two charts.

A pattern is a discrete claim -- present or absent -- where a dimension score is
a magnitude. That difference is the reason both exist. "This pair has a Saturn
emphasis" and "the stability dimension scores 7.51" are different statements,
and a report needs the first as much as a chart needs the second.

To keep them from being the same thing twice, the patterns here are defined on
**counts of contacts and which bodies take part**, never on the dimension
scores. They are a different view of the same geometry, not a relabelling of the
same number.

Five families, all deterministic
--------------------------------
**Cross configurations.** A grand trine, T-square, grand cross, yod, kite or
stellium formed across the two charts. These reuse the natal pattern detector
unchanged, run over both charts' bodies with their owner prefixed onto each id,
and are then filtered to those that actually span both people -- a figure lying
entirely inside one chart is that person's natal pattern and is already reported
there.

**Body emphasis.** One body involved in at least `emphasis_minimum_contacts`
cross-chart contacts. This is where "Saturn emphasis" or "nodal emphasis"
becomes a fact rather than an impression.

**Pair clusters.** Repeated contact between two named groups -- Venus with Mars
for chemistry, Mercury with Mercury for communication, and so on. Counted across
both directions, since A's Venus on B's Mars and B's Venus on A's Mars are two
instances of the same cluster.

**Mutual activation.** A's body aspects B's body *and* the same pair aspects the
other way round. Reciprocity is a real structure and not the same as two
unrelated contacts, so it is named separately.

**Angular activation.** At least `angular_minimum_contacts` contacts to the
angles. A pair whose planets keep landing on each other's horizon and meridian
is doing something a planet-to-planet count does not capture.

Thresholds, and what a threshold means
--------------------------------------
Every threshold is here rather than in the code, because every one of them is a
judgement about when a repetition becomes a theme, and a caller comparing two
readings has to be able to see what changed. None of these is measured against
anything -- like the scoring weights, they are editorial, and the version is
what makes a result reproducible rather than what makes it right.

Not scored
----------
Patterns cite the contacts they are built from and add nothing to the
compatibility score. Every contact behind a pattern is already scored once as
itself; scoring the pattern too would count the same geometry a second time for
having been noticed.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PairCluster:
    """A named repetition between two groups of bodies."""

    id: str
    left: tuple[str, ...]
    right: tuple[str, ...]
    minimum_contacts: int

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "left": list(self.left),
            "right": list(self.right),
            "minimumContacts": self.minimum_contacts,
        }


@dataclass(frozen=True)
class RelationshipPatternProfile:
    id: str
    version: str
    rationale: str
    # A body counts as emphasised at this many cross-chart contacts.
    emphasis_minimum_contacts: int
    # Cross configurations are searched over both charts' bodies at once, so the
    # natal leg orbs are far too loose here -- see the class-level constants.
    cross_leg_orb_scale: float
    cross_stellium_minimum_bodies: int
    # Which bodies may be reported as emphasised. The luminaries reach the
    # threshold in almost every pair, so naming them adds nothing.
    emphasis_bodies: tuple[str, ...]
    angular_minimum_contacts: int
    # Figures the cross search does not produce, because their defining legs are
    # aspects the synastry profile does not recognise as contacts.
    excluded_cross_configurations: tuple[str, ...] = ()
    clusters: tuple[PairCluster, ...] = ()
    include_cross_configurations: bool = True
    # A figure must involve at least this many bodies from each chart to count
    # as spanning both. One is the right answer: a trine from two of A's planets
    # to one of B's is a genuine cross-chart figure.
    cross_configuration_minimum_per_chart: int = 1
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "version": self.version,
            "rationale": self.rationale,
                "emphasisMinimumContacts": self.emphasis_minimum_contacts,
            "crossLegOrbScale": self.cross_leg_orb_scale,
            "crossStelliumMinimumBodies": self.cross_stellium_minimum_bodies,
            "excludedCrossConfigurations": list(self.excluded_cross_configurations),
            "emphasisBodies": list(self.emphasis_bodies),
            "angularMinimumContacts": self.angular_minimum_contacts,
            "clusters": [cluster.to_dict() for cluster in self.clusters],
            "includeCrossConfigurations": self.include_cross_configurations,
            "crossConfigurationMinimumPerChart": (
                self.cross_configuration_minimum_per_chart
            ),
            "notes": list(self.notes),
        }


RELATIONSHIP_PATTERNS_V1 = RelationshipPatternProfile(
    id="relationship-patterns-v1",
    version="1.0.0",
    rationale=(
        "Patterns are discrete claims defined on contact counts and which "
        "bodies take part, deliberately not on the dimension scores, so that "
        "they are a second view of the geometry rather than the same number "
        "under another name. Thresholds are judgements about when a repetition "
        "becomes a theme and live here so a caller can see what changed "
        "between two readings."
    ),
    # Measured over twenty pairs: a body averages 6.3 cross-chart contacts, so a
    # threshold of four names almost every body (7.8 of 10) and says nothing
    # about this particular pair. Eight leaves 1.7 on average and none at all
    # for some pairs, which is what "emphasis" should mean.
    emphasis_minimum_contacts=8,
    # Merging two charts doubles the bodies and roughly octuples the number of
    # triples to test, so the same leg orbs produce far more figures than they
    # do natally: 13.8 per pair against the two or three a natal chart yields.
    # Halving the legs brings it to 5.8, which a reader can hold.
    cross_leg_orb_scale=0.5,
    # Four rather than the natal three, for the same reason: with twenty-four
    # bodies in play, three sharing a sign is unremarkable.
    cross_stellium_minimum_bodies=4,
    # A yod is defined by two quincunxes, and the synastry aspect profile does
    # not treat a quincunx as a cross-chart contact at all. A cross yod would
    # therefore be a figure whose defining legs the engine does not consider
    # contacts between these two people, and it could cite no evidence for
    # them. Excluded rather than published with an empty evidence list.
    excluded_cross_configurations=("yod",),
    emphasis_bodies=(
        "mercury",
        "venus",
        "mars",
        "jupiter",
        "saturn",
        "uranus",
        "neptune",
        "pluto",
        "true_node",
        "chiron",
    ),
    angular_minimum_contacts=4,
    clusters=(
        PairCluster(
            id="venus_mars_chemistry",
            left=("venus", "mars"),
            right=("venus", "mars"),
            minimum_contacts=2,
        ),
        PairCluster(
            id="mercury_communication",
            left=("mercury",),
            right=("mercury", "moon", "jupiter"),
            minimum_contacts=2,
        ),
        PairCluster(
            id="moon_emotional",
            left=("moon",),
            right=("moon", "venus", "sun", "neptune"),
            minimum_contacts=2,
        ),
        PairCluster(
            id="saturn_commitment",
            left=("saturn",),
            right=("sun", "moon", "venus", "mars", "saturn"),
            minimum_contacts=2,
        ),
        PairCluster(
            id="nodal_connection",
            left=("true_node",),
            right=("sun", "moon", "venus", "mars", "true_node"),
            minimum_contacts=2,
        ),
    ),
    notes=(
        "The Sun and the Moon are excluded from body emphasis: they reach any "
        "workable threshold in nearly every pair, so naming them says nothing "
        "about this particular pair.",
        "A configuration lying entirely within one chart is that person's natal "
        "pattern and is reported on their chart, not here.",
        "Patterns cite the contacts they are built from and are not scored. "
        "Each of those contacts is already scored once as itself.",
    ),
)
