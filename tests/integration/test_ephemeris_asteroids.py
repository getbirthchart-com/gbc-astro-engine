"""Ephemeris generator and optional-body tests.

The generator's one claim is that a row equals a single-instant call, and the
asteroid layer's one claim is that it says what it can do instead of failing
unpredictably. Both are asserted directly.
"""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone

from gbc_astro import AstrologyEngine
from gbc_astro.charts.ephemeris import iter_ephemeris
from gbc_astro.errors import UnsupportedBodyError
from gbc_astro.providers.asteroids import (
    OPTIONAL_BODIES,
    available_optional_bodies,
    parse_numbered_asteroid,
)
from gbc_astro.providers.swiss import SwissEphemerisProvider

START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


class NumberedAsteroidParsingTests(unittest.TestCase):
    def test_valid_identifiers_parse(self) -> None:
        self.assertEqual(parse_numbered_asteroid("asteroid_433"), 433)
        self.assertEqual(parse_numbered_asteroid("asteroid_2060"), 2060)

    def test_invalid_identifiers_do_not(self) -> None:
        for value in ("asteroid_", "asteroid_abc", "asteroid_0", "433", "ceres", ""):
            with self.subTest(value=value):
                self.assertIsNone(parse_numbered_asteroid(value))


@unittest.skipUnless(_swiss_available(), "Optional bodies need Swiss Ephemeris data")
class OptionalBodyCapabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = SwissEphemerisProvider(
            ephemeris_path=os.environ["GBC_SWISS_EPHE_PATH"]
        )

    def test_the_standard_six_are_available_with_the_asteroid_file(self) -> None:
        capabilities = {
            capability.body_id: capability
            for capability in available_optional_bodies(
                os.environ["GBC_SWISS_EPHE_PATH"]
            )
        }
        self.assertEqual(set(capabilities), set(OPTIONAL_BODIES))
        for body_id, capability in capabilities.items():
            with self.subTest(body=body_id):
                self.assertTrue(capability.available, body_id)

    def test_an_unprovisioned_asteroid_reports_why_rather_than_raising(self) -> None:
        """Section 4: capability metadata, not unpredictable failure."""
        capabilities = available_optional_bodies(
            os.environ["GBC_SWISS_EPHE_PATH"], extra=("asteroid_433",)
        )
        eros = next(c for c in capabilities if c.body_id == "asteroid_433")
        self.assertFalse(eros.available)
        self.assertIsNotNone(eros.reason)
        self.assertIn("se<number>.se1", str(eros.reason))

    def test_an_unknown_body_is_reported_not_guessed(self) -> None:
        capabilities = available_optional_bodies(
            os.environ["GBC_SWISS_EPHE_PATH"], extra=("nibiru",)
        )
        unknown = next(c for c in capabilities if c.body_id == "nibiru")
        self.assertFalse(unknown.available)

    def test_optional_bodies_calculate_real_positions(self) -> None:
        instant = datetime(1992, 11, 3, 7, 35, tzinfo=timezone.utc)
        for body_id in OPTIONAL_BODIES:
            with self.subTest(body=body_id):
                position = self.provider.position(body_id, instant)
                self.assertGreaterEqual(position.longitude_deg, 0.0)
                self.assertLess(position.longitude_deg, 360.0)
                self.assertIsNotNone(position.longitude_speed_deg_per_day)

    def test_an_asteroid_that_is_off_the_ecliptic_says_so(self) -> None:
        """Otherwise a latitude of exactly zero would suggest a stub."""
        instant = datetime(1992, 11, 3, 7, 35, tzinfo=timezone.utc)
        self.assertGreater(abs(self.provider.position("ceres", instant).latitude_deg), 1.0)

    def test_the_provider_admits_supporting_them(self) -> None:
        for body_id in OPTIONAL_BODIES:
            self.assertTrue(self.provider.supports_body(body_id), body_id)
        self.assertTrue(self.provider.supports_body("asteroid_433"))
        self.assertFalse(self.provider.supports_body("nibiru"))

    def test_a_genuinely_unknown_body_still_raises_on_use(self) -> None:
        with self.assertRaises(UnsupportedBodyError):
            self.provider.position("nibiru", datetime(2000, 1, 1, tzinfo=timezone.utc))


@unittest.skipUnless(_swiss_available(), "Ephemeris generation needs Swiss Ephemeris data")
class EphemerisGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.provider = SwissEphemerisProvider(ephemeris_path=path)
        self.engine = AstrologyEngine(provider=self.provider)

    def test_a_row_equals_a_single_instant_call(self) -> None:
        """The generator is a convenience, not a second calculation path."""
        table = self.engine.ephemeris(
            ("sun", "moon"), START, START + timedelta(days=3), timedelta(days=1)
        )
        from gbc_astro.providers.normalization import normalize_body_position

        for row in table["rows"]:
            instant = datetime.fromisoformat(row["instantUtc"].replace("Z", "+00:00"))
            for body_id in ("sun", "moon"):
                with self.subTest(instant=row["instantUtc"], body=body_id):
                    direct = normalize_body_position(
                        body_id, self.provider.position(body_id, instant)
                    ).to_dict()
                    self.assertEqual(row["bodies"][body_id], direct)

    def test_the_range_is_inclusive_of_both_ends(self) -> None:
        table = self.engine.ephemeris(
            ("sun",), START, START + timedelta(days=4), timedelta(days=1)
        )
        self.assertEqual(table["rowCount"], 5)
        self.assertEqual(table["rows"][0]["instantUtc"], "2026-01-01T00:00:00Z")
        self.assertEqual(table["rows"][-1]["instantUtc"], "2026-01-05T00:00:00Z")

    def test_sub_daily_steps_work(self) -> None:
        table = self.engine.ephemeris(
            ("moon",), START, START + timedelta(hours=6), timedelta(hours=2)
        )
        self.assertEqual(table["rowCount"], 4)

    def test_rows_are_yielded_lazily(self) -> None:
        """Bounded memory over an arbitrary range, per requirements section 16."""
        stream = iter_ephemeris(
            self.provider,
            ("sun",),
            START,
            START + timedelta(days=10_000),
            timedelta(days=1),
        )
        first = next(stream)
        self.assertEqual(first.instant_utc, "2026-01-01T00:00:00Z")

    def test_an_oversized_request_is_refused_rather_than_attempted(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.ephemeris(
                ("sun",), START, START + timedelta(days=365), timedelta(days=1), max_rows=10
            )

    def test_invalid_ranges_and_steps_are_refused(self) -> None:
        for start, end, step in (
            (START, START - timedelta(days=1), timedelta(days=1)),
            (START, START + timedelta(days=1), timedelta(0)),
            (START, START + timedelta(days=1), timedelta(days=-1)),
        ):
            with self.subTest(step=step), self.assertRaises(ValueError):
                self.engine.ephemeris(("sun",), start, end, step)

    def test_naive_datetimes_are_refused(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.ephemeris(
                ("sun",), datetime(2026, 1, 1), datetime(2026, 1, 2), timedelta(days=1)
            )

    def test_unsupported_bodies_are_refused_before_any_work(self) -> None:
        with self.assertRaises(UnsupportedBodyError):
            self.engine.ephemeris(
                ("nibiru",), START, START + timedelta(days=1), timedelta(days=1)
            )

    def test_asteroids_can_be_tabulated_too(self) -> None:
        table = self.engine.ephemeris(
            ("ceres", "vesta"), START, START + timedelta(days=2), timedelta(days=1)
        )
        self.assertEqual(table["rowCount"], 3)
        self.assertIn("ceres", table["rows"][0]["bodies"])

    def test_output_is_deterministic(self) -> None:
        arguments = (("sun",), START, START + timedelta(days=2), timedelta(days=1))
        self.assertEqual(
            self.engine.ephemeris(*arguments), self.engine.ephemeris(*arguments)
        )

    def test_provenance_is_recorded(self) -> None:
        table = self.engine.ephemeris(
            ("sun",), START, START + timedelta(days=1), timedelta(days=1)
        )
        self.assertEqual(table["ephemerisProvider"], "swiss")
        self.assertTrue(table["ephemerisDataVersion"])
        self.assertEqual(table["range"]["stepSeconds"], 86400.0)
