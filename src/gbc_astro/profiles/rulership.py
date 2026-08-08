"""Versioned rulership and essential-dignity tables.

Rulership involves no astronomy. It is a table: this sign is ruled by that
planet, this planet is exalted in that sign. Nothing here is calculated and
nothing here is measurable -- which is exactly why it has to be versioned and
published rather than hardcoded wherever it happens to be needed. A table that
travels in the result is a table two clients cannot silently disagree about.

Two tables, because the schools genuinely disagree
-------------------------------------------------
The classical scheme has seven planets and assigns every sign a ruler among
them, each of the five non-luminaries taking two signs. When Uranus, Neptune
and Pluto were discovered, modern western practice reassigned Aquarius, Pisces
and Scorpio to them. Both schemes are in current use and they give different
answers for the chart ruler, for every dispositor chain, and for whether a
planet is in detriment.

Neither is a default that can be picked quietly. A Vedic chart uses the
classical seven; a modern western chart usually does not. So the calculation
profile names which table it wants, and every chart says which one it used.

What is derived rather than tabulated
-------------------------------------
Detriment is the sign opposite a planet's domicile, and fall the sign opposite
its exaltation. Both are computed from the two tables above rather than listed
separately, so a typo cannot put a planet in detriment somewhere that does not
face the sign it rules.

What is deliberately absent
---------------------------
The minor Ptolemaic dignities -- triplicity, terms and faces -- are not here.
They multiply the disagreements (there are at least three competing term
tables) and adding them under one arbitrary choice would be worse than not
offering them. The four major dignities are what this profile claims to cover,
and `minor_dignities_included` says so in the published output rather than
leaving a caller to assume completeness.

Vedic practice shares the classical domicile and exaltation tables, which is
why the traditional profile serves both, but its own refinements -- varga
dignity, combustion rules, the disputed rulership claims for Rahu and Ketu --
are not modelled. The profile id names a septenary scheme, not a school.
"""

from __future__ import annotations

from dataclasses import dataclass

from gbc_astro.constants import SIGN_IDS
from gbc_astro.errors import InvalidCalculationProfileError


@dataclass(frozen=True)
class RulershipProfile:
    id: str
    version: str
    rationale: str
    # Sign to its single ruling planet. Single, because a dispositor chain has
    # to have somewhere to go next; co-rulers are reported separately.
    domicile: dict[str, str]
    # Sign to the planet exalted in it. Signs with no exaltation are absent.
    exaltation: dict[str, str]
    # The degree of the exaltation, where tradition names one.
    exaltation_degrees: dict[str, float]
    # Additional rulers acknowledged but not used to walk a chain, so a modern
    # chart can still show that Mars has a claim on Scorpio.
    co_rulers: dict[str, tuple[str, ...]]
    # Bodies this scheme assigns no rulership to at all. Distinct from a planet
    # that has dignities and happens to be in none of them: an outer planet in
    # a septenary scheme is not peregrine, it is simply not rated.
    unrated_bodies: tuple[str, ...]
    minor_dignities_included: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "version": self.version,
            "rationale": self.rationale,
            "domicile": dict(self.domicile),
            "exaltation": dict(self.exaltation),
            "exaltationDegrees": dict(self.exaltation_degrees),
            "coRulers": {sign: list(ids) for sign, ids in self.co_rulers.items()},
            "unratedBodies": list(self.unrated_bodies),
            "minorDignitiesIncluded": self.minor_dignities_included,
        }

    def opposite_sign(self, sign: str) -> str:
        return SIGN_IDS[(SIGN_IDS.index(sign) + 6) % 12]

    def detriment_signs(self, body_id: str) -> tuple[str, ...]:
        """The signs opposite everything this body rules."""
        return tuple(
            self.opposite_sign(sign)
            for sign, ruler in self.domicile.items()
            if ruler == body_id
        )

    def fall_sign(self, body_id: str) -> str | None:
        for sign, exalted in self.exaltation.items():
            if exalted == body_id:
                return self.opposite_sign(sign)
        return None

    def rules(self, body_id: str) -> tuple[str, ...]:
        return tuple(
            sign for sign, ruler in self.domicile.items() if ruler == body_id
        )


# Shared by both schemes: these are not in dispute.
_EXALTATION = {
    "aries": "sun",
    "taurus": "moon",
    "cancer": "jupiter",
    "virgo": "mercury",
    "libra": "saturn",
    "capricorn": "mars",
    "pisces": "venus",
}

# Ptolemy gives a degree for each exaltation. They matter for anyone weighting
# an exact exaltation above a merely exalted sign, so they are published even
# though nothing here currently scores by them.
_EXALTATION_DEGREES = {
    "sun": 19.0,
    "moon": 3.0,
    "mercury": 15.0,
    "venus": 27.0,
    "mars": 28.0,
    "jupiter": 15.0,
    "saturn": 21.0,
}


TRADITIONAL_SEPTENARY_V1 = RulershipProfile(
    id="traditional-septenary-v1",
    version="1.0.0",
    rationale=(
        "The classical seven-planet scheme. The Sun and Moon rule one sign each "
        "and the five remaining planets rule two apiece, one on either side of "
        "the luminaries. Uranus, Neptune, Pluto and Chiron are given no "
        "rulership and are reported as unrated rather than as peregrine, "
        "because a body with no dignities cannot be in none of them."
    ),
    domicile={
        "aries": "mars",
        "taurus": "venus",
        "gemini": "mercury",
        "cancer": "moon",
        "leo": "sun",
        "virgo": "mercury",
        "libra": "venus",
        "scorpio": "mars",
        "sagittarius": "jupiter",
        "capricorn": "saturn",
        "aquarius": "saturn",
        "pisces": "jupiter",
    },
    exaltation=dict(_EXALTATION),
    exaltation_degrees=dict(_EXALTATION_DEGREES),
    co_rulers={},
    unrated_bodies=("uranus", "neptune", "pluto", "chiron", "true_node", "mean_node"),
)


MODERN_WESTERN_V1 = RulershipProfile(
    id="modern-western-v1",
    version="1.0.0",
    rationale=(
        "The classical scheme with Scorpio, Aquarius and Pisces reassigned to "
        "Pluto, Uranus and Neptune. The displaced classical rulers -- Mars, "
        "Saturn and Jupiter -- are kept as co-rulers, reported but not used to "
        "walk a dispositor chain, because a chain needs one next step. Chiron "
        "and the nodes remain unrated: the rulerships proposed for them are not "
        "settled enough to publish as fact."
    ),
    domicile={
        "aries": "mars",
        "taurus": "venus",
        "gemini": "mercury",
        "cancer": "moon",
        "leo": "sun",
        "virgo": "mercury",
        "libra": "venus",
        "scorpio": "pluto",
        "sagittarius": "jupiter",
        "capricorn": "saturn",
        "aquarius": "uranus",
        "pisces": "neptune",
    },
    exaltation=dict(_EXALTATION),
    exaltation_degrees=dict(_EXALTATION_DEGREES),
    co_rulers={
        "scorpio": ("mars",),
        "aquarius": ("saturn",),
        "pisces": ("jupiter",),
    },
    unrated_bodies=("chiron", "true_node", "mean_node"),
)


RULERSHIP_PROFILES: dict[str, RulershipProfile] = {
    TRADITIONAL_SEPTENARY_V1.id: TRADITIONAL_SEPTENARY_V1,
    MODERN_WESTERN_V1.id: MODERN_WESTERN_V1,
    # Short aliases, because "traditional" is what a caller will reach for.
    "traditional": TRADITIONAL_SEPTENARY_V1,
    "modern": MODERN_WESTERN_V1,
}


def resolve_rulership_profile(name: str) -> RulershipProfile:
    profile = RULERSHIP_PROFILES.get(name.strip().lower())
    if profile is None:
        raise InvalidCalculationProfileError(
            "Unknown rulership scheme. The traditional and modern tables give "
            "different chart rulers and different dispositor chains, so no "
            "default is applied.",
            {
                "rulership": name,
                "supported": sorted(
                    {p.id for p in RULERSHIP_PROFILES.values()}
                    | {"traditional", "modern"}
                ),
            },
        )
    return profile


@dataclass(frozen=True)
class DominantProfile:
    """Weights for ordering the planets of a chart by prominence.

    This is a product relevance ordering, in the same sense as the transit
    ranking: every weight is published in the result and no model of any kind
    is involved. It is not a claim about astrological truth, and two schools
    weighting differently would both be entitled to their answer -- which is
    precisely why the weights travel with the score instead of hiding in code.
    """

    id: str
    version: str
    rationale: str
    sign_weight: float
    house_weight: float
    # An angular house is the strongest placement in every scheme that scores
    # this at all, so it earns a multiplier rather than a flat bonus.
    angular_house_multiplier: float
    succedent_house_multiplier: float
    cadent_house_multiplier: float
    dignity_weights: dict[str, float]
    aspect_weight_by_type: dict[str, float]
    # Aspects to a luminary or an angle count for more than aspects to anything
    # else, so the target is weighted too.
    aspect_target_weights: dict[str, float]
    chart_ruler_bonus: float
    luminary_bonus: float
    participating_bodies: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "version": self.version,
            "rationale": self.rationale,
            "signWeight": self.sign_weight,
            "houseWeight": self.house_weight,
            "angularHouseMultiplier": self.angular_house_multiplier,
            "succedentHouseMultiplier": self.succedent_house_multiplier,
            "cadentHouseMultiplier": self.cadent_house_multiplier,
            "dignityWeights": dict(self.dignity_weights),
            "aspectWeightByType": dict(self.aspect_weight_by_type),
            "aspectTargetWeights": dict(self.aspect_target_weights),
            "chartRulerBonus": self.chart_ruler_bonus,
            "luminaryBonus": self.luminary_bonus,
            "participatingBodies": list(self.participating_bodies),
        }


DOMINANT_WESTERN_V1 = DominantProfile(
    id="dominant-western-v1",
    version="1.0.0",
    rationale=(
        "Prominence is scored from four things a reader actually looks at: "
        "where the planet sits by house, what condition it is in by sign, how "
        "much of the chart it aspects, and whether it rules the Ascendant. "
        "Angularity dominates because it is the one factor every school agrees "
        "raises a planet's prominence. Dignity contributes but cannot by itself "
        "make a cadent, unaspected planet dominant."
    ),
    sign_weight=1.0,
    house_weight=1.0,
    angular_house_multiplier=3.0,
    succedent_house_multiplier=1.5,
    cadent_house_multiplier=1.0,
    dignity_weights={
        "domicile": 5.0,
        "exaltation": 4.0,
        "peregrine": 0.0,
        "detriment": -2.0,
        "fall": -3.0,
        "unrated": 0.0,
    },
    aspect_weight_by_type={
        "conjunction": 3.0,
        "opposition": 2.5,
        "square": 2.0,
        "trine": 2.0,
        "sextile": 1.0,
    },
    aspect_target_weights={
        "sun": 2.0,
        "moon": 2.0,
        "ascendant": 2.0,
        "mc": 2.0,
        "default": 1.0,
    },
    chart_ruler_bonus=5.0,
    luminary_bonus=3.0,
    participating_bodies=(
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
    ),
)
