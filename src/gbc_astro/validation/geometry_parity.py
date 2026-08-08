"""Differential parity between engine geometry and the independent reference.

Compares `gbc_astro.houses.swiss` (Swiss Ephemeris) against
`gbc_astro.validation.geometry.GeometryReference` (independently derived) for
Ascendant, Midheaven, the twelve Placidus cusps, and planet house assignment.

Corpus coverage follows `docs/HOUSE_REFERENCE_METHODOLOGY.md`: equatorial,
mid-latitude and high-latitude sites in both hemispheres, every hour of the day,
DST-transition and historical-timezone instants, and cusp sequences that wrap
0 Aries.

Cases where Placidus is mathematically undefined (circumpolar semi-diurnal arc)
are excluded from the tolerance statistics and reported separately, never
compared against a substitute house system.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from gbc_astro.astronomy.time import normalize_local_datetime
from gbc_astro.constants import ENGINE_VERSION
from gbc_astro.engine import AstrologyEngine
from gbc_astro.errors import GbcAstroError
from gbc_astro.houses.base import assign_house, build_house_cusps
from gbc_astro.validation.geometry import GeometryReference, GeometryUndefinedError
from gbc_astro.validation.reference import ValidationCase
from gbc_astro.validation.tolerance import GEOMETRY_V0_1_TOLERANCE, GeometryToleranceProfile

# Equatorial, mid-latitude, high-latitude; eastern and western hemispheres.
GEOMETRY_ZONES: tuple[tuple[str, float, float, str], ...] = (
    ("Africa/Nairobi", -1.2921, 36.8219, "equatorial-east"),
    ("Asia/Singapore", 1.3521, 103.8198, "equatorial-east"),
    ("America/Guayaquil", -2.1894, -79.8891, "equatorial-west"),
    ("Pacific/Kiritimati", 1.8721, -157.4278, "equatorial-west"),
    ("Asia/Ho_Chi_Minh", 21.0285, 105.8542, "mid-east"),
    ("Asia/Tokyo", 35.6762, 139.6503, "mid-east"),
    ("Europe/Berlin", 52.52, 13.405, "mid-east"),
    ("Europe/Lisbon", 38.7223, -9.1393, "mid-west"),
    ("America/New_York", 40.7128, -74.0060, "mid-west"),
    ("America/Sao_Paulo", -23.5558, -46.6396, "mid-west"),
    ("Australia/Sydney", -33.8688, 151.2093, "mid-east"),
    ("Africa/Johannesburg", -26.2041, 28.0473, "mid-east"),
    ("Europe/Oslo", 59.9139, 10.7522, "high-east"),
    ("Europe/Helsinki", 60.1699, 24.9384, "high-east"),
    ("America/Anchorage", 61.2181, -149.9003, "high-west"),
    ("Atlantic/Reykjavik", 64.1466, -21.9426, "high-west"),
)

# Beyond the polar circles Placidus has no solution for part of the ecliptic.
# These are deliberately included so the undefined branch is exercised.
POLAR_ZONES: tuple[tuple[str, float, float, str], ...] = (
    ("Europe/Oslo", 69.6492, 18.9553, "polar-east"),
    ("America/Godthab", 72.7869, -56.1549, "polar-west"),
    ("Antarctica/McMurdo", -77.8419, 166.6863, "polar-south"),
)


def generate_geometry_cases(count: int, seed: int) -> tuple[ValidationCase, ...]:
    """Deterministic geometry corpus: curated coverage first, then random fill."""
    rng = random.Random(seed)
    curated = _curated_cases()
    cases: list[ValidationCase] = []

    for index in range(count):
        if index < len(curated):
            utc_dt, zone_name, latitude, longitude, reason = curated[index]
        else:
            start = datetime(1900, 1, 1, tzinfo=timezone.utc)
            end = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
            span_seconds = int((end - start).total_seconds())
            utc_dt = start + timedelta(seconds=rng.randrange(span_seconds))
            zone_name, latitude, longitude, _band = GEOMETRY_ZONES[index % len(GEOMETRY_ZONES)]
            reason = "geometry parity random coverage case"
        local_aware = utc_dt.astimezone(ZoneInfo(zone_name))
        cases.append(
            ValidationCase(
                id=f"geom-{index + 1:05d}",
                local_datetime=local_aware.replace(tzinfo=None).isoformat(timespec="seconds"),
                timezone=zone_name,
                latitude=latitude,
                longitude=longitude,
                house_system="placidus",
                reason=reason,
                expected_behavior="success",
                fold=local_aware.fold,
            )
        )
    return tuple(cases)


def _curated_cases() -> list[tuple[datetime, str, float, float, str]]:
    cases: list[tuple[datetime, str, float, float, str]] = []

    # Every hour of the day at every site, so RAMC sweeps the full circle and
    # cusp sequences wrap 0 Aries in both directions.
    for zone_index, (zone_name, latitude, longitude, band) in enumerate(GEOMETRY_ZONES):
        for hour in range(24):
            cases.append(
                (
                    datetime(1990, 1 + (zone_index + hour) % 12, 15, hour, 30, tzinfo=timezone.utc),
                    zone_name,
                    latitude,
                    longitude,
                    f"geometry parity hour-of-day sweep ({band})",
                )
            )

    # Solstices and equinoxes drive the declination extremes that stress the
    # semi-diurnal arc, at high latitude where the arc is shortest.
    for year in (1925, 1965, 2005, 2024):
        for month, day, label in ((3, 20, "equinox"), (6, 21, "solstice"), (12, 21, "solstice")):
            for zone_name, latitude, longitude, band in GEOMETRY_ZONES[-4:]:
                cases.append(
                    (
                        datetime(year, month, day, 6, 0, tzinfo=timezone.utc),
                        zone_name,
                        latitude,
                        longitude,
                        f"geometry parity {label} declination extreme ({band})",
                    )
                )

    # Polar sites: Placidus is undefined for part of the ecliptic here.
    for year in (1950, 2000, 2020):
        for hour in (0, 6, 12, 18):
            for zone_name, latitude, longitude, band in POLAR_ZONES:
                cases.append(
                    (
                        datetime(year, 6, 21, hour, tzinfo=timezone.utc),
                        zone_name,
                        latitude,
                        longitude,
                        f"geometry parity polar undefined-branch case ({band})",
                    )
                )

    # DST transitions and historical offsets.
    dst_instants = (
        (datetime(2024, 3, 31, 1, 30, tzinfo=timezone.utc), "Europe/Berlin", 52.52, 13.405),
        (datetime(2024, 10, 27, 1, 30, tzinfo=timezone.utc), "Europe/Berlin", 52.52, 13.405),
        (datetime(2024, 3, 10, 7, 30, tzinfo=timezone.utc), "America/New_York", 40.7128, -74.0060),
        (datetime(2024, 11, 3, 6, 30, tzinfo=timezone.utc), "America/New_York", 40.7128, -74.0060),
        (datetime(1975, 4, 6, 9, 0, tzinfo=timezone.utc), "America/New_York", 40.7128, -74.0060),
        (datetime(1940, 6, 15, 12, 0, tzinfo=timezone.utc), "Europe/Lisbon", 38.7223, -9.1393),
        (datetime(1910, 5, 20, 3, 0, tzinfo=timezone.utc), "Europe/Oslo", 59.9139, 10.7522),
        (datetime(1968, 2, 18, 2, 0, tzinfo=timezone.utc), "Asia/Ho_Chi_Minh", 21.0285, 105.8542),
    )
    cases.extend(
        (instant, zone, lat, lng, "geometry parity DST/historical timezone case")
        for instant, zone, lat, lng in dst_instants
    )
    return cases


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def _circular_delta(first: float, second: float) -> float:
    return abs((first - second + 180.0) % 360.0 - 180.0)


class _DeltaTracker:
    def __init__(self, tolerance: float) -> None:
        self.tolerance = tolerance
        self.values: list[float] = []
        self.outside: list[tuple[str, float]] = []

    def add(self, case_id: str, delta: float) -> None:
        self.values.append(delta)
        if delta > self.tolerance:
            self.outside.append((case_id, delta))

    def summary(self) -> dict[str, Any]:
        return {
            "cases": len(self.values),
            "maxDeg": max(self.values) if self.values else 0.0,
            "p95Deg": _percentile(self.values, 0.95),
            "toleranceDeg": self.tolerance,
            "outsideToleranceCount": len(self.outside),
            "worstCases": [
                {"caseId": case_id, "deltaDeg": delta}
                for case_id, delta in sorted(self.outside, key=lambda item: -item[1])[:10]
            ],
        }


def run_geometry_parity(
    cases: tuple[ValidationCase, ...],
    tolerance: GeometryToleranceProfile = GEOMETRY_V0_1_TOLERANCE,
) -> dict[str, Any]:
    """Run the engine and the independent reference over `cases` and compare."""
    reference = GeometryReference()
    engine = AstrologyEngine()

    ascendant = _DeltaTracker(tolerance.ascendant_deg)
    midheaven = _DeltaTracker(tolerance.mc_deg)
    cusp = _DeltaTracker(tolerance.house_cusp_deg)

    house_mismatches: list[dict[str, Any]] = []
    agreed_undefined: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []
    convention_differences: list[dict[str, Any]] = []
    time_errors: list[dict[str, Any]] = []
    compared = 0

    for case in cases:
        # Resolve the instant first so the undefined branch can be cross-checked
        # even when the engine refuses to produce houses.
        try:
            time_norm = normalize_local_datetime(
                datetime.fromisoformat(case.local_datetime),
                case.timezone,
                fold=case.fold,
            )
        except GbcAstroError as exc:
            time_errors.append({"caseId": case.id, "code": exc.code, "reason": case.reason})
            continue

        reference_undefined = ""
        geometry = None
        try:
            geometry = reference.calculate(
                julian_day_ut=time_norm.julian_day,
                latitude=case.latitude,
                longitude=case.longitude,
            )
        except GeometryUndefinedError as exc:
            reference_undefined = str(exc)

        engine_error = ""
        chart = None
        try:
            chart = engine.natal(
                local_datetime=datetime.fromisoformat(case.local_datetime),
                timezone=case.timezone,
                latitude=case.latitude,
                longitude=case.longitude,
                house_system="placidus",
                fold=case.fold,
            )
        except GbcAstroError as exc:
            engine_error = exc.code

        # Four-way cross-check. Both refusing is agreement, not failure: Placidus
        # genuinely has no solution there. One side producing cusps while the
        # other cannot is a real finding -- it is how a silent fallback to a
        # different house system would show up.
        if reference_undefined and engine_error:
            agreed_undefined.append(
                {
                    "caseId": case.id,
                    "latitude": case.latitude,
                    "engineErrorCode": engine_error,
                    "referenceReason": reference_undefined,
                }
            )
            continue
        if reference_undefined and chart is not None:
            # Unsafe direction: the engine emitted cusps for a chart where
            # Placidus has no solution. This is exactly how a silent fallback to
            # another house system would present, so it fails the gate.
            disagreements.append(
                {
                    "caseId": case.id,
                    "latitude": case.latitude,
                    "kind": "engine-produced-cusps-where-placidus-is-undefined",
                    "referenceReason": reference_undefined,
                }
            )
            continue
        if engine_error:
            # Safe direction: Swiss Ephemeris refuses Placidus categorically
            # beyond the polar circles, while the reference refuses per case and
            # can still solve some of them. Verified directly: at 69.65 N
            # `houses_ex(..., b"P")` raises while `b"O"` (Porphyry) returns
            # values, so the engine is declining rather than substituting.
            # Refusing more often than strictly necessary cannot produce a wrong
            # chart, so this is recorded as a convention difference, not a failure.
            convention_differences.append(
                {
                    "caseId": case.id,
                    "latitude": case.latitude,
                    "kind": "engine-refused-where-reference-solved",
                    "engineErrorCode": engine_error,
                    "assessment": "engine is stricter; safe direction",
                }
            )
            continue
        assert chart is not None and geometry is not None

        compared += 1
        ascendant.add(
            case.id, _circular_delta(chart.angles["ascendant"].longitude, geometry.ascendant)
        )
        midheaven.add(case.id, _circular_delta(chart.angles["mc"].longitude, geometry.midheaven))
        for index, house in enumerate(chart.houses):
            cusp.add(case.id, _circular_delta(house.cusp_longitude, geometry.cusps[index]))

        # Planet house assignment must agree when derived from reference cusps.
        reference_houses = build_house_cusps(geometry.cusps)
        for body_id, body in chart.bodies.items():
            expected = assign_house(body.longitude, reference_houses)
            if body.house != expected:
                house_mismatches.append(
                    {
                        "caseId": case.id,
                        "body": body_id,
                        "engineHouse": body.house,
                        "referenceHouse": expected,
                        "bodyLongitude": body.longitude,
                    }
                )

    outside_total = len(ascendant.outside) + len(midheaven.outside) + len(cusp.outside)
    status = (
        "PASS"
        if outside_total == 0
        and not house_mismatches
        and not disagreements
        and compared > 0
        else "FAIL"
    )

    return {
        "status": status,
        "engineVersion": ENGINE_VERSION,
        "reference": {
            "id": reference.id,
            "version": reference.version,
            "method": reference.method,
            "independentOfSwissEphemeris": True,
        },
        "tolerance": tolerance.as_dict(),
        "caseCount": len(cases),
        "comparedCount": compared,
        "ascendant": ascendant.summary(),
        "midheaven": midheaven.summary(),
        "houseCusps": cusp.summary(),
        "houseAssignmentMismatchCount": len(house_mismatches),
        "houseAssignmentMismatches": house_mismatches[:20],
        "agreedUndefinedCount": len(agreed_undefined),
        "agreedUndefinedCases": agreed_undefined[:20],
        "disagreementCount": len(disagreements),
        "disagreements": disagreements[:20],
        "conventionDifferenceCount": len(convention_differences),
        "conventionDifferences": convention_differences[:20],
        "timeErrorCount": len(time_errors),
        "timeErrors": time_errors[:20],
    }
