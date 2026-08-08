from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

from gbc_astro import AstrologyEngine
from gbc_astro.errors import GbcAstroError
from gbc_astro.validation.corpus import load_validation_cases
from tests.helpers import FixtureHouseCalculator, FixtureProvider

HOSTILE_CASES = Path("tests/fixtures/hostile_natal_cases.json")
REQUIRED_CATEGORIES = {
    "dst",
    "zodiac_boundary",
    "circular_boundary",
    "house_cusp",
    "high_latitude",
    "retrograde_station",
    "unknown_time",
    "date_line",
    "leap_day",
}


class HostileCorpusTests(unittest.TestCase):
    def test_corpus_shape_and_required_categories(self) -> None:
        with HOSTILE_CASES.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertGreaterEqual(len(payload), 100)
        for item in payload:
            for field in (
                "id",
                "local_datetime",
                "timezone",
                "latitude",
                "longitude",
                "house_system",
                "reason",
                "expected_behavior",
            ):
                self.assertIn(field, item)
            self.assertIn(item["expected_behavior"], {"success", "warning", "error"})
        categories = Counter(item["category"] for item in payload)
        self.assertFalse(REQUIRED_CATEGORIES - set(categories))

    def test_expected_behavior_with_fixture_engine(self) -> None:
        engine = AstrologyEngine(
            provider=FixtureProvider(),
            house_calculator=FixtureHouseCalculator(),
        )
        cases = load_validation_cases(HOSTILE_CASES)
        checked = 0
        for case in cases:
            if case.expected_behavior == "error" and "High latitude" in case.reason:
                continue
            checked += 1
            if case.expected_behavior == "error":
                with self.assertRaises((GbcAstroError, ValueError)):
                    engine.natal(
                        local_datetime=case.local_datetime,
                        timezone=case.timezone,
                        latitude=case.latitude,
                        longitude=case.longitude,
                        house_system=case.house_system,
                        unknown_time=case.unknown_time,
                        fold=case.fold,
                    )
                continue
            chart = engine.natal(
                local_datetime=case.local_datetime,
                timezone=case.timezone,
                latitude=case.latitude,
                longitude=case.longitude,
                house_system=case.house_system,
                unknown_time=case.unknown_time,
                fold=case.fold,
            )
            if case.expected_behavior == "warning":
                self.assertEqual(chart.angles, {})
                self.assertEqual(chart.houses, ())
                self.assertTrue(chart.warnings)
                for body in chart.bodies.values():
                    self.assertIsNone(body.house)
            else:
                self.assertTrue(chart.bodies)
        self.assertGreater(checked, 90)


if __name__ == "__main__":
    unittest.main()
