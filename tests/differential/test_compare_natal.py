from __future__ import annotations

import unittest

from gbc_astro import AstrologyEngine
from gbc_astro.validation import DEFAULT_V0_1_TOLERANCE, compare_natal
from tests.helpers import FixtureHouseCalculator, FixtureProvider


class CompareNatalTests(unittest.TestCase):
    def test_compare_matching_chart_passes(self) -> None:
        engine = AstrologyEngine(
            provider=FixtureProvider(),
            house_calculator=FixtureHouseCalculator(),
        )
        chart = engine.natal(
            local_datetime="1992-11-03T14:35:00",
            timezone="Asia/Ho_Chi_Minh",
            latitude=21.0285,
            longitude=105.8542,
            house_system="equal",
        )
        report = compare_natal(chart, chart.to_dict(), DEFAULT_V0_1_TOLERANCE)
        self.assertTrue(report.passed)
        self.assertEqual(report.to_dict()["mismatchCount"], 0)

    def test_compare_mismatch_reports_unresolved_delta(self) -> None:
        engine = AstrologyEngine(
            provider=FixtureProvider(),
            house_calculator=FixtureHouseCalculator(),
        )
        chart = engine.natal(
            local_datetime="1992-11-03T14:35:00",
            timezone="Asia/Ho_Chi_Minh",
            latitude=21.0285,
            longitude=105.8542,
            house_system="equal",
        )
        expected = chart.to_dict()
        expected["bodies"]["sun"]["longitude"] += 1.0
        report = compare_natal(chart, expected, DEFAULT_V0_1_TOLERANCE)
        self.assertFalse(report.passed)
        self.assertEqual(report.mismatches[0].path, "bodies.sun.longitude")
        self.assertEqual(report.mismatches[0].classification, "UNRESOLVED")


if __name__ == "__main__":
    unittest.main()
