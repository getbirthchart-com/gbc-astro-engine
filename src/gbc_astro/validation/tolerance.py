"""Versioned tolerance profiles for differential validation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToleranceProfile:
    id: str
    version: str
    reference_source: str
    rationale: str
    body_longitude_deg: float
    moon_longitude_deg: float
    body_speed_deg_per_day: float
    ascendant_deg: float
    mc_deg: float
    house_cusp_deg: float

    def longitude_tolerance_for_body(self, body_id: str) -> float:
        if body_id == "moon":
            return self.moon_longitude_deg
        return self.body_longitude_deg

    def angle_tolerance_for_angle(self, angle_id: str) -> float:
        if angle_id == "ascendant":
            return self.ascendant_deg
        if angle_id == "mc":
            return self.mc_deg
        return max(self.ascendant_deg, self.mc_deg)


@dataclass(frozen=True)
class GeometryToleranceProfile:
    """Tolerance for angle/cusp parity against an independent implementation."""

    id: str
    version: str
    reference_source: str
    rationale: str
    ascendant_deg: float
    mc_deg: float
    house_cusp_deg: float

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "version": self.version,
            "referenceSource": self.reference_source,
            "rationale": self.rationale,
            "ascendantDeg": self.ascendant_deg,
            "mcDeg": self.mc_deg,
            "houseCuspDeg": self.house_cusp_deg,
        }


GEOMETRY_V0_1_TOLERANCE = GeometryToleranceProfile(
    id="geometry-parity-v1",
    version="1.0.0",
    reference_source="gbc-independent-geometry",
    rationale=(
        "Two independent implementations of the same spherical geometry cannot agree "
        "to machine precision: they take sidereal time and true obliquity from "
        "different nutation series (Skyfield IAU 2000B versus Swiss Ephemeris), and "
        "the reference locates cusps by bisection rather than closed form. Measured "
        "agreement across the committed corpus is below 0.001 arcsecond "
        "(~3e-7 deg). The threshold is set at 1e-5 deg (0.036 arcsecond), roughly "
        "30x the observed maximum so nutation-model drift cannot cause a spurious "
        "failure, while remaining about 100x tighter than one arcsecond and far "
        "below any astrologically meaningful difference. Loosening this further "
        "requires new measured evidence recorded in "
        "evidence/v0.1-validation/PLACIDUS_PARITY.md."
    ),
    ascendant_deg=1e-5,
    mc_deg=1e-5,
    house_cusp_deg=1e-5,
)


DEFAULT_V0_1_TOLERANCE = ToleranceProfile(
    id="parity-v1",
    version="0.1.0",
    reference_source="independent-reference-required",
    rationale=(
        "Initial strict numerical tolerance profile for independent v0.1 parity. "
        "Thresholds are intentionally narrow and must not be loosened without "
        "evidence explaining provider/reference characteristics."
    ),
    body_longitude_deg=1e-7,
    moon_longitude_deg=2e-7,
    body_speed_deg_per_day=1e-7,
    ascendant_deg=1e-7,
    mc_deg=1e-7,
    house_cusp_deg=1e-7,
)
