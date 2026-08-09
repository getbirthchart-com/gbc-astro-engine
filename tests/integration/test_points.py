"""Vertex, antivertex, Lot of Fortune and south node.

Three things are pinned here, in rough order of how quietly they would fail.

**Sect.** The Lot of Fortune reverses its luminaries below the horizon under the
default profile. Getting day and night backwards is silent -- it yields a
well-formed Lot at the reflection of the right one, on exactly the charts where
the two conventions disagree. This test caught that in development.

**Zodiac.** The vertex arrives from Swiss Ephemeris tropically and is rotated
with its `HouseCalculation`; the Lot and the south node are arithmetic on
longitudes the chart already holds, so the ayanamsa cancels through and rotating
again would double it. Both are asserted against the recorded ayanamsa.

**Relocation.** These points depend on the horizon and the Ascendant, so a
relocated chart has different ones. So does most of the derived block.
"""

from __future__ import annotations

import os
import unittest

from gbc_astro import AstrologyEngine
from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.derived.points import is_day_chart
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.defaults import VEDIC_SIDEREAL_V1
from gbc_astro.profiles.points import TRADITIONAL_POINTS_V1, resolve_point_profile
from gbc_astro.providers.swiss import SwissEphemerisProvider

DAY = ("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
NIGHT = ("1992-11-03T02:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    return bool(path and os.path.exists(os.path.join(path, "sepl_18.se1")))


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class SectTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )

    def test_day_and_night_follow_the_horizon_not_the_clock(self) -> None:
        """Sunrise near 06:20 and sunset near 17:20 in Hanoi in November."""
        verdicts = {}
        for hour in range(0, 24, 2):
            chart = self.engine.natal(
                f"1992-11-03T{hour:02d}:00:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542
            )
            verdicts[hour] = is_day_chart(
                chart.bodies["sun"], chart.angles["ascendant"].longitude
            )
        for hour in (8, 10, 12, 14, 16):
            with self.subTest(hour=hour):
                self.assertTrue(verdicts[hour])
        for hour in (0, 2, 4, 18, 20, 22):
            with self.subTest(hour=hour):
                self.assertFalse(verdicts[hour])

    def test_a_day_chart_publishes_no_alternative(self) -> None:
        """Both conventions agree by day, so there is nothing to disclose."""
        lot = self.engine.natal(*DAY).points["part_of_fortune"]
        self.assertIsNone(lot.alternative_longitude)
        self.assertEqual(lot.method, "ascendant_plus_moon_minus_sun")

    def test_a_night_chart_publishes_what_the_other_school_would_give(self) -> None:
        chart = self.engine.natal(*NIGHT)
        lot = chart.points["part_of_fortune"]
        self.assertEqual(lot.method, "ascendant_plus_sun_minus_moon")
        self.assertIsNotNone(lot.alternative_longitude)
        self.assertIn(
            "PART_OF_FORTUNE_SECT_CONVENTION", {w.code for w in chart.warnings}
        )

    def test_the_two_night_conventions_reflect_about_the_ascendant(self) -> None:
        """Not an arbitrary difference: they are mirror images in the horizon."""
        chart = self.engine.natal(*NIGHT)
        lot = chart.points["part_of_fortune"]
        assert lot.alternative_longitude is not None
        ascendant = chart.angles["ascendant"].longitude
        midpoint = (lot.longitude + lot.alternative_longitude) / 2.0
        self.assertAlmostEqual(
            normalize_longitude(midpoint - ascendant) % 180.0, 0.0, places=9
        )

    def test_the_non_reversing_profile_uses_one_formula_always(self) -> None:
        """Ptolemy and Lilly. The engine offers it rather than deciding for them."""
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        import dataclasses

        from gbc_astro.profiles.defaults import WESTERN_MODERN_V1

        traditional = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
            profile=dataclasses.replace(WESTERN_MODERN_V1, points="traditional"),
        )
        night = traditional.natal(*NIGHT).points["part_of_fortune"]
        self.assertEqual(night.method, "ascendant_plus_moon_minus_sun")
        self.assertEqual(
            night.longitude,
            self.engine.natal(*NIGHT).points["part_of_fortune"].alternative_longitude,
        )

    def test_the_two_profiles_agree_on_a_day_chart(self) -> None:
        import dataclasses

        from gbc_astro.profiles.defaults import WESTERN_MODERN_V1

        path = os.environ["GBC_SWISS_EPHE_PATH"]
        traditional = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
            profile=dataclasses.replace(WESTERN_MODERN_V1, points="traditional"),
        )
        self.assertAlmostEqual(
            traditional.natal(*DAY).points["part_of_fortune"].longitude,
            self.engine.natal(*DAY).points["part_of_fortune"].longitude,
            places=9,
        )

    def test_an_unknown_point_profile_is_refused(self) -> None:
        from gbc_astro.errors import InvalidCalculationProfileError

        with self.assertRaises(InvalidCalculationProfileError):
            resolve_point_profile("hellenistic-lots")

    def test_the_traditional_profile_states_its_sect_rule(self) -> None:
        self.assertEqual(
            TRADITIONAL_POINTS_V1.part_of_fortune_sect, "day_formula_always"
        )


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class ZodiacTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        provider = SwissEphemerisProvider(ephemeris_path=path)
        houses = SwissHouseCalculator(ephemeris_path=path)
        self.tropical = AstrologyEngine(provider=provider, house_calculator=houses)
        self.sidereal = AstrologyEngine(
            provider=provider, house_calculator=houses, profile=VEDIC_SIDEREAL_V1
        )

    def test_every_point_rotates_by_exactly_the_ayanamsa(self) -> None:
        """The vertex is rotated upstream; the Lot and node cancel it through.

        Two different mechanisms, one required result. A double rotation would
        show here as twice the ayanamsa, and a missing one as zero.
        """
        tropical = self.tropical.natal(*DAY)
        sidereal = self.sidereal.natal(*DAY)
        ayanamsa = sidereal.meta.ayanamsa_degrees
        assert ayanamsa is not None

        self.assertEqual(set(tropical.points), set(sidereal.points))
        for point_id, point in tropical.points.items():
            with self.subTest(point=point_id):
                self.assertAlmostEqual(
                    normalize_longitude(
                        point.longitude - sidereal.points[point_id].longitude
                    ),
                    ayanamsa,
                    places=9,
                )

    def test_the_antivertex_stays_opposite_the_vertex(self) -> None:
        for chart in (self.tropical.natal(*DAY), self.sidereal.natal(*DAY)):
            with self.subTest(zodiac=chart.meta.zodiac):
                self.assertAlmostEqual(
                    normalize_longitude(
                        chart.points["antivertex"].longitude
                        - chart.points["vertex"].longitude
                    ),
                    180.0,
                    places=9,
                )

    def test_the_south_node_stays_opposite_the_north(self) -> None:
        chart = self.tropical.natal(*DAY)
        self.assertAlmostEqual(
            normalize_longitude(
                chart.points["south_node"].longitude
                - chart.bodies["true_node"].longitude
            ),
            180.0,
            places=9,
        )


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class AvailabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )

    def test_only_the_south_node_survives_an_unknown_birth_time(self) -> None:
        """The other three need an Ascendant. Nothing is substituted."""
        chart = self.engine.natal(
            "1992-11-03", "Asia/Ho_Chi_Minh", 21.0285, 105.8542, unknown_time=True
        )
        self.assertEqual(set(chart.points), {"south_node"})
        self.assertFalse(chart.points["south_node"].requires_birth_time)

    def test_a_low_latitude_chart_is_warned_about_the_vertex(self) -> None:
        """Stable at the poles, fragile at the equator -- the opposite of Placidus."""
        chart = self.engine.natal("1992-11-03T14:35:00", "UTC", 3.0, 101.0)
        self.assertIn(
            "VERTEX_LOW_LATITUDE_SENSITIVITY", {w.code for w in chart.warnings}
        )

    def test_a_mid_latitude_chart_is_not(self) -> None:
        chart = self.engine.natal(*DAY)
        self.assertNotIn(
            "VERTEX_LOW_LATITUDE_SENSITIVITY", {w.code for w in chart.warnings}
        )

    def test_the_vertex_survives_beyond_the_polar_circle(self) -> None:
        chart = self.engine.natal(
            "1985-06-12T03:40:00", "Europe/Oslo", 69.6492, 18.9553, house_system="whole_sign"
        )
        self.assertIn("vertex", chart.points)


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class RelocationTests(unittest.TestCase):
    """A relocated chart used to contradict itself."""

    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.natal = self.engine.natal(*DAY)
        self.relocated = self.engine.relocate(self.natal, 51.5074, -0.1278)

    def test_the_relocated_chart_agrees_with_its_own_angles(self) -> None:
        """It reported a Scorpio Ascendant beside a Pisces rising sign."""
        self.assertEqual(
            self.relocated.derived.big_three["rising"],
            self.relocated.angles["ascendant"].sign,
        )

    def test_the_house_rulers_describe_the_relocated_cusps(self) -> None:
        for ruler in self.relocated.derived.house_rulers:
            with self.subTest(house=ruler.house):
                self.assertEqual(
                    ruler.cusp_sign, self.relocated.houses[ruler.house - 1].sign
                )

    def test_the_chart_ruler_rules_the_relocated_rising_sign(self) -> None:
        from gbc_astro.profiles.rulership import resolve_rulership_profile

        profile = resolve_rulership_profile(self.engine.profile.rulership)
        assert self.relocated.derived.chart_ruler is not None
        self.assertEqual(
            self.relocated.derived.chart_ruler.body_id,
            profile.domicile[self.relocated.angles["ascendant"].sign],
        )

    def test_horizon_points_move_with_the_horizon(self) -> None:
        for point_id in ("vertex", "antivertex", "part_of_fortune"):
            with self.subTest(point=point_id):
                self.assertNotAlmostEqual(
                    self.natal.points[point_id].longitude,
                    self.relocated.points[point_id].longitude,
                    places=3,
                )

    def test_the_south_node_does_not(self) -> None:
        """It depends on the instant, not the place."""
        self.assertAlmostEqual(
            self.natal.points["south_node"].longitude,
            self.relocated.points["south_node"].longitude,
            places=9,
        )
