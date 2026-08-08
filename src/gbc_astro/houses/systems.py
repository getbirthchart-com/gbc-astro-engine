"""House system registry.

Each entry records what the system is, how Swiss Ephemeris names it, and two
properties that matter operationally: whether its cusps are derived from the
angles (so cusp 1 is the Ascendant and cusp 10 the Midheaven), and whether it is
defined at every latitude.

That second property is not cosmetic. Placidus and Koch have no solution beyond
the polar circles, and the engine refuses them there rather than substituting a
system that does -- which is exactly the silent fallback the spec forbids.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HouseSystemProfile:
    id: str
    version: str
    swisseph_code: str
    name: str
    description: str
    # True when cusp 1 is the Ascendant and cusp 10 the Midheaven. Equal-type
    # and axial systems do not hold this.
    quadrant_based: bool
    # True when cusp k + 180 is cusp k + 6 for every k.
    axially_symmetric: bool
    # False for systems with no solution beyond the polar circles.
    defined_at_all_latitudes: bool

    def to_dict(self) -> dict[str, bool | str]:
        return {
            "id": self.id,
            "version": self.version,
            "name": self.name,
            "swissephCode": self.swisseph_code,
            "quadrantBased": self.quadrant_based,
            "axiallySymmetric": self.axially_symmetric,
            "definedAtAllLatitudes": self.defined_at_all_latitudes,
        }


HOUSE_SYSTEMS: dict[str, HouseSystemProfile] = {
    "placidus": HouseSystemProfile(
        id="placidus",
        version="1.0.0",
        swisseph_code="P",
        name="Placidus",
        description=(
            "Divides each body's semi-diurnal and semi-nocturnal arc into thirds. "
            "The most widely used system in modern western astrology, and "
            "undefined beyond the polar circles because the arcs it divides do "
            "not exist there."
        ),
        quadrant_based=True,
        axially_symmetric=True,
        defined_at_all_latitudes=False,
    ),
    "koch": HouseSystemProfile(
        id="koch",
        version="1.0.0",
        swisseph_code="K",
        name="Koch",
        description=(
            "Divides the Ascendant's own diurnal arc. Shares Placidus's polar "
            "limitation for the same reason."
        ),
        quadrant_based=True,
        axially_symmetric=True,
        defined_at_all_latitudes=False,
    ),
    "porphyry": HouseSystemProfile(
        id="porphyry",
        version="1.0.0",
        swisseph_code="O",
        name="Porphyry",
        description=(
            "Trisects the ecliptic arcs between the angles. The simplest quadrant "
            "system, and defined everywhere because it needs nothing but the "
            "Ascendant and Midheaven."
        ),
        quadrant_based=True,
        axially_symmetric=True,
        defined_at_all_latitudes=True,
    ),
    "campanus": HouseSystemProfile(
        id="campanus",
        version="1.0.0",
        swisseph_code="C",
        name="Campanus",
        description="Divides the prime vertical into twelve equal arcs.",
        quadrant_based=True,
        axially_symmetric=True,
        defined_at_all_latitudes=True,
    ),
    "regiomontanus": HouseSystemProfile(
        id="regiomontanus",
        version="1.0.0",
        swisseph_code="R",
        name="Regiomontanus",
        description="Divides the celestial equator into twelve equal arcs.",
        quadrant_based=True,
        axially_symmetric=True,
        defined_at_all_latitudes=True,
    ),
    "alcabitius": HouseSystemProfile(
        id="alcabitius",
        version="1.0.0",
        swisseph_code="B",
        name="Alcabitius",
        description="Trisects the Ascendant's semi-arcs in right ascension.",
        quadrant_based=True,
        axially_symmetric=True,
        defined_at_all_latitudes=True,
    ),
    "topocentric": HouseSystemProfile(
        id="topocentric",
        version="1.0.0",
        swisseph_code="T",
        name="Topocentric (Polich-Page)",
        description=(
            "Placidus-like, computed from a modified geographic latitude. Very "
            "close to Placidus at ordinary latitudes."
        ),
        quadrant_based=True,
        axially_symmetric=True,
        defined_at_all_latitudes=True,
    ),
    "morinus": HouseSystemProfile(
        id="morinus",
        version="1.0.0",
        swisseph_code="M",
        name="Morinus",
        description=(
            "Divides the equator from the RAMC and projects onto the ecliptic. "
            "Cusp 1 is not the Ascendant: the system ignores the horizon entirely."
        ),
        quadrant_based=False,
        axially_symmetric=True,
        defined_at_all_latitudes=True,
    ),
    "meridian": HouseSystemProfile(
        id="meridian",
        version="1.0.0",
        swisseph_code="X",
        name="Meridian (axial rotation)",
        description=(
            "Cusps are the ecliptic points whose right ascension is the RAMC plus "
            "multiples of thirty degrees. Cusp 10 is the Midheaven, but cusp 1 is "
            "the East Point rather than the Ascendant."
        ),
        quadrant_based=False,
        axially_symmetric=True,
        defined_at_all_latitudes=True,
    ),
    "whole_sign": HouseSystemProfile(
        id="whole_sign",
        version="1.0.0",
        swisseph_code="W",
        name="Whole Sign",
        description=(
            "Each house is one whole sign, beginning with the sign holding the "
            "Ascendant. The oldest system and the standard in Vedic practice."
        ),
        quadrant_based=False,
        axially_symmetric=True,
        defined_at_all_latitudes=True,
    ),
    "equal": HouseSystemProfile(
        id="equal",
        version="1.0.0",
        swisseph_code="E",
        name="Equal",
        description="Twelve thirty-degree houses measured from the Ascendant.",
        quadrant_based=True,
        axially_symmetric=True,
        defined_at_all_latitudes=True,
    ),
}

SUPPORTED_HOUSE_SYSTEMS: tuple[str, ...] = tuple(sorted(HOUSE_SYSTEMS))

# Systems whose cusps this engine derives itself rather than taking from the
# provider, so their behaviour is identical at every latitude.
LOCALLY_DERIVED = frozenset({"whole_sign", "equal"})

# Systems whose cusps are defined against *sign boundaries* rather than against
# the angles. These are not equivariant under a zodiac rotation: rotating a
# whole-sign cusp set by an ayanamsa lands every cusp at an arbitrary degree
# instead of at 0 of a sign. They must be rebuilt from the rotated Ascendant,
# not rotated. Equal is safe because ASC + 30k rotates with the Ascendant.
SIGN_ANCHORED = frozenset({"whole_sign"})
