from __future__ import annotations

import os
import unittest

import gbc_astro
from gbc_astro import (
    AstrologyEngine,
    InvalidCoordinatesError,
    InvalidDateError,
    InvalidTimeError,
    MissingBirthTimeError,
    UnsupportedHouseSystemError,
    calculate_aspects,
    calculate_chart,
    calculate_houses,
    calculate_planet_positions,
    get_zodiac_sign,
    normalize_angle,
)
from gbc_astro.errors import (
    AmbiguousLocalTimeError,
    NonexistentLocalTimeError,
)
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.providers.swiss import SwissEphemerisProvider
from tests.helpers import FixtureHouseCalculator, FixtureProvider

HANOI = {
    "date": "1992-11-03",
    "time": "14:35:00",
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542,
    "house_system": "placidus",
}

# Trusted Swiss natal sample from tests/golden/test_swiss_natal.py
HANOI_SUN = 221.14154838535987
HANOI_MOON = 321.2929834918872
HANOI_ASC = 350.1088136374758
HANOI_MC = 263.03877867919044
HANOI_HOUSE_INDEX_1 = 27.07390716301976
HANOI_ASPECT_COUNT = 14


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


def _swiss_engine() -> AstrologyEngine:
    path = os.environ["GBC_SWISS_EPHE_PATH"]
    return AstrologyEngine(
        provider=SwissEphemerisProvider(ephemeris_path=path),
        house_calculator=SwissHouseCalculator(ephemeris_path=path),
    )


def _fixture_engine() -> AstrologyEngine:
    return AstrologyEngine(
        provider=FixtureProvider(),
        house_calculator=FixtureHouseCalculator(),
    )


class ImportSmokeTests(unittest.TestCase):
    def test_import_gbc_astro(self) -> None:
        self.assertTrue(hasattr(gbc_astro, "calculate_chart"))
        self.assertEqual(gbc_astro.__version__, "1.12.1")

    def test_versions_are_aligned(self) -> None:
        from gbc_astro import ENGINE_VERSION, SCHEMA_VERSION

        self.assertEqual(gbc_astro.__version__, "1.12.1")
        self.assertEqual(ENGINE_VERSION, "1.12.1")
        self.assertEqual(SCHEMA_VERSION, "1.3.0")

    def test_calculate_chart_is_exported(self) -> None:
        from gbc_astro import calculate_chart as imported

        self.assertIs(imported, calculate_chart)


class PublicValidationTests(unittest.TestCase):
    def test_invalid_date(self) -> None:
        with self.assertRaises(InvalidDateError):
            calculate_chart(
                "1990-02-31",
                "09:30",
                latitude=51.5074,
                longitude=-0.1278,
                timezone="Europe/London",
            )

    def test_malformed_date(self) -> None:
        with self.assertRaises(InvalidDateError):
            calculate_chart(
                "15/05/1990",
                "09:30",
                latitude=51.5074,
                longitude=-0.1278,
                timezone="Europe/London",
            )

    def test_invalid_time(self) -> None:
        with self.assertRaises(InvalidTimeError):
            calculate_chart(
                "1990-05-15",
                "25:61",
                latitude=51.5074,
                longitude=-0.1278,
                timezone="Europe/London",
            )

    def test_invalid_latitude(self) -> None:
        with self.assertRaises(InvalidCoordinatesError):
            calculate_chart(
                "1990-05-15",
                "09:30",
                latitude=91.0,
                longitude=-0.1278,
                timezone="Europe/London",
            )

    def test_invalid_longitude(self) -> None:
        with self.assertRaises(InvalidCoordinatesError):
            calculate_chart(
                "1990-05-15",
                "09:30",
                latitude=51.5074,
                longitude=181.0,
                timezone="Europe/London",
            )

    def test_unsupported_house_system(self) -> None:
        with self.assertRaises(UnsupportedHouseSystemError):
            calculate_chart(
                "1990-05-15",
                "09:30",
                latitude=51.5074,
                longitude=-0.1278,
                timezone="Europe/London",
                house_system="not-a-system",
            )

    def test_supported_house_system_is_accepted_before_provider(self) -> None:
        from gbc_astro.houses.systems import SUPPORTED_HOUSE_SYSTEMS

        self.assertIn("placidus", SUPPORTED_HOUSE_SYSTEMS)
        self.assertIn("whole_sign", SUPPORTED_HOUSE_SYSTEMS)

    def test_missing_time_houses_api(self) -> None:
        with self.assertRaises(MissingBirthTimeError):
            calculate_houses(
                "1990-05-15",
                latitude=51.5074,
                longitude=-0.1278,
                timezone="Europe/London",
                engine=_fixture_engine(),
            )


class ZodiacAndAngleTests(unittest.TestCase):
    def test_zodiac_sign_boundaries(self) -> None:
        self.assertEqual(get_zodiac_sign(0.0), "aries")
        self.assertEqual(get_zodiac_sign(29.999), "aries")
        self.assertEqual(get_zodiac_sign(30.0), "taurus")
        self.assertEqual(get_zodiac_sign(359.999), "pisces")
        self.assertEqual(get_zodiac_sign(360.0), "aries")

    def test_normalize_angle(self) -> None:
        self.assertEqual(normalize_angle(365.0), 5.0)
        self.assertEqual(normalize_angle(-30.0), 330.0)


class UnknownBirthTimeTests(unittest.TestCase):
    def test_unknown_time_omits_angles_and_houses(self) -> None:
        chart = calculate_chart(
            "1992-11-03",
            latitude=21.0285,
            longitude=105.8542,
            timezone="Asia/Ho_Chi_Minh",
            house_system="equal",
            engine=_fixture_engine(),
        )
        self.assertFalse(chart.subject.birth_time_known)
        self.assertEqual(chart.angles, {})
        self.assertEqual(chart.houses, ())
        self.assertTrue(all(body.house is None for body in chart.bodies.values()))
        self.assertTrue(any(warning.code == "UNKNOWN_BIRTH_TIME" for warning in chart.warnings))
        self.assertEqual(chart.subject.local_datetime, "1992-11-03T00:00:00")

    def test_unknown_time_does_not_default_to_noon(self) -> None:
        chart = calculate_chart(
            "1992-11-03",
            latitude=21.0285,
            longitude=105.8542,
            timezone="Asia/Ho_Chi_Minh",
            engine=_fixture_engine(),
        )
        self.assertNotIn("T12:00:00", chart.subject.local_datetime)
        self.assertTrue(chart.subject.local_datetime.endswith("T00:00:00"))


class DstAndTimezoneTests(unittest.TestCase):
    def test_timezone_conversion_without_provider(self) -> None:
        from datetime import datetime

        from gbc_astro.astronomy.time import normalize_local_datetime

        normalized = normalize_local_datetime(datetime(1992, 11, 3, 14, 35), "Asia/Ho_Chi_Minh")
        self.assertEqual(normalized.utc_datetime.isoformat(), "1992-11-03T07:35:00+00:00")

    def test_dst_nonexistent_local_time(self) -> None:
        with self.assertRaises(NonexistentLocalTimeError):
            calculate_chart(
                "2024-03-10",
                "02:30",
                latitude=40.7128,
                longitude=-74.006,
                timezone="America/New_York",
                engine=_fixture_engine(),
            )

    def test_dst_ambiguous_local_time(self) -> None:
        with self.assertRaises(AmbiguousLocalTimeError):
            calculate_chart(
                "2024-11-03",
                "01:30",
                latitude=40.7128,
                longitude=-74.006,
                timezone="America/New_York",
                engine=_fixture_engine(),
            )
        first = calculate_chart(
            "2024-11-03",
            "01:30",
            latitude=40.7128,
            longitude=-74.006,
            timezone="America/New_York",
            fold=0,
            engine=_fixture_engine(),
        )
        second = calculate_chart(
            "2024-11-03",
            "01:30",
            latitude=40.7128,
            longitude=-74.006,
            timezone="America/New_York",
            fold=1,
            engine=_fixture_engine(),
        )
        self.assertNotEqual(first.subject.utc_datetime, second.subject.utc_datetime)


@unittest.skipUnless(_swiss_available(), "Swiss Ephemeris data not configured")
class SwissPublicApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _swiss_engine()

    def test_known_timed_natal_chart(self) -> None:
        chart = calculate_chart(**HANOI, engine=self.engine)
        self.assertAlmostEqual(chart.bodies["sun"].longitude, HANOI_SUN)
        self.assertAlmostEqual(chart.bodies["moon"].longitude, HANOI_MOON)
        self.assertEqual(chart.bodies["sun"].sign, "scorpio")
        self.assertTrue(chart.subject.birth_time_known)

    def test_planetary_positions(self) -> None:
        bodies = calculate_planet_positions(**HANOI, engine=self.engine)
        self.assertAlmostEqual(bodies["sun"].longitude, HANOI_SUN)
        self.assertAlmostEqual(bodies["chiron"].longitude, 142.609580564659)

    def test_ascendant(self) -> None:
        chart = calculate_chart(**HANOI, engine=self.engine)
        self.assertAlmostEqual(chart.angles["ascendant"].longitude, HANOI_ASC)

    def test_midheaven(self) -> None:
        chart = calculate_chart(**HANOI, engine=self.engine)
        self.assertAlmostEqual(chart.angles["mc"].longitude, HANOI_MC)

    def test_houses(self) -> None:
        houses = calculate_houses(**HANOI, engine=self.engine)
        self.assertEqual(len(houses), 12)
        self.assertAlmostEqual(houses[1].cusp_longitude, HANOI_HOUSE_INDEX_1)

    def test_aspects(self) -> None:
        aspects = calculate_aspects(**HANOI, engine=self.engine)
        self.assertEqual(len(aspects), HANOI_ASPECT_COUNT)

    def test_supported_house_systems_run(self) -> None:
        for system in ("placidus", "whole_sign", "equal", "koch"):
            chart = calculate_chart(
                HANOI["date"],
                HANOI["time"],
                latitude=HANOI["latitude"],
                longitude=HANOI["longitude"],
                timezone=HANOI["timezone"],
                house_system=system,
                engine=self.engine,
            )
            self.assertEqual(len(chart.houses), 12)
            self.assertIn("ascendant", chart.angles)

    def test_deterministic_repeat(self) -> None:
        first = calculate_chart(**HANOI, engine=self.engine)
        second = calculate_chart(**HANOI, engine=self.engine)
        self.assertEqual(first.to_json(), second.to_json())

    def test_regression_matches_engine_natal(self) -> None:
        facade = calculate_chart(**HANOI, engine=self.engine)
        native = self.engine.natal(
            local_datetime="1992-11-03T14:35:00",
            timezone="Asia/Ho_Chi_Minh",
            latitude=21.0285,
            longitude=105.8542,
            house_system="placidus",
        )
        self.assertEqual(facade.to_json(), native.to_json())

    def test_london_1990_timed_chart_matches_engine(self) -> None:
        kwargs = {
            "date": "1990-05-15",
            "time": "09:30",
            "latitude": 51.5074,
            "longitude": -0.1278,
            "timezone": "Europe/London",
            "house_system": "placidus",
        }
        facade = calculate_chart(**kwargs, engine=self.engine)
        native = self.engine.natal(
            local_datetime="1990-05-15T09:30:00",
            timezone="Europe/London",
            latitude=51.5074,
            longitude=-0.1278,
            house_system="placidus",
        )
        self.assertEqual(facade.to_json(), native.to_json())
        self.assertTrue(facade.subject.birth_time_known)
        self.assertEqual(facade.bodies["sun"].sign, "taurus")
        self.assertIn("ascendant", facade.angles)
        self.assertIn("mc", facade.angles)
        self.assertEqual(len(facade.houses), 12)
        self.assertGreater(len(facade.aspects), 0)


if __name__ == "__main__":
    unittest.main()
