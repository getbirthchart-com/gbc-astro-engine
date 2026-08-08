"""Extended house system tests.

Eleven systems, validated at two different strengths. Placidus, Porphyry,
Meridian, Whole Sign and Equal are re-derived independently and compared
numerically; the rest are held to invariants, because claiming they are
validated when Swiss Ephemeris is the only source would be validating a thing
against itself.
"""

from __future__ import annotations

import os
import unittest
from dataclasses import replace

from gbc_astro import AstrologyEngine
from gbc_astro.astronomy.circular import shortest_angular_distance
from gbc_astro.errors import HouseCalculationUnavailableError, InvalidCalculationProfileError
from gbc_astro.houses.base import is_sequence_degenerate
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.houses.systems import HOUSE_SYSTEMS, SUPPORTED_HOUSE_SYSTEMS
from gbc_astro.profiles.defaults import WESTERN_MODERN_V1
from gbc_astro.providers.swiss import SwissEphemerisProvider

BIRTH = ("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
POLAR = ("1990-12-15T11:30:00", "Europe/Oslo", 69.6492, 18.9553)


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


class RegistryTests(unittest.TestCase):
    def test_all_eleven_systems_are_registered_and_versioned(self) -> None:
        self.assertEqual(len(HOUSE_SYSTEMS), 11)
        for system_id, profile in HOUSE_SYSTEMS.items():
            with self.subTest(system=system_id):
                self.assertEqual(profile.id, system_id)
                self.assertTrue(profile.version)
                self.assertTrue(profile.description)
                self.assertTrue(profile.swisseph_code)

    def test_the_v1_target_list_is_complete(self) -> None:
        """01_MASTER_REQUIREMENTS section 8 names these for v1.0."""
        for required in (
            "koch",
            "porphyry",
            "campanus",
            "regiomontanus",
            "alcabitius",
            "morinus",
            "meridian",
            "topocentric",
        ):
            self.assertIn(required, HOUSE_SYSTEMS)

    def test_only_placidus_and_koch_are_polar_limited(self) -> None:
        limited = {
            system for system, p in HOUSE_SYSTEMS.items() if not p.defined_at_all_latitudes
        }
        self.assertEqual(limited, {"placidus", "koch"})

    def test_morinus_and_meridian_are_not_quadrant_based(self) -> None:
        """Neither puts the Ascendant on cusp 1; the horizon plays no part."""
        self.assertFalse(HOUSE_SYSTEMS["morinus"].quadrant_based)
        self.assertFalse(HOUSE_SYSTEMS["meridian"].quadrant_based)

    def test_an_unknown_system_is_refused(self) -> None:
        engine = AstrologyEngine(profile=WESTERN_MODERN_V1)
        with self.assertRaises(InvalidCalculationProfileError):
            engine.natal(*BIRTH, house_system="vehlow")


@unittest.skipUnless(_swiss_available(), "House systems need Swiss Ephemeris data")
class HouseSystemChartTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )

    def test_every_system_produces_a_usable_chart_at_mid_latitude(self) -> None:
        for system in SUPPORTED_HOUSE_SYSTEMS:
            with self.subTest(system=system):
                chart = self.engine.natal(*BIRTH, house_system=system)
                self.assertEqual(len(chart.houses), 12)
                self.assertEqual(chart.meta.house_system, system)
                for body in chart.bodies.values():
                    self.assertIn(body.house, range(1, 13))

    def test_quadrant_systems_put_the_angles_on_cusps_one_and_ten(self) -> None:
        for system, profile in HOUSE_SYSTEMS.items():
            if not profile.quadrant_based or system == "equal":
                continue
            with self.subTest(system=system):
                chart = self.engine.natal(*BIRTH, house_system=system)
                self.assertAlmostEqual(
                    shortest_angular_distance(
                        chart.houses[0].cusp_longitude,
                        chart.angles["ascendant"].longitude,
                    ),
                    0.0,
                    places=6,
                )
                self.assertAlmostEqual(
                    shortest_angular_distance(
                        chart.houses[9].cusp_longitude, chart.angles["mc"].longitude
                    ),
                    0.0,
                    places=6,
                )

    def test_meridian_does_not_put_the_ascendant_on_cusp_one(self) -> None:
        """Confirms the registry's claim rather than assuming it."""
        chart = self.engine.natal(*BIRTH, house_system="meridian")
        self.assertGreater(
            shortest_angular_distance(
                chart.houses[0].cusp_longitude, chart.angles["ascendant"].longitude
            ),
            0.1,
        )

    def test_systems_actually_differ_from_one_another(self) -> None:
        """Otherwise every test above could pass with one system wired eleven times."""
        cusp_sets = {
            system: tuple(round(c.cusp_longitude, 4) for c in
                          self.engine.natal(*BIRTH, house_system=system).houses)
            for system in SUPPORTED_HOUSE_SYSTEMS
        }
        self.assertGreaterEqual(len(set(cusp_sets.values())), 8)

    def test_angles_are_identical_across_every_system(self) -> None:
        """Only the cusps depend on the system; the angles are the same sky."""
        reference = self.engine.natal(*BIRTH, house_system="placidus").angles
        for system in SUPPORTED_HOUSE_SYSTEMS:
            with self.subTest(system=system):
                angles = self.engine.natal(*BIRTH, house_system=system).angles
                for name, angle in reference.items():
                    self.assertAlmostEqual(
                        shortest_angular_distance(angle.longitude, angles[name].longitude),
                        0.0,
                        places=9,
                    )


@unittest.skipUnless(_swiss_available(), "House systems need Swiss Ephemeris data")
class PolarBehaviourTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.calculator = SwissHouseCalculator(ephemeris_path=path)

    def test_placidus_and_koch_refuse_beyond_the_polar_circle(self) -> None:
        for system in ("placidus", "koch"):
            with self.subTest(system=system), self.assertRaises(
                HouseCalculationUnavailableError
            ):
                self.calculator.calculate(
                    julian_day=2448256.0,
                    latitude=78.2232,
                    longitude=15.6267,
                    house_system=system,
                )

    def test_the_polar_refusal_says_why_and_names_what_does_work(self) -> None:
        """"Could not calculate" left the caller with nowhere to go."""
        with self.assertRaises(HouseCalculationUnavailableError) as raised:
            self.calculator.calculate(
                julian_day=2448256.0,
                latitude=78.2232,
                longitude=15.6267,
                house_system="placidus",
            )
        message = str(raised.exception)
        self.assertIn("polar circles", message)
        self.assertIn("78.2232", message)
        self.assertIn("whole_sign", message)
        # Naming alternatives must not shade into choosing one.
        self.assertIn("No other system was substituted", message)

    def test_inverting_systems_are_flagged_not_returned_silently(self) -> None:
        for system in ("campanus", "regiomontanus", "topocentric"):
            with self.subTest(system=system):
                chart = self.engine.natal(*POLAR, house_system=system)
                self.assertIn(
                    "HOUSE_SEQUENCE_DEGENERATE",
                    {warning.code for warning in chart.warnings},
                )

    def test_whole_sign_and_equal_stay_well_formed_at_the_pole(self) -> None:
        for system in ("whole_sign", "equal"):
            with self.subTest(system=system):
                chart = self.engine.natal(*POLAR, house_system=system)
                self.assertNotIn(
                    "HOUSE_SEQUENCE_DEGENERATE",
                    {warning.code for warning in chart.warnings},
                )
                self.assertFalse(is_sequence_degenerate(chart.houses))

    def test_no_degeneracy_at_ordinary_latitudes(self) -> None:
        for system in SUPPORTED_HOUSE_SYSTEMS:
            with self.subTest(system=system):
                chart = self.engine.natal(*BIRTH, house_system=system)
                self.assertFalse(is_sequence_degenerate(chart.houses))
                self.assertNotIn(
                    "HOUSE_SEQUENCE_DEGENERATE",
                    {warning.code for warning in chart.warnings},
                )


@unittest.skipUnless(_swiss_available(), "Parity gate needs Swiss Ephemeris data")
class ParityGateTests(unittest.TestCase):
    def test_the_gate_passes(self) -> None:
        from gbc_astro.validation.houses_parity import (
            generate_house_cases,
            run_house_system_parity,
        )

        report = run_house_system_parity(cases=generate_house_cases(24))
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["unexpectedDegeneracy"], [])
        for system, data in report["independentlyValidated"].items():
            with self.subTest(system=system):
                self.assertEqual(data["outside"], 0)
                self.assertGreater(data["compared"], 0)

    def test_sidereal_works_with_every_house_system(self) -> None:
        from gbc_astro.profiles.defaults import VEDIC_SIDEREAL_V1

        for system in SUPPORTED_HOUSE_SYSTEMS:
            if system in ("placidus", "koch"):
                continue
            with self.subTest(system=system):
                engine = AstrologyEngine(
                    provider=SwissEphemerisProvider(
                        ephemeris_path=os.environ["GBC_SWISS_EPHE_PATH"]
                    ),
                    house_calculator=SwissHouseCalculator(
                        ephemeris_path=os.environ["GBC_SWISS_EPHE_PATH"]
                    ),
                    profile=replace(VEDIC_SIDEREAL_V1, id="t", house_system=system),
                )
                chart = engine.natal(*BIRTH)
                self.assertEqual(chart.meta.zodiac, "sidereal")
                self.assertEqual(len(chart.houses), 12)
