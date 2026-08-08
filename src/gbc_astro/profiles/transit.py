"""Versioned transit orb and ranking profiles.

Transits need their own orb policy. The natal profile allows 8 degrees on a
conjunction, which is right for reading a birth chart and wrong for answering
"what is happening now": measured across twelve monthly snapshots of the
reference chart, natal orbs leave 27 to 44 aspects active at any moment. A
feature that surfaces the three most meaningful transits cannot start from a
pool where everything is always active.

Measured alternatives, same twelve snapshots, mean active aspects:

    natal orbs (8/7/7/5)   36.2   (27-44)
    6/4                    36.2   (27-44)
    4/3                    24.2   (20-30)
    3/2                    18.7   (13-26)   <- chosen
    2/1.5                  12.8   ( 9-18)

3/2 was chosen over the tighter option because a slow outer planet sitting two
to three degrees off exact is genuinely the story of a season, and 2/1.5 drops
those. It was chosen over the wider options because they do not narrow anything.

Ranking is a **product relevance ordering**, not a claim about astrological
truth. Every weight is named here and echoed in the result's provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gbc_astro.profiles.model import AspectProfile, AspectRule

# Spec-mandated transit scope: the ten planets. The lunar nodes and Chiron are
# supported by the engine and appear in natal charts, but they are excluded as
# transiting bodies and as natal targets here. A transiting node is a
# mathematical point moving under a degree a day, and including it would pad the
# pool without adding anything a top-three list would ever surface.
TRANSITING_BODIES: tuple[str, ...] = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
)

NATAL_BODY_TARGETS: tuple[str, ...] = TRANSITING_BODIES

# Angles are targets only when the birth time is known. The Descendant and IC
# are deliberately absent: each is the exact opposite of one of these, so a
# transit square the Ascendant is square the Descendant too, and including both
# would report one geometric fact twice.
NATAL_ANGLE_TARGETS: tuple[str, ...] = ("ascendant", "mc")


TRANSIT_ASPECT_PROFILE_V1 = AspectProfile(
    id="transit-major-v1",
    version="1.0.0",
    rules=(
        AspectRule("conjunction", 0.0, 3.0),
        AspectRule("opposition", 180.0, 3.0),
        AspectRule("square", 90.0, 3.0),
        AspectRule("trine", 120.0, 3.0),
        AspectRule("sextile", 60.0, 2.0),
    ),
)


@dataclass(frozen=True)
class TransitRankingProfile:
    """Weights for ordering transits by product relevance.

    Not a claim about astrological truth. The ordering exists so a caller can
    show three things instead of twenty, and every number behind it is public.
    """

    id: str
    version: str
    rationale: str
    aspect_weights: dict[str, float]
    transiting_body_weights: dict[str, float]
    natal_target_weights: dict[str, float]
    phase_multipliers: dict[str, float]
    exactness_floor: float
    default_top_count: int
    tie_breaker: str = "score_desc_then_transiting_body_natal_target_aspect_asc"

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "version": self.version,
            "rationale": self.rationale,
            "aspectWeights": dict(self.aspect_weights),
            "transitingBodyWeights": dict(self.transiting_body_weights),
            "natalTargetWeights": dict(self.natal_target_weights),
            "phaseMultipliers": dict(self.phase_multipliers),
            "exactnessFloor": self.exactness_floor,
            "defaultTopCount": self.default_top_count,
            "tieBreaker": self.tie_breaker,
        }


TRANSIT_RANKING_V1 = TransitRankingProfile(
    id="transit-ranking-v1",
    version="1.0.0",
    rationale=(
        "A product relevance ordering, not a statement of astrological truth. "
        "Slower transiting bodies outrank faster ones because their contacts last "
        "months rather than hours; hard aspects outrank soft ones because they are "
        "what people notice; contacts to the natal Sun, Moon and Ascendant outrank "
        "contacts to the outer planets because they touch the chart's personal "
        "centre. Exactness dominates within any of those groups. Ties are broken "
        "by name so ordering is stable across runs, never by chance."
    ),
    aspect_weights={
        "conjunction": 1.0,
        "opposition": 0.9,
        "square": 0.9,
        "trine": 0.7,
        "sextile": 0.5,
    },
    transiting_body_weights={
        # Slower body, longer-lived contact, more weight.
        "pluto": 1.0,
        "neptune": 0.95,
        "uranus": 0.9,
        "saturn": 0.85,
        "jupiter": 0.7,
        "mars": 0.55,
        "sun": 0.5,
        "venus": 0.4,
        "mercury": 0.35,
        "moon": 0.25,
    },
    natal_target_weights={
        "sun": 1.0,
        "moon": 1.0,
        "ascendant": 1.0,
        "mc": 0.85,
        "venus": 0.7,
        "mars": 0.7,
        "mercury": 0.6,
        "saturn": 0.6,
        "jupiter": 0.55,
        "uranus": 0.4,
        "neptune": 0.4,
        "pluto": 0.4,
    },
    phase_multipliers={
        "exact": 1.25,
        "applying": 1.15,
        "separating": 1.0,
        "indeterminate": 1.0,
    },
    # An exact contact scores at full weight; one at the edge of orb at this
    # fraction. Exactness therefore separates otherwise-equal contacts without
    # letting a wide contact between heavy bodies vanish.
    exactness_floor=0.35,
    default_top_count=3,
)


@dataclass(frozen=True)
class TransitProfile:
    """The pair of versioned profiles a transit calculation is bound to."""

    aspect_profile: AspectProfile = TRANSIT_ASPECT_PROFILE_V1
    ranking: TransitRankingProfile = TRANSIT_RANKING_V1
    transiting_bodies: tuple[str, ...] = TRANSITING_BODIES
    natal_body_targets: tuple[str, ...] = NATAL_BODY_TARGETS
    natal_angle_targets: tuple[str, ...] = field(default=NATAL_ANGLE_TARGETS)


TRANSIT_PROFILE_V1 = TransitProfile()
