"""Versioned profile for derived chart points.

Three points, and only one of them involves a decision.

South Node
----------
The lunar node opposed, exactly 180 degrees from the north node. No school
disagrees, so there is nothing here to configure. It follows whichever node the
chart's `node_type` selected, so a chart using the true node gets a true south
node rather than a mean one sitting a degree away from it.

Vertex
------
The western intersection of the prime vertical with the ecliptic. Its definition
is not in dispute either, and Swiss Ephemeris has been returning it all along in
the same call the engine already makes for houses -- `houses_ex` answers with
eight values and the engine was using two.

What is worth stating is where it misbehaves, which is the opposite end of the
Earth from where one would expect. Measured for a single instant:

    latitude   vertex
      1.0      357.50
      5.0      167.36
     21.0      132.35
     45.0      104.90
     78.2       87.02

It is perfectly stable near the poles, where Placidus has no cusps at all, and
violently sensitive near the equator -- a swing of 170 degrees across four
degrees of latitude. A birth place recorded to the nearest city is fine at 45
degrees and not fine at 5, so low-latitude charts carry a warning.

Part of Fortune -- the one real decision
----------------------------------------
By day the Lot is `Ascendant + Moon - Sun`. The dispute is what to do at night.

The reversing convention swaps the luminaries below the horizon, giving
`Ascendant + Sun - Moon`, on the reasoning that the Moon leads a nocturnal
chart. Most contemporary software does this; Astrodienst does it by default and
exposes it as a setting because, in their own words, astrologers differ.

The non-reversing convention uses one formula always. Ptolemy defined the Lot as
the horoskopos of the Moon -- the Moon's own ascendant -- and reversing breaks
that reading; William Lilly followed him and used the day formula throughout.

For a day chart the two agree exactly. For a night chart they produce two
different points, reflections of each other about the Ascendant, and that is
roughly half of all charts.

There is no defensible silent default, so the profile names one explicitly and
every chart publishes which was used. A night chart additionally carries the
longitude the other convention would have given, because a user comparing
against another program will otherwise see a discrepancy and reasonably read it
as a defect.
"""

from __future__ import annotations

from dataclasses import dataclass

from gbc_astro.errors import InvalidCalculationProfileError

# Below this latitude the vertex moves fast enough with position that a
# city-level birth place is not precise enough to pin it.
VERTEX_SENSITIVE_LATITUDE = 10.0

SECT_REVERSING = "reverse_by_night"
SECT_FIXED = "day_formula_always"


@dataclass(frozen=True)
class PointProfile:
    id: str
    version: str
    rationale: str
    # Which convention the Part of Fortune uses below the horizon.
    part_of_fortune_sect: str
    include_vertex: bool = True
    include_antivertex: bool = True
    include_south_node: bool = True
    include_part_of_fortune: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "version": self.version,
            "rationale": self.rationale,
            "partOfFortuneSect": self.part_of_fortune_sect,
            "includeVertex": self.include_vertex,
            "includeAntivertex": self.include_antivertex,
            "includeSouthNode": self.include_south_node,
            "includePartOfFortune": self.include_part_of_fortune,
        }


WESTERN_POINTS_V1 = PointProfile(
    id="western-points-v1",
    version="1.0.0",
    rationale=(
        "The Part of Fortune reverses its luminaries below the horizon, which "
        "is what most contemporary software does and what Astrodienst does by "
        "default. Ptolemy and Lilly did not reverse, and a night chart "
        "therefore publishes the longitude the other convention would have "
        "given rather than leaving a user to discover the difference against "
        "another program."
    ),
    part_of_fortune_sect=SECT_REVERSING,
)

TRADITIONAL_POINTS_V1 = PointProfile(
    id="traditional-points-v1",
    version="1.0.0",
    rationale=(
        "One formula for the Lot of Fortune whatever the sect, following "
        "Ptolemy's definition of it as the horoskopos of the Moon and Lilly's "
        "practice. Reversing breaks that reading, which is the argument against "
        "it; the argument for it is that the Moon leads a nocturnal chart."
    ),
    part_of_fortune_sect=SECT_FIXED,
)


POINT_PROFILES: dict[str, PointProfile] = {
    WESTERN_POINTS_V1.id: WESTERN_POINTS_V1,
    TRADITIONAL_POINTS_V1.id: TRADITIONAL_POINTS_V1,
    "western": WESTERN_POINTS_V1,
    "traditional": TRADITIONAL_POINTS_V1,
}


def resolve_point_profile(name: str) -> PointProfile:
    profile = POINT_PROFILES.get(name.strip().lower())
    if profile is None:
        raise InvalidCalculationProfileError(
            "Unknown point profile. The two differ over the Part of Fortune "
            "below the horizon, which is about half of all charts, so no "
            "substitute is chosen.",
            {
                "pointProfile": name,
                "supported": sorted({p.id for p in POINT_PROFILES.values()}),
            },
        )
    return profile
