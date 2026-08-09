"""Relationship-type profiles: what matters, for what kind of relationship.

The geometry does not change. Two people have the contacts they have, and a
Venus-Mars square is the same square whether they are lovers, colleagues or
siblings. What changes is how much each dimension counts toward the reading,
and that is the only thing these profiles touch.

Where the weight is applied
---------------------------
Inside each contribution, as it is split across dimensions -- not afterwards on
the dimension totals. Applying it afterwards would scale the totals away from
the contributions that produced them, and the decomposition invariant is the
whole basis of the evidence rule: a dimension score has to remain exactly the
sum of the contributions cited under it.

The weight actually used is published per dimension in the result, so a caller
can see it without dividing the numbers back out.

There is no default relationship type
-------------------------------------
`general-v1` weights every dimension at 1.0 and is what a caller gets when they
say nothing. That is not a fifth opinion about relationships -- it is the
absence of one. Defaulting to `romantic-v1` would be answering a question the
caller never asked, and a compatibility score is exactly the place where that
assumption would be least welcome and least visible.

One axis, deliberately
----------------------
These profiles reweight dimensions and nothing else. They could also reweight
body pairs, aspect families, angles and overlays, and every one of those would
be another table of editorial numbers with no reference to validate against.
One axis is enough to make a work reading differ from a romantic one in the way
that matters, and it keeps what changed between two readings legible.

Not a measurement
-----------------
Editorial weights, like everything else in the scoring layer. The version is
what makes a result reproducible; it is not what makes it true.
"""

from __future__ import annotations

from dataclasses import dataclass

from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.profiles.dimensions import (
    ATTRACTION,
    COMMUNICATION,
    CONFLICT,
    DIMENSION_IDS,
    EMOTIONAL,
    GROWTH,
    STABILITY,
)


@dataclass(frozen=True)
class RelationshipTypeProfile:
    id: str
    version: str
    label: str
    rationale: str
    # Multiplier per dimension. A dimension absent from the table weighs 1.0,
    # so a profile only has to state where it differs from neutral.
    dimension_weights: dict[str, float]

    def weight_for(self, dimension: str) -> float:
        return self.dimension_weights.get(dimension, 1.0)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "version": self.version,
            "label": self.label,
            "rationale": self.rationale,
            "dimensionWeights": {
                dimension: self.weight_for(dimension) for dimension in DIMENSION_IDS
            },
        }


GENERAL_V1 = RelationshipTypeProfile(
    id="general-v1",
    version="1.0.0",
    label="Unspecified",
    rationale=(
        "Every dimension at 1.0. Not a fifth opinion about relationships but "
        "the absence of one, for a caller who has not said what kind of "
        "relationship this is. Assuming romantic would answer a question they "
        "never asked."
    ),
    dimension_weights={},
)

ROMANTIC_V1 = RelationshipTypeProfile(
    id="romantic-v1",
    version="1.0.0",
    label="Romantic",
    rationale=(
        "Attraction and emotional life carry a romantic reading, and conflict "
        "matters more here than anywhere else because a romantic relationship "
        "has fewer structures to absorb friction than a working one does. "
        "Communication is not demoted -- it is left at neutral rather than "
        "raised, because it matters to every kind of relationship equally."
    ),
    dimension_weights={
        ATTRACTION: 1.6,
        EMOTIONAL: 1.4,
        CONFLICT: 1.2,
        STABILITY: 1.1,
        GROWTH: 0.9,
    },
)

FRIENDSHIP_V1 = RelationshipTypeProfile(
    id="friendship-v1",
    version="1.0.0",
    label="Friendship",
    rationale=(
        "Friendships rest on talking easily and on growing in compatible "
        "directions. Attraction is heavily demoted rather than removed: it is "
        "not the point, but a Venus contact still describes real warmth "
        "between friends and zeroing it would delete evidence rather than "
        "reweight it."
    ),
    dimension_weights={
        COMMUNICATION: 1.5,
        GROWTH: 1.4,
        EMOTIONAL: 1.2,
        ATTRACTION: 0.4,
        CONFLICT: 0.8,
    },
)

FAMILY_V1 = RelationshipTypeProfile(
    id="family-v1",
    version="1.0.0",
    label="Family",
    rationale=(
        "Family relationships are not chosen and not easily left, so what "
        "matters most is emotional weather, endurance, and how friction "
        "persists. Conflict is weighted highest of any profile here for that "
        "reason. Attraction is demoted furthest for the obvious one."
    ),
    dimension_weights={
        EMOTIONAL: 1.5,
        STABILITY: 1.4,
        CONFLICT: 1.3,
        ATTRACTION: 0.2,
        GROWTH: 1.0,
    },
)

WORK_V1 = RelationshipTypeProfile(
    id="work-v1",
    version="1.0.0",
    label="Working",
    rationale=(
        "Working relationships are judged on getting things said and getting "
        "them done, so communication and stability lead. Conflict is weighted "
        "up because unresolved friction is more costly where the relationship "
        "is instrumental. Attraction is demoted furthest of all -- not because "
        "it is absent from workplaces, but because it is not what a working "
        "compatibility reading is being asked about."
    ),
    dimension_weights={
        COMMUNICATION: 1.6,
        STABILITY: 1.5,
        CONFLICT: 1.2,
        GROWTH: 1.1,
        EMOTIONAL: 0.7,
        ATTRACTION: 0.15,
    },
)


RELATIONSHIP_TYPE_PROFILES: dict[str, RelationshipTypeProfile] = {
    profile.id: profile
    for profile in (GENERAL_V1, ROMANTIC_V1, FRIENDSHIP_V1, FAMILY_V1, WORK_V1)
}
# Short aliases, because a caller will reach for the plain word.
RELATIONSHIP_TYPE_PROFILES.update(
    {
        "general": GENERAL_V1,
        "romantic": ROMANTIC_V1,
        "friendship": FRIENDSHIP_V1,
        "family": FAMILY_V1,
        "work": WORK_V1,
    }
)


def resolve_relationship_type(name: str | None) -> RelationshipTypeProfile:
    """The named profile, or the neutral one when nothing was said."""
    if name is None or not name.strip():
        return GENERAL_V1
    profile = RELATIONSHIP_TYPE_PROFILES.get(name.strip().lower())
    if profile is None:
        raise InvalidCalculationProfileError(
            "Unknown relationship type. The named types reweight dimensions "
            "differently, so no substitute is chosen.",
            {
                "relationshipType": name,
                "supported": sorted(
                    {p.id for p in RELATIONSHIP_TYPE_PROFILES.values()}
                ),
            },
        )
    return profile
