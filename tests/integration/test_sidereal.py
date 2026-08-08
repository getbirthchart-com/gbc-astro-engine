"""Sidereal zodiac tests.

The central claim is that a sidereal chart is a tropical chart rotated by the
ayanamsa, and nothing more. That makes it testable in a way most astrology is
not: every relationship between points must survive the rotation exactly, and
only the labels may change.
"""

from __future__ import annotations

import os
import unittest
from dataclasses import replace

from gbc_astro import AstrologyEngine
from gbc_astro.astronomy.circular import normalize_longitude, shortest_angular_distance
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.ayanamsa import AYANAMSA_PROFILES
from gbc_astro.profiles.defaults import VEDIC_SIDEREAL_V1, WESTERN_MODERN_V1
from gbc_astro.providers.swiss import SwissEphemerisProvider
from gbc_astro.zodiac.sidereal import longitude_to_sidereal, resolve_ayanamsa_profile

BIRTH = ("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


class AyanamsaProfileTests(unittest.TestCase):
    def test_every_profile_is_versioned_and_described(self) -> None:
        for profile_id, profile in AYANAMSA_PROFILES.items():
            with self.subTest(ayanamsa=profile_id):
                self.assertEqual(profile.id, profile_id)
                self.assertTrue(profile.version)
                self.assertTrue(profile.description)
                self.assertTrue(profile.swisseph_mode.startswith("SIDM_"))

    def test_the_schools_disagree_by_more_than_a_sign_boundary(self) -> None:
        """The reason no default is substituted: 2.3 degrees moves planets."""
        from gbc_astro.validation.ayanamsa import observed_spread_degrees

        self.assertGreater(observed_spread_degrees(), 2.0)

    def test_an_unknown_ayanamsa_is_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError):
            resolve_ayanamsa_profile("not_an_ayanamsa")

    def test_a_sidereal_profile_without_an_ayanamsa_is_refused_at_construction(self) -> None:
        """Fail when the engine is built, not on the first chart."""
        broken = replace(VEDIC_SIDEREAL_V1, id="broken-sidereal", ayanamsa=None)
        with self.assertRaises(InvalidCalculationProfileError):
            AstrologyEngine(profile=broken)

    def test_an_unsupported_zodiac_is_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError):
            AstrologyEngine(profile=replace(WESTERN_MODERN_V1, zodiac="draconic"))


class SiderealMappingTests(unittest.TestCase):
    """Pure rotation arithmetic, no ephemeris involved."""

    def test_rotation_subtracts_the_ayanamsa(self) -> None:
        self.assertAlmostEqual(longitude_to_sidereal(100.0, 24.0).longitude, 76.0, places=9)

    def test_rotation_wraps_below_zero_aries(self) -> None:
        """10 degrees Aries minus a 24 degree ayanamsa is late Pisces, not negative."""
        result = longitude_to_sidereal(10.0, 24.0)
        self.assertAlmostEqual(result.longitude, 346.0, places=9)
        self.assertEqual(result.sign, "pisces")
        self.assertAlmostEqual(result.degree_in_sign, 16.0, places=9)

    def test_sign_and_degree_stay_consistent(self) -> None:
        for longitude in (0.0, 29.999, 30.0, 180.0, 359.9):
            with self.subTest(longitude=longitude):
                result = longitude_to_sidereal(longitude, 23.85)
                expected = normalize_longitude(longitude - 23.85)
                self.assertAlmostEqual(result.longitude, expected, places=9)
                self.assertAlmostEqual(
                    result.degree_in_sign, expected % 30.0, places=9
                )

    def test_a_zero_ayanamsa_is_the_tropical_zodiac(self) -> None:
        from gbc_astro.zodiac.tropical import longitude_to_tropical

        for longitude in (0.0, 47.5, 200.25, 359.99):
            with self.subTest(longitude=longitude):
                self.assertEqual(
                    longitude_to_sidereal(longitude, 0.0), longitude_to_tropical(longitude)
                )


@unittest.skipUnless(_swiss_available(), "Sidereal charts need Swiss Ephemeris data")
class SiderealChartTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.provider = SwissEphemerisProvider(ephemeris_path=path)
        self.houses = SwissHouseCalculator(ephemeris_path=path)
        # Same house system on both sides, so only the zodiac differs.
        self.tropical = AstrologyEngine(
            provider=self.provider, house_calculator=self.houses, profile=WESTERN_MODERN_V1
        ).natal(*BIRTH)
        self.sidereal = AstrologyEngine(
            provider=self.provider,
            house_calculator=self.houses,
            profile=replace(VEDIC_SIDEREAL_V1, id="test-sid", house_system="placidus"),
        ).natal(*BIRTH)

    def test_provenance_records_which_ayanamsa_and_its_value(self) -> None:
        meta = self.sidereal.meta
        self.assertEqual(meta.zodiac, "sidereal")
        self.assertEqual(meta.ayanamsa, "lahiri")
        self.assertEqual(meta.ayanamsa_version, "1.0.0")
        assert meta.ayanamsa_degrees is not None
        self.assertGreater(meta.ayanamsa_degrees, 23.0)
        self.assertLess(meta.ayanamsa_degrees, 25.0)

        payload = self.sidereal.to_dict()["meta"]
        self.assertIn("ayanamsaDegrees", payload)

    def test_a_tropical_chart_carries_no_ayanamsa_fields(self) -> None:
        self.assertNotIn("ayanamsa", self.tropical.to_dict()["meta"])
        self.assertIsNone(self.tropical.meta.ayanamsa)

    def test_every_body_rotates_by_exactly_the_same_ayanamsa(self) -> None:
        ayanamsa = self.sidereal.meta.ayanamsa_degrees
        assert ayanamsa is not None
        for body_id, body in self.tropical.bodies.items():
            with self.subTest(body=body_id):
                self.assertAlmostEqual(
                    shortest_angular_distance(
                        normalize_longitude(body.longitude - ayanamsa),
                        self.sidereal.bodies[body_id].longitude,
                    ),
                    0.0,
                    places=9,
                )

    def test_angles_and_cusps_rotate_with_the_bodies(self) -> None:
        ayanamsa = self.sidereal.meta.ayanamsa_degrees
        assert ayanamsa is not None
        for name, angle in self.tropical.angles.items():
            with self.subTest(angle=name):
                self.assertAlmostEqual(
                    shortest_angular_distance(
                        normalize_longitude(angle.longitude - ayanamsa),
                        self.sidereal.angles[name].longitude,
                    ),
                    0.0,
                    places=9,
                )
        for index, cusp in enumerate(self.tropical.houses):
            with self.subTest(cusp=index + 1):
                self.assertAlmostEqual(
                    shortest_angular_distance(
                        normalize_longitude(cusp.cusp_longitude - ayanamsa),
                        self.sidereal.houses[index].cusp_longitude,
                    ),
                    0.0,
                    places=9,
                )

    def test_house_assignments_are_invariant(self) -> None:
        """A house is a relation between two longitudes that shift together."""
        for body_id, body in self.tropical.bodies.items():
            self.assertEqual(body.house, self.sidereal.bodies[body_id].house, body_id)

    def test_aspects_are_invariant(self) -> None:
        """Angular separations do not care which zodiac labels them."""
        self.assertEqual(len(self.tropical.aspects), len(self.sidereal.aspects))
        self.assertEqual(
            sorted(round(a.orb, 9) for a in self.tropical.aspects),
            sorted(round(a.orb, 9) for a in self.sidereal.aspects),
        )

    def test_speed_latitude_and_retrograde_are_untouched(self) -> None:
        for body_id, body in self.tropical.bodies.items():
            with self.subTest(body=body_id):
                other = self.sidereal.bodies[body_id]
                self.assertEqual(body.retrograde, other.retrograde)
                self.assertEqual(body.speed_longitude, other.speed_longitude)
                self.assertEqual(body.latitude, other.latitude)

    def test_signs_actually_differ_so_the_test_is_not_vacuous(self) -> None:
        differing = [
            body_id
            for body_id, body in self.tropical.bodies.items()
            if body.sign != self.sidereal.bodies[body_id].sign
        ]
        self.assertGreater(len(differing), 5)

    def test_choice_of_ayanamsa_changes_the_chart(self) -> None:
        """Raman and Lahiri differ by 1.4 degrees, which moves planets."""
        raman = AstrologyEngine(
            provider=self.provider,
            house_calculator=self.houses,
            profile=replace(
                VEDIC_SIDEREAL_V1, id="test-raman", house_system="placidus", ayanamsa="raman"
            ),
        ).natal(*BIRTH)

        assert self.sidereal.meta.ayanamsa_degrees is not None
        assert raman.meta.ayanamsa_degrees is not None
        self.assertGreater(
            abs(self.sidereal.meta.ayanamsa_degrees - raman.meta.ayanamsa_degrees), 1.0
        )

    def test_sidereal_charts_are_deterministic(self) -> None:
        engine = AstrologyEngine(
            provider=self.provider, house_calculator=self.houses, profile=VEDIC_SIDEREAL_V1
        )
        self.assertEqual(engine.natal(*BIRTH).to_json(), engine.natal(*BIRTH).to_json())

    def test_unknown_time_still_works_and_omits_angles(self) -> None:
        chart = AstrologyEngine(
            provider=self.provider, house_calculator=self.houses, profile=VEDIC_SIDEREAL_V1
        ).natal("1992-11-03", "Asia/Ho_Chi_Minh", 21.0285, 105.8542, unknown_time=True)

        self.assertEqual(chart.angles, {})
        self.assertEqual(chart.houses, ())
        self.assertTrue(chart.bodies)
        self.assertEqual(chart.meta.ayanamsa, "lahiri")


@unittest.skipUnless(_swiss_available(), "Sidereal houses need Swiss Ephemeris data")
class SignAnchoredHouseTests(unittest.TestCase):
    """Regression: Whole Sign cusps are not equivariant under a zodiac rotation.

    The first implementation computed Whole Sign cusps from the tropical
    Ascendant and then rotated the whole chart by the ayanamsa. Rotating a cusp
    that is defined as "the start of a sign" moves it off the sign boundary:
    every cusp landed at 6.2429 degrees instead of 0. House assignments were
    wrong with them.

    Whole Sign is the default of the Vedic profile, so this was wrong on every
    sidereal chart the engine produced. The existing suite did not catch it
    because it asserted rotation-invariance -- true for quadrant systems,
    exactly false for sign-anchored ones.
    """

    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.provider = SwissEphemerisProvider(ephemeris_path=path)
        self.houses = SwissHouseCalculator(ephemeris_path=path)

    def _chart(self, system: str, sidereal: bool = True):
        profile = (
            replace(VEDIC_SIDEREAL_V1, id=f"t-{system}", house_system=system)
            if sidereal
            else replace(WESTERN_MODERN_V1, id=f"t-{system}", house_system=system)
        )
        return AstrologyEngine(
            provider=self.provider, house_calculator=self.houses, profile=profile
        ).natal(*BIRTH)

    def test_sidereal_whole_sign_cusps_sit_on_sign_boundaries(self) -> None:
        chart = self._chart("whole_sign")
        for cusp in chart.houses:
            with self.subTest(house=cusp.number):
                self.assertAlmostEqual(cusp.degree_in_sign, 0.0, places=9)

    def test_the_first_house_is_the_sign_holding_the_sidereal_ascendant(self) -> None:
        chart = self._chart("whole_sign")
        self.assertEqual(chart.houses[0].sign, chart.angles["ascendant"].sign)

    def test_whole_sign_house_assignments_follow_the_sidereal_signs(self) -> None:
        """Each body's house is its sign's distance from the first house."""
        from gbc_astro.constants import SIGN_IDS

        chart = self._chart("whole_sign")
        first = SIGN_IDS.index(chart.houses[0].sign)
        for body_id, body in chart.bodies.items():
            with self.subTest(body=body_id):
                expected = (SIGN_IDS.index(body.sign) - first) % 12 + 1
                self.assertEqual(body.house, expected)

    def test_cusps_come_from_the_sidereal_ascendant_not_the_rotated_tropical_ones(
        self,
    ) -> None:
        """The precise statement of the fix.

        Under the bug the cusps were the tropical whole-sign set rotated by the
        ayanamsa; correct is the whole-sign set built from the sidereal
        Ascendant. Those differ by the ayanamsa's fractional part, so comparing
        against both distinguishes them unambiguously.

        House *numbers* are not a reliable canary: on this chart the ayanamsa
        moves the Ascendant and every body back by exactly one sign, so the
        relative sign distances -- and therefore the house numbers -- happen to
        be unchanged. That is a coincidence of this chart, not a rule.
        """
        from gbc_astro.houses.whole_sign import whole_sign_cusp_longitudes

        sidereal = self._chart("whole_sign")
        tropical = self._chart("whole_sign", sidereal=False)
        ayanamsa = sidereal.meta.ayanamsa_degrees
        assert ayanamsa is not None

        correct = whole_sign_cusp_longitudes(sidereal.angles["ascendant"].longitude)
        buggy = tuple(
            normalize_longitude(cusp.cusp_longitude - ayanamsa)
            for cusp in tropical.houses
        )
        actual = tuple(cusp.cusp_longitude for cusp in sidereal.houses)

        for index in range(12):
            with self.subTest(house=index + 1):
                self.assertAlmostEqual(actual[index], correct[index], places=9)
        self.assertNotAlmostEqual(actual[0], buggy[0], places=6)

    def test_equal_houses_stay_anchored_to_the_ascendant(self) -> None:
        """Equal is ASC + 30k, which does rotate correctly. Confirm, don't assume."""
        chart = self._chart("equal")
        self.assertAlmostEqual(
            shortest_angular_distance(
                chart.houses[0].cusp_longitude, chart.angles["ascendant"].longitude
            ),
            0.0,
            places=9,
        )

    def test_quadrant_cusps_still_track_the_angles(self) -> None:
        chart = self._chart("placidus")
        self.assertAlmostEqual(
            shortest_angular_distance(
                chart.houses[0].cusp_longitude, chart.angles["ascendant"].longitude
            ),
            0.0,
            places=9,
        )
        self.assertAlmostEqual(
            shortest_angular_distance(
                chart.houses[9].cusp_longitude, chart.angles["mc"].longitude
            ),
            0.0,
            places=9,
        )


@unittest.skipUnless(_swiss_available(), "Sidereal relocation needs Swiss Ephemeris data")
class SiderealRelocationTests(unittest.TestCase):
    """Regression: relocation recalculated geometry without applying the ayanamsa.

    The house calculator always works tropically. A relocated sidereal chart came
    back with sidereal bodies against tropical angles -- incoherent by the whole
    ayanamsa, 23.76 degrees, while `meta` still reported zodiac "sidereal" and
    the ayanamsa it had supposedly used.
    """

    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.sidereal = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
            profile=VEDIC_SIDEREAL_V1,
        )
        self.tropical = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )

    def test_relocated_angles_are_offset_by_the_ayanamsa(self) -> None:
        sidereal = self.sidereal.relocate(self.sidereal.natal(*BIRTH), 51.5074, -0.1278)
        tropical = self.tropical.relocate(self.tropical.natal(*BIRTH), 51.5074, -0.1278)

        ayanamsa = sidereal.meta.ayanamsa_degrees
        assert ayanamsa is not None
        for name, angle in tropical.angles.items():
            with self.subTest(angle=name):
                self.assertAlmostEqual(
                    shortest_angular_distance(
                        normalize_longitude(angle.longitude - ayanamsa),
                        sidereal.angles[name].longitude,
                    ),
                    0.0,
                    places=9,
                )

    def test_relocated_whole_sign_cusps_stay_on_sign_boundaries(self) -> None:
        relocated = self.sidereal.relocate(self.sidereal.natal(*BIRTH), 51.5074, -0.1278)
        for cusp in relocated.houses:
            with self.subTest(house=cusp.number):
                self.assertAlmostEqual(cusp.degree_in_sign, 0.0, places=9)
        self.assertEqual(relocated.houses[0].sign, relocated.angles["ascendant"].sign)

    def test_bodies_are_untouched_by_relocation(self) -> None:
        natal = self.sidereal.natal(*BIRTH)
        relocated = self.sidereal.relocate(natal, 51.5074, -0.1278)
        for body_id, body in natal.bodies.items():
            self.assertEqual(relocated.bodies[body_id].longitude, body.longitude, body_id)

    def test_the_relocated_chart_still_declares_its_ayanamsa(self) -> None:
        relocated = self.sidereal.relocate(self.sidereal.natal(*BIRTH), 51.5074, -0.1278)
        self.assertEqual(relocated.meta.zodiac, "sidereal")
        self.assertEqual(relocated.meta.ayanamsa, "lahiri")
        self.assertIsNotNone(relocated.meta.ayanamsa_degrees)
