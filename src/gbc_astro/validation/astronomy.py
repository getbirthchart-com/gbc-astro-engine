"""Independent JPL astronomy parity validation."""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from gbc_astro.astronomy.circular import shortest_angular_distance
from gbc_astro.astronomy.time import normalize_local_datetime
from gbc_astro.constants import ENGINE_VERSION
from gbc_astro.providers.swiss import SwissEphemerisProvider
from gbc_astro.validation.reference import JplReferenceSource, ValidationCase

ASTRONOMY_BODIES = (
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
)


@dataclass(frozen=True)
class AstronomyToleranceProfile:
    id: str
    version: str
    rationale: str
    sun_longitude_deg: float
    moon_longitude_deg: float
    inner_planet_longitude_deg: float
    mars_longitude_deg: float
    outer_planet_longitude_deg: float
    latitude_deg: float
    moon_latitude_deg: float
    speed_deg_per_day: float
    moon_speed_deg_per_day: float
    station_speed_threshold_deg_per_day: float

    def longitude_tolerance(self, body: str) -> float:
        if body == "sun":
            return self.sun_longitude_deg
        if body == "moon":
            return self.moon_longitude_deg
        if body in {"mercury", "venus"}:
            return self.inner_planet_longitude_deg
        if body == "mars":
            return self.mars_longitude_deg
        return self.outer_planet_longitude_deg

    def speed_tolerance(self, body: str) -> float:
        if body == "moon":
            return self.moon_speed_deg_per_day
        return self.speed_deg_per_day

    def latitude_tolerance(self, body: str) -> float:
        if body == "moon":
            return self.moon_latitude_deg
        return self.latitude_deg


ASTRONOMY_JPL_PARITY_V1 = AstronomyToleranceProfile(
    id="astronomy-jpl-parity-v1",
    version="0.1.0",
    rationale=(
        "Compares Swiss apparent geocentric tropical ecliptic positions against "
        "JPL DE440S through Skyfield apparent geocentric ecliptic-of-date. "
        "Tolerances allow small residual provider/model differences observed "
        "before validation: Moon is looser because lunar model/frame residuals "
        "are larger; longitude speed is a JPL central finite difference over "
        "the same apparent ecliptic-of-date longitude used for position comparison, "
        "with one-sided evaluation near UTC day boundaries. Retrograde state is "
        "categorical except near stations."
    ),
    sun_longitude_deg=0.001,
    moon_longitude_deg=0.01,
    inner_planet_longitude_deg=0.002,
    mars_longitude_deg=0.001,
    outer_planet_longitude_deg=0.001,
    latitude_deg=0.002,
    moon_latitude_deg=0.01,
    speed_deg_per_day=0.002,
    moon_speed_deg_per_day=0.001,
    station_speed_threshold_deg_per_day=0.001,
)


@dataclass
class MetricAccumulator:
    deltas: list[float] = field(default_factory=list)
    outside_tolerance_count: int = 0
    max_delta_case: str | None = None

    def add(self, case_id: str, delta: float, tolerance: float) -> None:
        self.deltas.append(delta)
        if delta > tolerance:
            self.outside_tolerance_count += 1
        if self.max_delta_case is None or delta >= max(self.deltas[:-1], default=-1.0):
            self.max_delta_case = case_id

    def to_dict(self) -> dict[str, float | int | str | None]:
        if not self.deltas:
            return {
                "meanDelta": None,
                "p50Delta": None,
                "p95Delta": None,
                "p99Delta": None,
                "maxDelta": None,
                "maxDeltaCase": None,
                "outsideToleranceCount": self.outside_tolerance_count,
            }
        ordered = sorted(self.deltas)
        return {
            "meanDelta": sum(self.deltas) / len(self.deltas),
            "p50Delta": _percentile(ordered, 50),
            "p95Delta": _percentile(ordered, 95),
            "p99Delta": _percentile(ordered, 99),
            "maxDelta": max(self.deltas),
            "maxDeltaCase": self.max_delta_case,
            "outsideToleranceCount": self.outside_tolerance_count,
        }


def generate_astronomy_cases(count: int, seed: int) -> tuple[ValidationCase, ...]:
    rng = random.Random(seed)
    zones = (
        ("America/New_York", 40.7128, -74.0060),
        ("America/Los_Angeles", 34.0522, -118.2437),
        ("America/Sao_Paulo", -23.5558, -46.6396),
        ("Europe/London", 51.5074, -0.1278),
        ("Europe/Berlin", 52.52, 13.405),
        ("Africa/Cairo", 30.0444, 31.2357),
        ("Africa/Johannesburg", -26.2041, 28.0473),
        ("Asia/Ho_Chi_Minh", 21.0285, 105.8542),
        ("Asia/Tokyo", 35.6762, 139.6503),
        ("Australia/Sydney", -33.8688, 151.2093),
        ("Pacific/Kiritimati", 1.8721, -157.4278),
        ("Pacific/Honolulu", 21.3069, -157.8583),
        ("UTC", 0.0, 0.0),
    )
    curated_cases = _curated_utc_cases(zones)
    cases: list[ValidationCase] = []
    for index in range(count):
        if index < len(curated_cases):
            utc_dt, zone_name, latitude, longitude, reason = curated_cases[index]
        else:
            start = datetime(1900, 1, 1, tzinfo=timezone.utc)
            end = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
            span_seconds = int((end - start).total_seconds())
            utc_dt = start + timedelta(seconds=rng.randrange(span_seconds))
            zone_name, latitude, longitude = zones[index % len(zones)]
            reason = "JPL astronomy parity random coverage case"
        local_aware = utc_dt.astimezone(ZoneInfo(zone_name))
        local_dt = local_aware.replace(tzinfo=None)
        cases.append(
            ValidationCase(
                id=f"astro-{index + 1:05d}",
                local_datetime=local_dt.isoformat(timespec="seconds"),
                timezone=zone_name,
                latitude=latitude,
                longitude=longitude,
                house_system="equal",
                reason=reason,
                expected_behavior="success",
                fold=local_aware.fold,
            )
        )
    return tuple(cases)


def _curated_utc_cases(
    zones: tuple[tuple[str, float, float], ...],
) -> list[tuple[datetime, str, float, float, str]]:
    cases: list[tuple[datetime, str, float, float, str]] = []
    anchor_years = (1900, 1925, 1950, 1975, 2000, 2026)
    for index in range(len(anchor_years) * 12):
        zone_name, latitude, longitude = zones[index % len(zones)]
        year = anchor_years[(index // 12) % len(anchor_years)]
        month = index % 12 + 1
        day = min(28, 1 + (index * 7) % 28)
        hour = (index * 5) % 24
        minute = (index * 11) % 60
        cases.append(
            (
                datetime(year, month, day, hour, minute, tzinfo=timezone.utc),
                zone_name,
                latitude,
                longitude,
                "JPL astronomy parity anchor year/month coverage case",
            )
        )

    cases.extend(
        (
            datetime(year, 2, 29, 12, tzinfo=timezone.utc),
            "UTC",
            0.0,
            0.0,
            "JPL astronomy parity leap-day coverage case",
        )
        for year in (1904, 1940, 1960, 2000, 2020, 2024)
    )
    cases.extend(
        (
            datetime(2024, month, day, hour, minute, tzinfo=timezone.utc),
            "UTC",
            latitude,
            longitude,
            "JPL astronomy parity Moon zodiac-boundary coverage case",
        )
        for month, day, hour, minute, latitude, longitude in (
            (1, 11, 11, 57, -30.0, -90.0),
            (2, 9, 22, 59, -20.0, -59.0),
            (3, 10, 9, 0, -10.0, -28.0),
            (4, 8, 18, 21, 0.0, 3.0),
            (5, 8, 3, 22, 10.0, 34.0),
            (6, 6, 12, 37, 20.0, 65.0),
            (7, 5, 22, 57, -30.0, -84.0),
            (8, 4, 11, 13, -20.0, -53.0),
            (9, 3, 1, 55, -10.0, -22.0),
            (10, 2, 18, 49, 0.0, 9.0),
            (11, 1, 12, 47, 10.0, 40.0),
            (12, 1, 6, 21, 20.0, 71.0),
        )
    )
    cases.extend(
        (
            utc_dt,
            "UTC",
            34.0522,
            -118.2437,
            reason,
        )
        for utc_dt, reason in (
            (
                datetime(2024, 4, 1, tzinfo=timezone.utc),
                "JPL astronomy parity Mercury retrograde station coverage case",
            ),
            (
                datetime(2024, 4, 25, tzinfo=timezone.utc),
                "JPL astronomy parity Mercury direct station coverage case",
            ),
            (
                datetime(2024, 8, 5, tzinfo=timezone.utc),
                "JPL astronomy parity Mercury retrograde station coverage case",
            ),
            (
                datetime(2024, 8, 28, tzinfo=timezone.utc),
                "JPL astronomy parity Mercury direct station coverage case",
            ),
            (
                datetime(2020, 5, 13, tzinfo=timezone.utc),
                "JPL astronomy parity Venus retrograde station coverage case",
            ),
            (
                datetime(2020, 6, 25, tzinfo=timezone.utc),
                "JPL astronomy parity Venus direct station coverage case",
            ),
        )
    )
    cases.extend(
        (
            utc_dt,
            zone_name,
            latitude,
            longitude,
            "JPL astronomy parity UTC day-boundary coverage case",
        )
        for utc_dt, zone_name, latitude, longitude in (
            (datetime(1900, 1, 1, 0, 0, 2, tzinfo=timezone.utc), "UTC", 0.0, 0.0),
            (
                datetime(1979, 12, 31, 23, 59, 58, tzinfo=timezone.utc),
                "Asia/Tokyo",
                35.6762,
                139.6503,
            ),
            (
                datetime(2000, 1, 1, 0, 0, 2, tzinfo=timezone.utc),
                "Europe/London",
                51.5074,
                -0.1278,
            ),
            (
                datetime(2026, 12, 31, 23, 59, 58, tzinfo=timezone.utc),
                "Pacific/Honolulu",
                21.3069,
                -157.8583,
            ),
        )
    )
    return cases


def run_jpl_astronomy_parity(
    cases: tuple[ValidationCase, ...],
    swiss_ephemeris_path: str | None,
    jpl_ephemeris_path: str | None,
    tolerance: AstronomyToleranceProfile = ASTRONOMY_JPL_PARITY_V1,
) -> dict[str, Any]:
    started = time.perf_counter()
    swiss = SwissEphemerisProvider(ephemeris_path=swiss_ephemeris_path)
    jpl = JplReferenceSource(ephemeris_path=jpl_ephemeris_path)
    metrics = {
        body: {
            "longitude": MetricAccumulator(),
            "latitude": MetricAccumulator(),
            "speed": MetricAccumulator(),
        }
        for body in ASTRONOMY_BODIES
    }
    retrograde_mismatches: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    reference_failures: list[dict[str, str]] = []

    for case in cases:
        try:
            time_norm = normalize_local_datetime(
                datetime.fromisoformat(case.local_datetime),
                case.timezone,
                fold=case.fold,
            )
            instant = time_norm.utc_datetime
            for body in ASTRONOMY_BODIES:
                actual = swiss.position(body, instant)
                reference = jpl.body_position(body, instant)
                longitude_delta = shortest_angular_distance(
                    actual.longitude_deg,
                    reference.longitude_deg,
                )
                latitude_delta = abs(actual.latitude_deg - reference.latitude_deg)
                speed_actual = actual.longitude_speed_deg_per_day
                speed_reference = reference.longitude_speed_deg_per_day
                speed_delta = (
                    abs(speed_actual - speed_reference)
                    if speed_actual is not None and speed_reference is not None
                    else 0.0
                )
                metrics[body]["longitude"].add(
                    case.id,
                    longitude_delta,
                    tolerance.longitude_tolerance(body),
                )
                metrics[body]["latitude"].add(
                    case.id,
                    latitude_delta,
                    tolerance.latitude_tolerance(body),
                )
                metrics[body]["speed"].add(case.id, speed_delta, tolerance.speed_tolerance(body))
                if (speed_actual is not None) and (reference.retrograde is not None):
                    actual_retrograde = speed_actual < 0
                    if actual_retrograde != reference.retrograde:
                        classification = "UNRESOLVED"
                        if (
                            abs(speed_actual) <= tolerance.station_speed_threshold_deg_per_day
                            or abs(speed_reference or 0.0)
                            <= tolerance.station_speed_threshold_deg_per_day
                        ):
                            classification = "STATION_BOUNDARY_CONVENTION"
                        retrograde_mismatches.append(
                            {
                                "caseId": case.id,
                                "body": body,
                                "actualSpeed": speed_actual,
                                "referenceSpeed": speed_reference,
                                "classification": classification,
                            }
                        )
        except Exception as exc:
            reference_failures.append({"caseId": case.id, "error": str(exc)})

    outside_tolerance = _outside_tolerance(metrics)
    unresolved.extend(
        mismatch for mismatch in retrograde_mismatches if mismatch["classification"] == "UNRESOLVED"
    )
    status = (
        "PASS"
        if not outside_tolerance and not unresolved and not reference_failures
        else "FAIL"
    )
    report = {
        "status": status,
        "engineVersion": ENGINE_VERSION,
        "provider": "swiss",
        "providerVersion": swiss.data_version,
        "reference": jpl.id,
        "referenceVersion": jpl.version,
        "jplHealth": jpl.health_check(),
        "toleranceProfile": _tolerance_to_dict(tolerance),
        "caseCount": len(cases),
        "successCount": len(cases) - len(reference_failures),
        "referenceFailureCount": len(reference_failures),
        "referenceFailures": reference_failures[:50],
        "runtimeMs": (time.perf_counter() - started) * 1000.0,
        "bodies": {
            body: {
                "longitude": body_metrics["longitude"].to_dict(),
                "latitude": body_metrics["latitude"].to_dict(),
                "speed": body_metrics["speed"].to_dict(),
            }
            for body, body_metrics in metrics.items()
        },
        "retrogradeMismatchCount": len(retrograde_mismatches),
        "retrogradeMismatches": retrograde_mismatches[:50],
        "outsideToleranceCount": len(outside_tolerance),
        "outsideTolerance": outside_tolerance[:100],
        "unresolvedCount": len(unresolved),
        "unresolved": unresolved[:50],
    }
    return report


def write_astronomy_parity_report(output_dir: str | Path, report: dict[str, Any]) -> None:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "jpl-astronomy-parity.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (path / "JPL_ASTRONOMY_PARITY.md").write_text(_markdown(report), encoding="utf-8")


def _outside_tolerance(metrics: dict[str, dict[str, MetricAccumulator]]) -> list[dict[str, Any]]:
    outside = []
    for body, body_metrics in metrics.items():
        for metric_name, accumulator in body_metrics.items():
            if accumulator.outside_tolerance_count:
                outside.append(
                    {
                        "body": body,
                        "metric": metric_name,
                        "outsideToleranceCount": accumulator.outside_tolerance_count,
                        "maxDelta": max(accumulator.deltas) if accumulator.deltas else None,
                        "maxDeltaCase": accumulator.max_delta_case,
                        "classification": "UNRESOLVED",
                    }
                )
    return outside


def _tolerance_to_dict(tolerance: AstronomyToleranceProfile) -> dict[str, Any]:
    return {
        "id": tolerance.id,
        "version": tolerance.version,
        "rationale": tolerance.rationale,
        "sunLongitudeDeg": tolerance.sun_longitude_deg,
        "moonLongitudeDeg": tolerance.moon_longitude_deg,
        "innerPlanetLongitudeDeg": tolerance.inner_planet_longitude_deg,
        "marsLongitudeDeg": tolerance.mars_longitude_deg,
        "outerPlanetLongitudeDeg": tolerance.outer_planet_longitude_deg,
        "latitudeDeg": tolerance.latitude_deg,
        "moonLatitudeDeg": tolerance.moon_latitude_deg,
        "speedDegPerDay": tolerance.speed_deg_per_day,
        "moonSpeedDegPerDay": tolerance.moon_speed_deg_per_day,
        "stationSpeedThresholdDegPerDay": tolerance.station_speed_threshold_deg_per_day,
    }


def _percentile(ordered: list[float], percentile: int) -> float:
    index = round((percentile / 100.0) * (len(ordered) - 1))
    return ordered[index]


def _markdown(report: dict[str, Any]) -> str:
    if report.get("status") == "BLOCKED":
        return (
            "# JPL Astronomy Parity\n\n"
            "Status: BLOCKED\n\n"
            f"Reference: {report.get('reference')}\n\n"
            f"Cases requested: {report.get('caseCount')}\n\n"
            f"Blocked reason: {report.get('blockedReason')}\n"
        )
    lines = [
        "# JPL Astronomy Parity",
        "",
        f"Status: {report['status']}",
        "",
        f"Reference: {report['reference']} {report['referenceVersion']}",
        f"Cases: {report['caseCount']}",
        f"Outside tolerance: {report['outsideToleranceCount']}",
        f"Retrograde mismatches: {report['retrogradeMismatchCount']}",
        f"Unresolved: {report['unresolvedCount']}",
        "",
    ]
    for metric_name in ("longitude", "latitude", "speed"):
        lines.extend(
            [
                f"## {metric_name.title()}",
                "",
                "| Body | Mean | P50 | P95 | P99 | Max | Max case | Outside tolerance |",
                "|---|---:|---:|---:|---:|---:|---|---:|",
            ]
        )
        for body in ASTRONOMY_BODIES:
            metric = report["bodies"][body][metric_name]
            lines.append(
                "| "
                f"{body} | "
                f"{metric['meanDelta']} | "
                f"{metric['p50Delta']} | "
                f"{metric['p95Delta']} | "
                f"{metric['p99Delta']} | "
                f"{metric['maxDelta']} | "
                f"{metric['maxDeltaCase']} | "
                f"{metric['outsideToleranceCount']} |"
            )
        lines.append("")
    return "\n".join(lines)
