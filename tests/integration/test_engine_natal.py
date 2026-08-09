from __future__ import annotations

import json
import unittest

from gbc_astro import AstrologyEngine
from tests.helpers import FixtureHouseCalculator, FixtureProvider


class EngineNatalTests(unittest.TestCase):
    def test_exact_time_natal_chart_serializes_canonical_json(self) -> None:
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
        payload = chart.to_dict()
        self.assertEqual(payload["schemaVersion"], "1.3.0")
        self.assertEqual(payload["meta"]["ephemerisProvider"], "fixture")
        self.assertEqual(payload["subject"]["utcDateTime"], "1992-11-03T07:35:00Z")
        self.assertEqual(payload["angles"]["ascendant"]["sign"], "aries")
        self.assertEqual(len(payload["houses"]), 12)
        self.assertIn("sun", payload["bodies"])
        self.assertIsNotNone(payload["bodies"]["sun"]["house"])
        json.loads(chart.to_json())

    def test_unknown_time_omits_time_sensitive_fields(self) -> None:
        engine = AstrologyEngine(provider=FixtureProvider())
        chart = engine.natal(
            local_datetime="1992-11-03",
            timezone="Asia/Ho_Chi_Minh",
            latitude=21.0285,
            longitude=105.8542,
            unknown_time=True,
        )
        payload = chart.to_dict()
        self.assertEqual(payload["angles"], {})
        self.assertEqual(payload["houses"], [])
        self.assertIsNone(payload["meta"]["houseSystem"])
        self.assertIsNone(payload["derived"]["bigThree"]["rising"])
        self.assertEqual(payload["warnings"][0]["code"], "UNKNOWN_BIRTH_TIME")


if __name__ == "__main__":
    unittest.main()

