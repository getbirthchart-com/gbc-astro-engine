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
