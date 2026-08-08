"""Versioned relationship scoring profiles.

`03_CALCULATION_SPEC.md` allows a compatibility score only behind a separately
versioned scoring profile. This is that profile. Everything editorial lives
here, in named numbers, so a score can always be traced to the opinion that
produced it, and changing an opinion means changing a version rather than
quietly changing everybody's results.

What is not editorial
---------------------
The *structure* is the industry-wide consensus and is not in dispute: a contact
is weighted by which aspect it is, which two bodies it joins, and how tight the
orb is. Harmonious aspects count positively, hard aspects negatively, personal
planets outweigh outer planets, and tighter orbs count for more.

What is editorial
-----------------
The numbers. There is no standard and no published system that another
implementation could be checked against -- most services keep their formula
private, and two of them will disagree about the same couple. These weights are
structurally aligned with the one widely cited system that does publish its
reasoning, Cafe Astrology's synastry scoring, whose author is explicit that
"none of these weights are absolute" and offers them "as a general guideline
only".

Why three totals and no percentage
----------------------------------
A percentage implies an absolute scale that nobody has: there is no defensible
answer to what 100% would mean. This profile reports the positive total, the
negative total, and the *activity* -- their combined magnitude. Activity is the
number Cafe Astrology's author calls "the most telling value", and the reason is
sound: a couple with many hard contacts can be strongly bound, while a couple
with only mild easy contacts can be forgettable. A single net figure hides
exactly that difference.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScoringBand:
    """A named range for a total, declared by the profile rather than universal."""

    label: str
    minimum: float

    def to_dict(self) -> dict[str, float | str]:
        return {"label": self.label, "minimum": self.minimum}


@dataclass(frozen=True)
class ScoringProfile:
    id: str
    version: str
    rationale: str
    source_note: str

    # Signed weight per aspect type. Sign carries the polarity; magnitude
    # carries how much the contact is held to matter.
    aspect_weights: dict[str, float]

    # How much each body counts in a relationship context.
    body_weights: dict[str, float]

    # How much each angle counts when a body contacts it.
    angle_weights: dict[str, float]

    # Multipliers for specific unordered pairs held to matter more than their
    # individual weights suggest.
    pair_bonuses: dict[tuple[str, str], float]

    # An exact contact scores at full weight; one at the edge of orb scores at
    # `orb_floor`. Linear in between.
    orb_floor: float

    # The four angles are two axes: the Descendant is always exactly opposite the
    # Ascendant, and the IC the Midheaven. A body square the Ascendant is
    # therefore square the Descendant as well -- one geometric fact, not two --
    # and a body conjunct the Descendant is opposite the Ascendant, which would
    # otherwise be scored as a positive and a negative at once. Each axis is
    # scored exactly once. `angle_axis_policy` names how the end is chosen.
    angle_axis_of: dict[str, str] = field(default_factory=dict)
    angle_axis_primary_end: dict[str, str] = field(default_factory=dict)
    angle_axis_policy: str = "prefer_conjunction_then_primary_end"

    activity_bands: tuple[ScoringBand, ...] = field(default_factory=tuple)
    balance_bands: tuple[ScoringBand, ...] = field(default_factory=tuple)

    def pair_bonus(self, body_a: str, body_b: str) -> float:
        key = (body_a, body_b) if body_a <= body_b else (body_b, body_a)
        return self.pair_bonuses.get(key, 1.0)

    def band_for(self, value: float, bands: tuple[ScoringBand, ...]) -> str | None:
        matched: str | None = None
        for band in sorted(bands, key=lambda item: item.minimum):
            if value >= band.minimum:
                matched = band.label
        return matched

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "version": self.version,
            "rationale": self.rationale,
            "sourceNote": self.source_note,
            "aspectWeights": dict(self.aspect_weights),
            "bodyWeights": dict(self.body_weights),
            "angleWeights": dict(self.angle_weights),
            "pairBonuses": {f"{a}+{b}": value for (a, b), value in self.pair_bonuses.items()},
            "orbFloor": self.orb_floor,
            "angleAxisOf": dict(self.angle_axis_of),
            "angleAxisPrimaryEnd": dict(self.angle_axis_primary_end),
            "angleAxisPolicy": self.angle_axis_policy,
            "activityBands": [band.to_dict() for band in self.activity_bands],
            "balanceBands": [band.to_dict() for band in self.balance_bands],
        }


SYNASTRY_SCORING_V1 = ScoringProfile(
    id="synastry-scoring-v1",
    version="1.0.0",
    rationale=(
        "Weights are GetBirthChart's editorial opinion, not a measurement. They are "
        "structurally aligned with the standard three-factor model -- aspect type, "
        "which bodies are joined, and orb tightness -- and calibrated so that the "
        "contacts most consistently emphasised in relationship astrology (Sun-Moon, "
        "Venus-Mars, and contacts to the Ascendant and Descendant) dominate, while "
        "outer-planet and asteroid contacts contribute little. No percentage is "
        "produced because no absolute scale exists to measure one against."
    ),
    source_note=(
        "Structure follows the consensus across published synastry scoring, most "
        "explicitly Cafe Astrology's system (cafeastrology.com/synastry-2.html and "
        "/compatibility-report-scores.html), whose author states that none of the "
        "weights are absolute and that total activity is more telling than the net "
        "sum. Numbers here are GetBirthChart's own and are not copied from any "
        "source. No independent reference exists to validate a score against, "
        "unlike every other calculation in this engine."
    ),
    aspect_weights={
        "conjunction": 3.0,
        "trine": 3.0,
        "sextile": 2.0,
        "square": -3.0,
        "opposition": -2.0,
    },
    body_weights={
        "sun": 1.0,
        "moon": 1.0,
        "venus": 0.9,
        "mars": 0.8,
        "mercury": 0.6,
        "jupiter": 0.5,
        "saturn": 0.5,
        "uranus": 0.3,
        "neptune": 0.3,
        "pluto": 0.3,
        "true_node": 0.3,
        "mean_node": 0.2,
        "chiron": 0.2,
    },
    angle_weights={
        # The Descendant is the relationship angle; the Ascendant is how one
        # person meets the world. Both outrank the vertical axis here.
        "ascendant": 1.0,
        "descendant": 1.0,
        "mc": 0.6,
        "ic": 0.6,
    },
    pair_bonuses={
        ("moon", "sun"): 1.5,
        ("mars", "venus"): 1.4,
        ("sun", "venus"): 1.2,
        ("moon", "venus"): 1.2,
        ("moon", "moon"): 1.2,
        ("venus", "venus"): 1.2,
        ("sun", "sun"): 1.1,
        ("mars", "mars"): 1.1,
        ("mercury", "mercury"): 1.1,
    },
    orb_floor=0.3,
    angle_axis_of={
        "ascendant": "horizon",
        "descendant": "horizon",
        "mc": "meridian",
        "ic": "meridian",
    },
    angle_axis_primary_end={"horizon": "ascendant", "meridian": "mc"},
    activity_bands=(
        ScoringBand("quiet", 0.0),
        ScoringBand("moderate", 25.0),
        ScoringBand("strong", 50.0),
        ScoringBand("intense", 80.0),
    ),
    balance_bands=(
        ScoringBand("predominantly challenging", -1000.0),
        ScoringBand("mixed", -10.0),
        ScoringBand("predominantly supportive", 10.0),
    ),
)
