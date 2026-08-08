from __future__ import annotations

import unittest

from gbc_astro import AstrologyEngine
from gbc_astro.validation.reproducibility import calculation_hash
from tests.helpers import FixtureHouseCalculator, FixtureProvider


class ReproducibilityTests(unittest.TestCase):
    def test_same_input_produces_same_hash(self) -> None:
        engine = AstrologyEngine(
            provider=FixtureProvider(),
            house_calculator=FixtureHouseCalculator(),
        )
        kwargs = {
            "local_datetime": "1992-11-03T14:35:00",
            "timezone": "Asia/Ho_Chi_Minh",
            "latitude": 21.0285,
            "longitude": 105.8542,
            "house_system": "equal",
        }
        first = engine.natal(**kwargs)
        second = engine.natal(**kwargs)
        self.assertEqual(calculation_hash(first), calculation_hash(second))
        self.assertEqual(first.to_json(), second.to_json())

