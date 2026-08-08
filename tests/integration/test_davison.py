"""Davison chart tests.

A Davison chart is an ordinary natal calculation at the midpoint moment and
midpoint place of two births. Its point is that everything is real: speeds,
retrograde states, houses, and applying/separating phases that a midpoint
composite cannot honestly provide.
"""

from __future__ import annotations

import os
import unittest
from dataclasses import replace
from datetime import datetime, timezone

from gbc_astro import AstrologyEngine
from gbc_astro.errors import UnknownBirthTimeError
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.providers.swiss import SwissEphemerisProvider
from gbc_astro.relationship.davison import (
    midpoint_instant,
    midpoint_latitude,
    midpoint_longitude,
)


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


class MidpointLocationTests(unittest.TestCase):
    """Geographic longitude wraps at the antimeridian; latitude does not."""

    def test_longitude_wraps_at_the_antimeridian(self) -> None:
        self.assertAlmostEqual(midpoint_longitude(179.0, -179.0), 180.0, places=9)
        self.assertAlmostEqual(midpoint_longitude(-179.0, 179.0), 180.0, places=9)
        self.assertAlmostEqual(midpoint_longitude(170.0, -170.0), 180.0, places=9)

    def test_longitude_across_the_prime_meridian(self) -> None:
        self.assertAlmostEqual(midpoint_longitude(-10.0, 10.0), 0.0, places=9)
        self.assertAlmostEqual(midpoint_longitude(-1.0, 1.0), 0.0, places=9)

    def test_ordinary_longitudes_are_the_plain_mean(self) -> None:
        for first, second in ((10.0, 50.0), (-120.0, -60.0), (100.0, 140.0)):
            with self.subTest(first=first, second=second):
                self.assertAlmostEqual(
                    midpoint_longitude(first, second), (first + second) / 2.0, places=9
                )

    def test_result_stays_in_the_signed_convention(self) -> None:
        for first in (-180.0, -90.0, 0.0, 90.0, 179.9):
            for second in (-179.9, -45.0, 5.0, 120.0, 180.0):
                with self.subTest(first=first, second=second):
                    value = midpoint_longitude(first, second)
                    self.assertGreaterEqual(value, -180.0)
                    self.assertLessEqual(value, 180.0)

    def test_latitude_is_the_plain_mean(self) -> None:
        self.assertAlmostEqual(midpoint_latitude(60.0, -20.0), 20.0, places=9)
        self.assertAlmostEqual(midpoint_latitude(-89.0, 89.0), 0.0, places=9)

    def test_instant_midpoint_is_order_independent(self) -> None:
        first = datetime(1990, 1, 1, tzinfo=timezone.utc)
        second = datetime(1992, 7, 1, 12, 30, tzinfo=timezone.utc)
        self.assertEqual(midpoint_instant(first, second), midpoint_instant(second, first))
        self.assertLess(first, midpoint_instant(first, second))
        self.assertLess(midpoint_instant(first, second), second)


@unittest.skipUnless(_swiss_available(), "Davison charts need Swiss Ephemeris data")
class DavisonChartTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.chart_a = self.engine.natal(
            "1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542
        )
        self.chart_b = self.engine.natal("1990-06-21T08:20:00", "Europe/Berlin", 52.52, 13.405)

    def test_derived_instant_lies_between_the_two_births(self) -> None:
        davison = self.engine.davison(self.chart_a, self.chart_b)
        derived = datetime.fromisoformat(davison.derived_utc_datetime.replace("Z", "+00:00"))
        first = datetime.fromisoformat(self.chart_a.subject.utc_datetime.replace("Z", "+00:00"))
        second = datetime.fromisoformat(self.chart_b.subject.utc_datetime.replace("Z", "+00:00"))

        earlier, later = sorted((first, second))
        self.assertLess(earlier, derived)
        self.assertLess(derived, later)

    def test_bodies_carry_real_speeds_and_retrograde_states(self) -> None:
        """This is the whole point: a composite cannot provide these honestly."""
        davison = self.engine.davison(self.chart_a, self.chart_b)
        for body in davison.chart.bodies.values():
            self.assertIsNotNone(body.speed_longitude)
            self.assertIsNotNone(body.retrograde)
            self.assertIn(body.house, range(1, 13))

    def test_aspects_have_real_applying_and_separating_phases(self) -> None:
        davison = self.engine.davison(self.chart_a, self.chart_b)
        phases = {aspect.phase for aspect in davison.chart.aspects}
        self.assertTrue(phases & {"applying", "separating"})
        self.assertNotEqual(phases, {"indeterminate"})

    def test_chart_is_an_ordinary_natal_chart_at_the_derived_point(self) -> None:
        davison = self.engine.davison(self.chart_a, self.chart_b)
        rebuilt = self.engine.natal(
            local_datetime=davison.derived_utc_datetime.replace("Z", ""),
            timezone="UTC",
            latitude=davison.derived_latitude,
            longitude=davison.derived_longitude,
        )
        self.assertEqual(davison.chart.to_dict(), rebuilt.to_dict())

    def test_davison_is_order_independent(self) -> None:
        forward = self.engine.davison(self.chart_a, self.chart_b)
        backward = self.engine.davison(self.chart_b, self.chart_a)
        self.assertEqual(forward.chart.to_dict(), backward.chart.to_dict())

    def test_davison_with_self_reproduces_the_original_chart(self) -> None:
        davison = self.engine.davison(self.chart_a, self.chart_a)
        self.assertEqual(davison.derived_latitude, self.chart_a.subject.latitude)
        self.assertAlmostEqual(
            davison.derived_longitude, self.chart_a.subject.longitude, places=9
        )
        self.assertAlmostEqual(
            davison.chart.bodies["sun"].longitude,
            self.chart_a.bodies["sun"].longitude,
            places=9,
        )

    def test_unknown_birth_time_is_refused_rather_than_guessed(self) -> None:
        unknown = self.engine.natal(
            "1990-06-21", "Europe/Berlin", 52.52, 13.405, unknown_time=True
        )
        with self.assertRaises(UnknownBirthTimeError):
            self.engine.davison(self.chart_a, unknown)

    def test_mismatched_schema_versions_are_refused(self) -> None:
        from gbc_astro.errors import InvalidCalculationProfileError

        other = replace(self.chart_b, schema_version="9.9.9")
        with self.assertRaises(InvalidCalculationProfileError):
            self.engine.davison(self.chart_a, other)

    def test_provenance_names_the_construction(self) -> None:
        davison = self.engine.davison(self.chart_a, self.chart_b)
        self.assertEqual(
            davison.meta.davison_location_method, "mean_latitude_circular_mean_longitude"
        )
        self.assertIn("DAVISON_DERIVED_LOCATION", {w.code for w in davison.warnings})

        payload = davison.to_dict()
        self.assertEqual(
            set(payload), {"schemaVersion", "meta", "derivedFrom", "chart", "warnings"}
        )
        self.assertEqual(payload["derivedFrom"]["utcDateTime"], davison.derived_utc_datetime)
