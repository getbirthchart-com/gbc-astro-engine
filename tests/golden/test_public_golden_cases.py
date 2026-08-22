from __future__ import annotations

import json
import os
import unittest
from datetime import datetime
from pathlib import Path

from gbc_astro import AstrologyEngine
from gbc_astro.astronomy.time import normalize_local_datetime
from gbc_astro.errors import (
    AmbiguousLocalTimeError,
    HouseCalculationUnavailableError,
    NonexistentLocalTimeError,
)
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.providers.swiss import SwissEphemerisProvider
from tests.helpers import FixtureProvider

CASES = Path(__file__).parents[1] / "fixtures" / "public_golden_cases.json"
HOSTILE = Path(__file__).parents[1] / "fixtures" / "hostile_natal_cases.json"


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    return bool(
        path
        and all(
            os.path.exists(os.path.join(path, name))
            for name in (
                "sepl_18.se1",
                "semo_18.se1",
                "seas_18.se1",
            )
        )
    )


class PublicGoldenManifestTests(unittest.TestCase):
    def test_manifest_is_curated_and_points_to_existing_sources(self) -> None:
        cases = json.loads(CASES.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(cases), 8)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        for case in cases:
            source_ref = case.get("source_test") or case.get("source_fixture")
            self.assertIsNotNone(source_ref)
            source = source_ref.split("::", 1)[0]
            self.assertTrue((CASES.parents[2] / source).exists(), source)

        corpus = json.loads(HOSTILE.read_text(encoding="utf-8"))
        coverage = next(
            case for case in cases if case["id"] == "hostile-corpus-required-boundaries"
        )
        self.assertGreaterEqual(len(corpus), coverage["expected"]["minimum_cases"])
        self.assertTrue(
            set(coverage["expected"]["required_categories"]).issubset(
                {item["category"] for item in corpus}
            )
        )

    def test_timezone_boundary_contract(self) -> None:
        with self.assertRaises(NonexistentLocalTimeError):
            normalize_local_datetime(
                datetime.fromisoformat("2024-03-10T02:30:00"),
                "America/New_York",
            )
        with self.assertRaises(AmbiguousLocalTimeError):
            normalize_local_datetime(
                datetime.fromisoformat("2024-11-03T01:30:00"),
                "America/New_York",
            )
        first = normalize_local_datetime(
            datetime.fromisoformat("2024-11-03T01:30:00"), "America/New_York", fold=0
        )
        second = normalize_local_datetime(
            datetime.fromisoformat("2024-11-03T01:30:00"), "America/New_York", fold=1
        )
        self.assertNotEqual(first.utc_datetime, second.utc_datetime)

    def test_unknown_time_contract_is_explicit(self) -> None:
        engine = AstrologyEngine(provider=FixtureProvider())
        chart = engine.natal(
            local_datetime="1992-11-03",
            timezone="Asia/Ho_Chi_Minh",
            latitude=21.0285,
            longitude=105.8542,
            house_system="equal",
            unknown_time=True,
        )
        self.assertEqual(chart.angles, {})
        self.assertEqual(chart.houses, ())
        self.assertEqual(chart.warnings[0].code, "UNKNOWN_BIRTH_TIME")


@unittest.skipUnless(_swiss_available(), "Swiss Ephemeris data not configured")
class PublicSwissGoldenTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )

    def test_known_time_natal_values_match_existing_trusted_fixture(self) -> None:
        chart = self.engine.natal(
            local_datetime="1992-11-03T14:35:00",
            timezone="Asia/Ho_Chi_Minh",
            latitude=21.0285,
            longitude=105.8542,
            house_system="placidus",
        )
        expected = json.loads(CASES.read_text(encoding="utf-8"))[0]["expected"]
        self.assertAlmostEqual(chart.bodies["sun"].longitude, expected["sun_longitude"])
        self.assertAlmostEqual(chart.bodies["moon"].longitude, expected["moon_longitude"])
        self.assertAlmostEqual(chart.angles["ascendant"].longitude, expected["ascendant_longitude"])
        self.assertAlmostEqual(chart.angles["mc"].longitude, expected["mc_longitude"])
        self.assertEqual(chart.derived.big_three, expected["big_three"])
        self.assertEqual(len(chart.aspects), expected["aspect_count"])

    def test_high_latitude_placidus_is_not_silently_substituted(self) -> None:
        with self.assertRaises(HouseCalculationUnavailableError):
            self.engine.natal(
                local_datetime="1992-06-21T12:00:00",
                timezone="UTC",
                latitude=70.0,
                longitude=0.0,
                house_system="placidus",
            )


if __name__ == "__main__":
    unittest.main()
