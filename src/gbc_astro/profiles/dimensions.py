"""Versioned mapping from relationship contacts into dimensions.

A dimension score answers a narrower question than an overall score: not "how
compatible are these two" but "what does the geometry say about how they
communicate", separately from what it says about attraction or stability. That
is more useful and far more defensible, because each dimension can name the
contacts it rests on.

What decides a dimension
------------------------
Which bodies are involved, and nothing else. Mercury contacts speak to
communication, Moon contacts to emotional life, Venus and Mars to attraction,
Saturn to stability. The aspect only decides whether the contribution is
supportive or challenging -- it does not move a contact from one dimension to
another, because a Mercury square is still about communication.

A contact can land in more than one dimension. Venus-Mercury is both attraction
and communication, and forcing a single home would throw away half of what it
says. Weights per dimension are declared here so a contact counted twice is
counted deliberately and visibly rather than by accident.

Coverage, and why it is reported instead of patched
---------------------------------------------------
A dimension with no contacts is not a score of zero. Zero means the geometry is
neutral; absent means the geometry is silent, and a pair with an unknown birth
time is silent about everything the angles would have said. Reporting
`contactCount` alongside every score keeps the two apart, and keeps a caller
from averaging an absence into a total as though it were evidence.

This is the same reason no overall 0-100 figure is produced here. Summing
dimensions rewards the pair that happens to have more available data, and
dividing by what is available rewards the sparse pair with one strong contact.
Neither is defensible yet, so neither is shipped.

Not a measurement
-----------------
These weights are editorial. Unlike every geometric calculation in this engine,
a dimension score has no independent reference to be validated against, and the
profile version is what makes a result reproducible rather than what makes it
true.
"""

from __future__ import annotations

from dataclasses import dataclass

EMOTIONAL = "emotional"
COMMUNICATION = "communication"
ATTRACTION = "attraction"
STABILITY = "stability"
GROWTH = "growth"
CONFLICT = "conflict"

DIMENSION_IDS: tuple[str, ...] = (
    EMOTIONAL,
    COMMUNICATION,
    ATTRACTION,
    STABILITY,
    GROWTH,
    CONFLICT,
)


@dataclass(frozen=True)
class DimensionProfile:
    id: str
    version: str
    rationale: str
    # Body to the dimensions it speaks to, and how strongly. A body absent from
    # a dimension contributes nothing to it.
    body_dimensions: dict[str, dict[str, float]]
    # Angles carry their own mapping: an Ascendant contact is not the same
    # statement as a contact to the ruler of the first house.
    angle_dimensions: dict[str, dict[str, float]]
    # Hard aspects speak to conflict whatever the bodies involved, so this is
    # added on top of the body mapping rather than replacing it.
    conflict_aspects: tuple[str, ...]
    conflict_aspect_weight: float

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "version": self.version,
            "rationale": self.rationale,
            "dimensions": list(DIMENSION_IDS),
            "bodyDimensions": {
                body: dict(weights) for body, weights in self.body_dimensions.items()
            },
            "angleDimensions": {
                angle: dict(weights) for angle, weights in self.angle_dimensions.items()
            },
            "conflictAspects": list(self.conflict_aspects),
            "conflictAspectWeight": self.conflict_aspect_weight,
        }

    def weights_for(self, subject: str) -> dict[str, float]:
        """Dimension weights for one body or angle. Empty if it speaks to none."""
        return self.body_dimensions.get(subject) or self.angle_dimensions.get(
            subject, {}
        )


SYNASTRY_DIMENSION_PROFILE_V1 = DimensionProfile(
    id="synastry-dimensions-v1",
    version="1.0.0",
    rationale=(
        "Dimensions are decided by the bodies in contact, never by the aspect. "
        "A Mercury square is still about communication; what the aspect decides "
        "is whether the contribution helps or strains. Contacts may belong to "
        "more than one dimension because they genuinely do -- Venus with "
        "Mercury is attraction and communication both -- and the weights make "
        "that double counting deliberate and visible."
    ),
    body_dimensions={
        "sun": {EMOTIONAL: 0.4, GROWTH: 0.6, STABILITY: 0.4},
        "moon": {EMOTIONAL: 1.0, STABILITY: 0.4},
        "mercury": {COMMUNICATION: 1.0},
        "venus": {ATTRACTION: 1.0, EMOTIONAL: 0.5},
        "mars": {ATTRACTION: 0.8, CONFLICT: 0.4},
        "jupiter": {GROWTH: 1.0, EMOTIONAL: 0.3},
        "saturn": {STABILITY: 1.0, CONFLICT: 0.3},
        # Growth only, and no negative weight for stability. "Uranus unsettles"
        # is a real reading, but a negative weight would flip the sign of a
        # supportive contact, which is a stronger editorial claim than this
        # profile makes. The aspect decides whether a contact helps or strains;
        # the body decides only which dimension hears it.
        "uranus": {GROWTH: 0.6},
        "neptune": {EMOTIONAL: 0.5, GROWTH: 0.3},
        "pluto": {ATTRACTION: 0.5, CONFLICT: 0.5},
        # The lunar node and Chiron form contacts and are deliberately given no
        # dimension. Both are read as themes of direction and of injury rather
        # than as any of the six here, and inventing a home for them would put
        # weight behind a claim this profile is not making.
        #
        # Unmapped does not mean silencing. A contact still scores in whatever
        # dimensions its OTHER end speaks to, at the reduced weight the averaging
        # gives it -- Mars trine the node is still about drive, just less
        # squarely than Mars trine Venus. From the emotional dimension's point of
        # view an unmapped body and a body mapped elsewhere are the same thing:
        # not emotional. What an unmapped body never does is introduce a
        # dimension of its own.
        "true_node": {},
        "chiron": {},
    },
    angle_dimensions={
        # The Ascendant is how one person meets the other, so contacts to it are
        # attraction and emotional presence rather than any single theme.
        "ascendant": {ATTRACTION: 0.7, EMOTIONAL: 0.5},
        "descendant": {ATTRACTION: 0.7, EMOTIONAL: 0.5},
        # The Midheaven axis is shared direction and standing, which reads as
        # growth and stability rather than as feeling.
        "mc": {GROWTH: 0.7, STABILITY: 0.5},
        "ic": {EMOTIONAL: 0.7, STABILITY: 0.5},
    },
    conflict_aspects=("square", "opposition"),
    conflict_aspect_weight=0.5,
)
