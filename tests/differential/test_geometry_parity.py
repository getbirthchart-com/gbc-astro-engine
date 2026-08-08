"""Gate-machinery tests for the geometry parity runner.

The full corpus runs through `gbc validate geometry-parity`; these tests keep the
case count small and assert that the runner classifies correctly -- including
that it fails when the engine disagrees with the independent reference, so a
green report cannot come from a comparator that never compares anything.
"""

from __future__ import annotations

import os
import unittest

from gbc_astro.validation.geometry_parity import (
    GEOMETRY_ZONES,
    POLAR_ZONES,
    generate_geometry_cases,
    run_geometry_parity,
)
from gbc_astro.validation.tolerance import GEOMETRY_V0_1_TOLERANCE, GeometryToleranceProfile


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


def _skyfield_available() -> bool:
    try:
        import skyfield  # noqa: F401
    except ImportError:
        return False
    return True


class GeometryCorpusTests(unittest.TestCase):
    def test_corpus_is_deterministic_for_a_seed(self) -> None:
        first = generate_geometry_cases(120, seed=42)
        second = generate_geometry_cases(120, seed=42)
        self.assertEqual([case.id for case in first], [case.id for case in second])
        self.assertEqual(
            [case.local_datetime for case in first], [case.local_datetime for case in second]
        )

    def test_corpus_covers_required_latitude_bands_and_hemispheres(self) -> None:
        cases = generate_geometry_cases(500, seed=42)
        latitudes = {case.latitude for case in cases}
        longitudes = {case.longitude for case in cases}

        self.assertTrue(any(abs(value) < 5.0 for value in latitudes), "equatorial")
        self.assertTrue(any(20.0 < abs(value) < 60.0 for value in latitudes), "mid-latitude")
        self.assertTrue(any(abs(value) >= 60.0 for value in latitudes), "high-latitude")
        self.assertTrue(any(value > 0 for value in longitudes), "eastern hemisphere")
        self.assertTrue(any(value < 0 for value in longitudes), "western hemisphere")

    def test_corpus_sweeps_every_hour_of_the_day(self) -> None:
        cases = generate_geometry_cases(500, seed=42)
        hours = {int(case.local_datetime[11:13]) for case in cases}
        self.assertEqual(hours, set(range(24)))

    def test_corpus_includes_polar_sites_for_the_undefined_branch(self) -> None:
        cases = generate_geometry_cases(500, seed=42)
        polar_latitudes = {latitude for _zone, latitude, _lng, _band in POLAR_ZONES}
        self.assertTrue(polar_latitudes.issubset({case.latitude for case in cases}))

    def test_every_case_requests_placidus(self) -> None:
        cases = generate_geometry_cases(200, seed=7)
        self.assertEqual({case.house_system for case in cases}, {"placidus"})

    def test_zone_table_declares_both_hemispheres(self) -> None:
        bands = {band for _zone, _lat, _lng, band in GEOMETRY_ZONES}
        self.assertIn("equatorial-east", bands)
        self.assertIn("equatorial-west", bands)
        self.assertIn("high-east", bands)
        self.assertIn("high-west", bands)


@unittest.skipUnless(
    _swiss_available() and _skyfield_available(),
    "Geometry parity needs Swiss Ephemeris data and skyfield",
)
class GeometryParityRunnerTests(unittest.TestCase):
    def test_small_corpus_passes_against_the_independent_reference(self) -> None:
        report = run_geometry_parity(generate_geometry_cases(48, seed=42))

        self.assertEqual(report["status"], "PASS")
        self.assertGreater(report["comparedCount"], 0)
        self.assertEqual(report["disagreementCount"], 0)
        self.assertEqual(report["houseAssignmentMismatchCount"], 0)
        self.assertEqual(report["ascendant"]["outsideToleranceCount"], 0)
        self.assertEqual(report["midheaven"]["outsideToleranceCount"], 0)
        self.assertEqual(report["houseCusps"]["outsideToleranceCount"], 0)

    def test_reference_is_declared_independent_of_swiss_ephemeris(self) -> None:
        report = run_geometry_parity(generate_geometry_cases(12, seed=42))
        self.assertTrue(report["reference"]["independentOfSwissEphemeris"])
        self.assertNotEqual(report["reference"]["id"], "swiss-house")

    def test_an_impossible_tolerance_makes_the_gate_fail(self) -> None:
        """A comparator that cannot fail proves nothing: force it to fail."""
        impossible = GeometryToleranceProfile(
            id="test-impossible",
            version="0.0.0",
            reference_source="test",
            rationale="Deliberately unattainable, to prove the gate can fail.",
            ascendant_deg=0.0,
            mc_deg=0.0,
            house_cusp_deg=0.0,
        )
        report = run_geometry_parity(generate_geometry_cases(12, seed=42), tolerance=impossible)

        self.assertEqual(report["status"], "FAIL")
        self.assertGreater(
            report["ascendant"]["outsideToleranceCount"]
            + report["midheaven"]["outsideToleranceCount"]
            + report["houseCusps"]["outsideToleranceCount"],
            0,
        )

    def test_polar_cases_are_excluded_rather_than_silently_compared(self) -> None:
        report = run_geometry_parity(generate_geometry_cases(500, seed=42))

        self.assertGreater(report["agreedUndefinedCount"], 0)
        self.assertEqual(report["disagreementCount"], 0)
        for case in report["agreedUndefinedCases"]:
            self.assertGreaterEqual(abs(case["latitude"]), 66.0)
            self.assertEqual(case["engineErrorCode"], "HOUSE_CALCULATION_UNAVAILABLE")

    def test_default_tolerance_has_headroom_over_measured_agreement(self) -> None:
        report = run_geometry_parity(generate_geometry_cases(48, seed=42))
        measured = max(
            report["ascendant"]["maxDeg"],
            report["midheaven"]["maxDeg"],
            report["houseCusps"]["maxDeg"],
        )
        self.assertLess(measured * 10.0, GEOMETRY_V0_1_TOLERANCE.house_cusp_deg)
