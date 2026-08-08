"""Chiron parity against the frozen JPL Horizons fixture."""

from __future__ import annotations

import os
import unittest
from datetime import datetime

from gbc_astro.validation.chiron import (
    CHIRON_HORIZONS_V1,
    load_chiron_fixture,
    run_chiron_parity,
)


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


class ChironFixtureTests(unittest.TestCase):
    """The fixture is the reference, so its provenance is part of the gate."""

    def setUp(self) -> None:
        self.fixture = load_chiron_fixture()

    def test_fixture_declares_its_provenance(self) -> None:
        self.assertEqual(self.fixture["source"], "JPL Horizons")
        self.assertEqual(self.fixture["target"], "2060 Chiron")
        self.assertTrue(self.fixture["independentOfSwissEphemeris"])
        self.assertIn("ecliptic of date", self.fixture["frame"])
        self.assertTrue(self.fixture["capturedAt"])

    def test_fixture_covers_the_supported_date_range(self) -> None:
        samples = self.fixture["samples"]
        self.assertGreaterEqual(len(samples), 500)

        first = datetime.fromisoformat(samples[0]["utc"].replace("Z", "+00:00"))
        last = datetime.fromisoformat(samples[-1]["utc"].replace("Z", "+00:00"))
        self.assertLessEqual(first.year, 1900)
        self.assertGreaterEqual(last.year, 2026)

    def test_samples_advance_in_time_without_duplicates(self) -> None:
        stamps = [sample["utc"] for sample in self.fixture["samples"]]
        self.assertEqual(len(stamps), len(set(stamps)))
        self.assertEqual(stamps, sorted(stamps))

    def test_latitudes_are_non_trivial(self) -> None:
        """Chiron is well off the ecliptic; all-zero latitudes would mean a bad parse."""
        latitudes = [abs(float(sample["latitudeDeg"])) for sample in self.fixture["samples"]]
        self.assertGreater(max(latitudes), 1.0)


@unittest.skipUnless(_swiss_available(), "Chiron parity needs Swiss Ephemeris data")
class ChironParityTests(unittest.TestCase):
    def test_chiron_matches_horizons_within_tolerance(self) -> None:
        report = run_chiron_parity(load_chiron_fixture())

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["outsideToleranceCount"], 0)
        self.assertGreaterEqual(report["sampleCount"], 500)
        self.assertTrue(report["reference"]["independentOfSwissEphemeris"])

    def test_tolerance_has_headroom_over_measured_agreement(self) -> None:
        report = run_chiron_parity(load_chiron_fixture())
        measured = max(report["longitude"]["maxDeg"], report["latitude"]["maxDeg"])
        self.assertLess(measured * 5.0, CHIRON_HORIZONS_V1.longitude_deg)

    def test_an_impossible_tolerance_makes_the_gate_fail(self) -> None:
        """A comparator that cannot fail proves nothing."""
        from gbc_astro.validation.chiron import ChironToleranceProfile

        impossible = ChironToleranceProfile(
            id="test-impossible",
            version="0.0.0",
            rationale="Deliberately unattainable, to prove the gate can fail.",
            longitude_deg=0.0,
            latitude_deg=0.0,
        )
        report = run_chiron_parity(load_chiron_fixture(), tolerance=impossible)

        self.assertEqual(report["status"], "FAIL")
        self.assertGreater(report["outsideToleranceCount"], 0)
