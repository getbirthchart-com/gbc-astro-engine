"""Numerical chart comparison helpers for parity testing."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from gbc_astro.astronomy.circular import shortest_angular_distance
from gbc_astro.models.chart import NatalChart
from gbc_astro.validation.tolerance import ToleranceProfile

PASS_WITHIN_TOLERANCE = "PASS_WITHIN_TOLERANCE"
IMPLEMENTATION_BUG = "IMPLEMENTATION_BUG"
REFERENCE_CONVENTION_DIFFERENCE = "REFERENCE_CONVENTION_DIFFERENCE"
TIMEZONE_MISMATCH = "TIMEZONE_MISMATCH"
DST_RESOLUTION_DIFFERENCE = "DST_RESOLUTION_DIFFERENCE"
HOUSE_SYSTEM_DIFFERENCE = "HOUSE_SYSTEM_DIFFERENCE"
NODE_CONVENTION_DIFFERENCE = "NODE_CONVENTION_DIFFERENCE"
EPHEMERIS_DATA_DIFFERENCE = "EPHEMERIS_DATA_DIFFERENCE"
FLOATING_POINT_NOISE = "FLOATING_POINT_NOISE"
REFERENCE_DATA_ERROR = "REFERENCE_DATA_ERROR"
UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class DifferentialMismatch:
    path: str
    expected: float
    actual: float
    delta: float
    tolerance: float
    classification: str = UNRESOLVED

    def to_dict(self) -> dict[str, float | str]:
        return {
            "path": self.path,
            "expected": self.expected,
            "actual": self.actual,
            "delta": self.delta,
            "tolerance": self.tolerance,
            "classification": self.classification,
        }


@dataclass(frozen=True)
class DifferentialReport:
    tolerance_profile: str
    cases: int = 1
    mismatches: tuple[DifferentialMismatch, ...] = ()
    max_delta_by_path: dict[str, float] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.mismatches

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "pass" if self.passed else "fail",
            "toleranceProfile": self.tolerance_profile,
            "cases": self.cases,
            "mismatchCount": len(self.mismatches),
            "maxDeltaByPath": self.max_delta_by_path,
            "mismatches": [mismatch.to_dict() for mismatch in self.mismatches],
        }


def compare_natal(
    actual: NatalChart,
    expected: Mapping[str, Any],
    tolerance: ToleranceProfile,
) -> DifferentialReport:
    mismatches: list[DifferentialMismatch] = []
    max_delta_by_path: dict[str, float] = {}

    for body_id, expected_body in expected.get("bodies", {}).items():
        if body_id not in actual.bodies:
            continue
        actual_body = actual.bodies[body_id]
        _compare_angle(
            mismatches,
            max_delta_by_path,
            path=f"bodies.{body_id}.longitude",
            expected=float(expected_body["longitude"]),
            actual=actual_body.longitude,
            tolerance=tolerance.longitude_tolerance_for_body(body_id),
        )
        retrograde_expected = expected_body.get("retrograde")
        if retrograde_expected is not None and actual_body.retrograde is not None:
            _compare_boolean(
                mismatches,
                max_delta_by_path,
                path=f"bodies.{body_id}.retrograde",
                expected=bool(retrograde_expected),
                actual=actual_body.retrograde,
            )
        speed_expected = expected_body.get("speedLongitude")
        if speed_expected is not None and actual_body.speed_longitude is not None:
            _compare_linear(
                mismatches,
                max_delta_by_path,
                path=f"bodies.{body_id}.speedLongitude",
                expected=float(speed_expected),
                actual=actual_body.speed_longitude,
                tolerance=tolerance.body_speed_deg_per_day,
            )

    for angle_id, expected_angle in expected.get("angles", {}).items():
        if angle_id not in actual.angles:
            continue
        _compare_angle(
            mismatches,
            max_delta_by_path,
            path=f"angles.{angle_id}.longitude",
            expected=float(expected_angle["longitude"]),
            actual=actual.angles[angle_id].longitude,
            tolerance=tolerance.angle_tolerance_for_angle(angle_id),
        )

    for index, expected_house in enumerate(expected.get("houses", [])):
        if index >= len(actual.houses):
            continue
        _compare_angle(
            mismatches,
            max_delta_by_path,
            path=f"houses.{index + 1}.cuspLongitude",
            expected=float(expected_house["cuspLongitude"]),
            actual=actual.houses[index].cusp_longitude,
            tolerance=tolerance.house_cusp_deg,
        )

    for body_id, expected_body in expected.get("bodies", {}).items():
        if body_id not in actual.bodies:
            continue
        expected_house = expected_body.get("house")
        actual_house = actual.bodies[body_id].house
        if expected_house is not None and actual_house is not None:
            _compare_boolean(
                mismatches,
                max_delta_by_path,
                path=f"bodies.{body_id}.house",
                expected=int(expected_house) == actual_house,
                actual=True,
            )

    return DifferentialReport(
        tolerance_profile=tolerance.id,
        mismatches=tuple(mismatches),
        max_delta_by_path=max_delta_by_path,
    )


def _compare_angle(
    mismatches: list[DifferentialMismatch],
    max_delta_by_path: dict[str, float],
    path: str,
    expected: float,
    actual: float,
    tolerance: float,
) -> None:
    delta = shortest_angular_distance(expected, actual)
    _record_delta(mismatches, max_delta_by_path, path, expected, actual, delta, tolerance)


def _compare_linear(
    mismatches: list[DifferentialMismatch],
    max_delta_by_path: dict[str, float],
    path: str,
    expected: float,
    actual: float,
    tolerance: float,
) -> None:
    delta = abs(expected - actual)
    _record_delta(mismatches, max_delta_by_path, path, expected, actual, delta, tolerance)


def _compare_boolean(
    mismatches: list[DifferentialMismatch],
    max_delta_by_path: dict[str, float],
    path: str,
    expected: bool,
    actual: bool,
) -> None:
    delta = 0.0 if expected == actual else 1.0
    _record_delta(
        mismatches,
        max_delta_by_path,
        path,
        float(expected),
        float(actual),
        delta,
        0.0,
    )


def _record_delta(
    mismatches: list[DifferentialMismatch],
    max_delta_by_path: dict[str, float],
    path: str,
    expected: float,
    actual: float,
    delta: float,
    tolerance: float,
) -> None:
    max_delta_by_path[path] = max(delta, max_delta_by_path.get(path, 0.0))
    if delta > tolerance:
        mismatches.append(
            DifferentialMismatch(
                path=path,
                expected=expected,
                actual=actual,
                delta=delta,
                tolerance=tolerance,
            )
        )
