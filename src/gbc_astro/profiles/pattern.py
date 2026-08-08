"""Versioned chart-pattern profile.

A pattern is a claim that several bodies form a named configuration. Whether one
is present depends entirely on how wide an orb you allow, and schools disagree,
so every threshold lives here and travels with the result.

Two decisions worth stating rather than burying:

**Pattern orbs are tighter than aspect orbs.** The natal profile allows eight
degrees on a conjunction, which is right for reading a single aspect and far too
loose for a three-body figure: at eight degrees per leg a grand trine can be
twenty-four degrees out of true and still be reported. The values here are
narrower so that a detected pattern is one someone would recognise on the wheel.

**A grand cross is not also two T-squares.** Every grand cross contains two, and
every kite contains a grand trine. Reporting both would triple the output
without adding anything, so contained figures are suppressed and the profile
says so.
"""

from __future__ import annotations

from dataclasses import dataclass

# The quincunx is needed for yods and is not part of the major-aspect profile,
# so pattern detection carries its own angle table rather than borrowing one.
PATTERN_ANGLES: dict[str, float] = {
    "conjunction": 0.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "quincunx": 150.0,
    "opposition": 180.0,
}


@dataclass(frozen=True)
class PatternProfile:
    id: str
    version: str
    rationale: str
    # Orb allowed per aspect leg when testing a pattern.
    leg_orbs: dict[str, float]
    # A stellium is this many bodies or more sharing a sign.
    stellium_minimum_bodies: int
    stellium_grouping: str
    # Which bodies may take part.
    participating_bodies: tuple[str, ...]
    suppress_contained_patterns: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "version": self.version,
            "rationale": self.rationale,
            "legOrbs": dict(self.leg_orbs),
            "stelliumMinimumBodies": self.stellium_minimum_bodies,
            "stelliumGrouping": self.stellium_grouping,
            "participatingBodies": list(self.participating_bodies),
            "suppressContainedPatterns": self.suppress_contained_patterns,
        }


PATTERN_PROFILE_V1 = PatternProfile(
    id="pattern-v1",
    version="1.0.0",
    rationale=(
        "Orbs per leg are deliberately tighter than the natal aspect profile. A "
        "three-body figure accumulates its legs' error, so eight degrees a leg "
        "would report grand trines twenty-four degrees out of true. Six degrees "
        "for the hard and flowing legs and three for the quincunx keep a detected "
        "figure recognisable on the wheel. Only the ten planets take part: a "
        "grand trine that needs the mean node to close is not a grand trine "
        "anyone draws. Contained figures are suppressed, because every grand "
        "cross holds two T-squares and every kite holds a grand trine, and "
        "reporting both says the same thing three times."
    ),
    leg_orbs={
        "conjunction": 6.0,
        "sextile": 4.0,
        "square": 6.0,
        "trine": 6.0,
        "quincunx": 3.0,
        "opposition": 6.0,
    },
    stellium_minimum_bodies=3,
    stellium_grouping="same_sign",
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
    suppress_contained_patterns=True,
)
