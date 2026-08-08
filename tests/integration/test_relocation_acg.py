"""Relocation and astrocartography tests.

Both answer the same question from opposite directions: relocation asks what one
other place looked like, astrocartography asks which places looked a particular
way. Neither moves a planet, so both are validated by what must stay fixed.
"""

from __future__ import annotations

import math
import os
import unittest

from gbc_astro import AstrologyEngine
from gbc_astro.astronomy.circular import normalize_longitude, shortest_angular_distance
from gbc_astro.charts.astrocartography import (
    horizon_longitude,
    meridian_longitude,
)
from gbc_astro.errors import InvalidCalculationProfileError, UnsupportedBodyError
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.providers.swiss import SwissEphemerisProvider

BIRTH = ("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


class MeridianAndHorizonTests(unittest.TestCase):
    """Closed forms, checked against their own definitions."""

    def test_the_meridian_is_where_right_ascension_meets_sidereal_time(self) -> None:
        self.assertAlmostEqual(meridian_longitude(100.0, 40.0), 60.0, places=9)

    def test_longitudes_use_the_signed_convention(self) -> None:
        for right_ascension in (0.0, 90.0, 200.0, 359.0):
            with self.subTest(ra=right_ascension):
                value = meridian_longitude(right_ascension, 10.0)
                self.assertGreaterEqual(value, -180.0)
                self.assertLessEqual(value, 180.0)

    def test_a_circumpolar_body_has_no_rising_line(self) -> None:
        """Omitted, never clamped to the nearest latitude that happens to work."""
        self.assertIsNone(horizon_longitude(0.0, 23.0, 80.0, 0.0, rising=True))

    def test_rising_and_setting_are_on_opposite_sides(self) -> None:
        rising = horizon_longitude(0.0, 10.0, 40.0, 0.0, rising=True)
        setting = horizon_longitude(0.0, 10.0, 40.0, 0.0, rising=False)
        assert rising is not None and setting is not None
        self.assertNotAlmostEqual(rising, setting, places=3)


@unittest.skipUnless(_swiss_available(), "Relocation needs Swiss Ephemeris data")
class RelocationTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.natal = self.engine.natal(*BIRTH)

    def test_relocating_to_the_birthplace_reproduces_the_chart(self) -> None:
        same = self.engine.relocate(self.natal, 21.0285, 105.8542)
        self.assertEqual(
            [c.cusp_longitude for c in same.houses],
            [c.cusp_longitude for c in self.natal.houses],
        )
        for name, angle in self.natal.angles.items():
            self.assertEqual(same.angles[name].longitude, angle.longitude, name)

    def test_no_body_moves(self) -> None:
        """The planets were where they were; only the horizon changed."""
        moved = self.engine.relocate(self.natal, 51.5074, -0.1278)
        for body_id, body in self.natal.bodies.items():
            with self.subTest(body=body_id):
                self.assertEqual(moved.bodies[body_id].longitude, body.longitude)
                self.assertEqual(moved.bodies[body_id].latitude, body.latitude)

    def test_aspects_are_unchanged_by_construction(self) -> None:
        moved = self.engine.relocate(self.natal, 51.5074, -0.1278)
        self.assertEqual(
            sorted(round(a.orb, 9) for a in self.natal.aspects),
            sorted(round(a.orb, 9) for a in moved.aspects),
        )
        self.assertIn(
            "RELOCATION_POSITIONS_UNCHANGED", {w.code for w in moved.warnings}
        )

    def test_angles_and_houses_do_change(self) -> None:
        """Otherwise every test above would pass with relocation doing nothing."""
        moved = self.engine.relocate(self.natal, 51.5074, -0.1278)
        self.assertGreater(
            shortest_angular_distance(
                moved.angles["ascendant"].longitude,
                self.natal.angles["ascendant"].longitude,
            ),
            1.0,
        )
        self.assertNotEqual(
            [b.house for b in moved.bodies.values()],
            [b.house for b in self.natal.bodies.values()],
        )

    def test_the_midheaven_depends_only_on_geographic_longitude(self) -> None:
        """It is a meridian property: latitude cannot move it."""
        first = self.engine.relocate(self.natal, 10.0, 30.0)
        second = self.engine.relocate(self.natal, 60.0, 30.0)
        self.assertAlmostEqual(
            shortest_angular_distance(
                first.angles["mc"].longitude, second.angles["mc"].longitude
            ),
            0.0,
            places=6,
        )

    def test_an_unknown_birth_time_is_refused(self) -> None:
        unknown = self.engine.natal(
            "1992-11-03", "Asia/Ho_Chi_Minh", 21.0285, 105.8542, unknown_time=True
        )
        with self.assertRaises(InvalidCalculationProfileError):
            self.engine.relocate(unknown, 51.5, -0.13)

    def test_an_impossible_coordinate_is_refused(self) -> None:
        from gbc_astro.errors import InvalidCoordinateError

        with self.assertRaises(InvalidCoordinateError):
            self.engine.relocate(self.natal, 95.0, 0.0)

    def test_a_different_house_system_can_be_requested(self) -> None:
        moved = self.engine.relocate(
            self.natal, 51.5074, -0.1278, house_system="whole_sign"
        )
        self.assertEqual(moved.meta.house_system, "whole_sign")


@unittest.skipUnless(_swiss_available(), "Astrocartography needs Swiss Ephemeris data")
class AstrocartographyTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.natal = self.engine.natal(*BIRTH)
        self.result = self.engine.astrocartography(
            self.natal, bodies=("sun", "moon", "jupiter")
        )
        self.lines = {line["id"]: line for line in self.result["lines"]}

    def test_four_lines_per_body(self) -> None:
        self.assertEqual(self.result["lineCount"], 12)
        for body in ("sun", "moon", "jupiter"):
            for angle in ("mc", "ic", "ascendant", "descendant"):
                self.assertIn(f"acg.{body}.{angle}", self.lines)

    def test_a_body_on_its_mc_line_really_is_on_the_meridian(self) -> None:
        """In mundo: the body's right ascension equals the local sidereal time."""
        sidereal_time = float(self.result["siderealTimeDeg"])
        for body in ("sun", "moon", "jupiter"):
            line = self.lines[f"acg.{body}.mc"]
            right_ascension = float(line["detail"]["rightAscension"])
            for point in line["points"][::12]:
                with self.subTest(body=body, latitude=point["latitude"]):
                    self.assertAlmostEqual(
                        shortest_angular_distance(
                            right_ascension,
                            normalize_longitude(sidereal_time + point["longitude"]),
                        ),
                        0.0,
                        places=9,
                    )

    def test_a_body_on_its_horizon_line_really_is_at_zero_altitude(self) -> None:
        sidereal_time = float(self.result["siderealTimeDeg"])
        for body in ("sun", "moon", "jupiter"):
            for angle in ("ascendant", "descendant"):
                line = self.lines[f"acg.{body}.{angle}"]
                right_ascension = float(line["detail"]["rightAscension"])
                declination = math.radians(float(line["detail"]["declination"]))
                for point in line["points"][::12]:
                    with self.subTest(body=body, angle=angle):
                        hour_angle = math.radians(
                            normalize_longitude(sidereal_time + point["longitude"])
                            - right_ascension
                        )
                        latitude = math.radians(point["latitude"])
                        altitude = math.degrees(
                            math.asin(
                                math.sin(latitude) * math.sin(declination)
                                + math.cos(latitude)
                                * math.cos(declination)
                                * math.cos(hour_angle)
                            )
                        )
                        self.assertAlmostEqual(altitude, 0.0, places=9)

    def test_the_mc_line_is_a_single_meridian(self) -> None:
        longitudes = {
            round(point["longitude"], 9) for point in self.lines["acg.sun.mc"]["points"]
        }
        self.assertEqual(len(longitudes), 1)
        self.assertEqual(self.lines["acg.sun.mc"]["kind"], "meridian")

    def test_the_ic_line_is_half_a_turn_from_the_mc_line(self) -> None:
        mc = self.lines["acg.sun.mc"]["points"][0]["longitude"]
        ic = self.lines["acg.sun.ic"]["points"][0]["longitude"]
        self.assertAlmostEqual(
            shortest_angular_distance(mc, ic), 180.0, places=6
        )

    def test_the_horizon_lines_are_curves(self) -> None:
        longitudes = {
            round(point["longitude"], 6)
            for point in self.lines["acg.sun.ascendant"]["points"]
        }
        self.assertGreater(len(longitudes), 10)
        self.assertEqual(self.lines["acg.sun.ascendant"]["kind"], "curve")

    def test_an_unknown_body_is_refused(self) -> None:
        with self.assertRaises(UnsupportedBodyError):
            self.engine.astrocartography(self.natal, bodies=("nibiru",))

    def test_results_are_deterministic(self) -> None:
        again = self.engine.astrocartography(self.natal, bodies=("sun",))
        first = self.engine.astrocartography(self.natal, bodies=("sun",))
        self.assertEqual(again["lines"], first["lines"])
