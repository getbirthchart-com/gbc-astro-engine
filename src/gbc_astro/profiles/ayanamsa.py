"""Versioned ayanamsa profiles for the sidereal zodiac.

An ayanamsa is the angular offset between the tropical zodiac, which starts at
the vernal equinox, and a sidereal zodiac fixed against the stars. The two drift
apart at the rate of precession, roughly 50.3 arcseconds a year, so a sidereal
chart is a tropical chart rotated backwards by that offset.

Schools disagree about where the sidereal zodiac begins, and the disagreement is
large -- Fagan-Bradley and Raman differ by more than two degrees, which moves
planets across sign boundaries. There is no correct answer to arbitrate, so the
choice is a profile and every chart records which one produced it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AyanamsaProfile:
    """One named ayanamsa, bound to a Swiss Ephemeris sidereal mode."""

    id: str
    version: str
    swisseph_mode: str
    description: str
    reference_j2000_deg: float

    def to_dict(self) -> dict[str, float | str]:
        return {
            "id": self.id,
            "version": self.version,
            "swissephMode": self.swisseph_mode,
            "description": self.description,
            "referenceJ2000Deg": self.reference_j2000_deg,
        }


# `reference_j2000_deg` is the value at J2000, recorded so a runtime result can
# be sanity-checked against the profile it claims without recomputing anything.
AYANAMSA_PROFILES: dict[str, AyanamsaProfile] = {
    "lahiri": AyanamsaProfile(
        id="lahiri",
        version="1.0.0",
        swisseph_mode="SIDM_LAHIRI",
        description=(
            "The Indian government standard, and the default for most Vedic work. "
            "Anchored near Spica at 180 degrees but defined by its own polynomial "
            "rather than by the star directly."
        ),
        reference_j2000_deg=23.857092,
    ),
    "true_citra": AyanamsaProfile(
        id="true_citra",
        version="1.0.0",
        swisseph_mode="SIDM_TRUE_CITRA",
        description=(
            "Spica held at exactly 180 degrees at every epoch. Unlike the others "
            "this has a direct observable definition, which is what makes it the "
            "one this engine can validate independently."
        ),
        reference_j2000_deg=23.840018,
    ),
    "fagan_bradley": AyanamsaProfile(
        id="fagan_bradley",
        version="1.0.0",
        swisseph_mode="SIDM_FAGAN_BRADLEY",
        description="The western sidereal standard, anchored on Aldebaran and Antares.",
        reference_j2000_deg=24.740300,
    ),
    "krishnamurti": AyanamsaProfile(
        id="krishnamurti",
        version="1.0.0",
        swisseph_mode="SIDM_KRISHNAMURTI",
        description="Used by the Krishnamurti Paddhati school.",
        reference_j2000_deg=23.760240,
    ),
    "raman": AyanamsaProfile(
        id="raman",
        version="1.0.0",
        swisseph_mode="SIDM_RAMAN",
        description=(
            "B. V. Raman's value, about 1.45 degrees from Lahiri -- enough to move "
            "a planet into the neighbouring sign."
        ),
        reference_j2000_deg=22.410791,
    ),
}

DEFAULT_AYANAMSA = "lahiri"
