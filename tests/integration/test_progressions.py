"""Secondary progression and solar arc tests.

The mapping is symbolic but exact: age zero must be the birth instant itself and
age one must be birth plus exactly one day. Those are assertions, not
approximations, and they are what separates a progression from a guess.
"""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone

from gbc_astro import AstrologyEngine
from gbc_astro.astronomy.circular import normalize_longitude, shortest_angular_distance
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.progression import (
    JULIAN_YEAR_DAYS,
    SECONDARY_PROGRESSION_V1,
    SOLAR_ARC_V1,
    TROPICAL_YEAR_DAYS,
)
from gbc_astro.providers.swiss import SwissEphemerisProvider
from gbc_astro.transforms.progressions import progressed_instant

BIRTH = ("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


class ProgressionProfileTests(unittest.TestCase):
    def test_both_profiles_are_versioned_and_name_their_year(self) -> None:
        for profile in (SECONDARY_PROGRESSION_V1, SOLAR_ARC_V1):
            with self.subTest(profile=profile.id):
                self.assertTrue(profile.version)
                self.assertEqual(profile.year_length_days, TROPICAL_YEAR_DAYS)
                self.assertEqual(profile.year_length_name, "tropical")
                self.assertTrue(profile.angle_method)
                self.assertTrue(profile.rationale)

    def test_the_year_length_choice_is_declared_but_immaterial(self) -> None:
        """It changes the answer, but by minutes per century -- so say so, precisely.

        The profile records the value for reproducibility, not because tropical
        versus Julian changes a reading: over a hundred years of life the two
        progressed instants differ by about three minutes, some eight arcseconds
        of progressed Sun.
        """
        from dataclasses import replace

        birth = datetime(1992, 11, 3, tzinfo=timezone.utc)
        target = birth + timedelta(days=100 * TROPICAL_YEAR_DAYS)
        tropical, _ = progressed_instant(birth, target, SECONDARY_PROGRESSION_V1)
        julian, _ = progressed_instant(
            birth,
            target,
            replace(
                SECONDARY_PROGRESSION_V1,
                id="julian",
                year_length_days=JULIAN_YEAR_DAYS,
                year_length_name="julian",
            ),
        )

        difference_minutes = abs((tropical - julian).total_seconds()) / 60.0
        self.assertGreater(difference_minutes, 0.0, "the choice does change the answer")
        self.assertLess(difference_minutes, 10.0, "but only by minutes per century")


class ProgressedInstantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.birth = datetime(1992, 11, 3, 7, 35, tzinfo=timezone.utc)

    def test_age_zero_is_the_birth_instant_itself(self) -> None:
        instant, years = progressed_instant(
            self.birth, self.birth, SECONDARY_PROGRESSION_V1
        )
        self.assertEqual(instant, self.birth)
        self.assertEqual(years, 0.0)

    def test_one_year_of_life_is_exactly_one_day(self) -> None:
        target = self.birth + timedelta(days=TROPICAL_YEAR_DAYS)
        instant, years = progressed_instant(self.birth, target, SECONDARY_PROGRESSION_V1)
        self.assertAlmostEqual(years, 1.0, places=9)
        self.assertAlmostEqual(
            (instant - self.birth).total_seconds() / 86400.0, 1.0, places=9
        )

    def test_the_mapping_is_linear(self) -> None:
        for age in (0.5, 5.0, 33.5, 80.0):
            with self.subTest(age=age):
                target = self.birth + timedelta(days=age * TROPICAL_YEAR_DAYS)
                instant, years = progressed_instant(
                    self.birth, target, SECONDARY_PROGRESSION_V1
                )
                self.assertAlmostEqual(years, age, places=9)
                self.assertAlmostEqual(
                    (instant - self.birth).total_seconds() / 86400.0, age, places=9
                )

    def test_a_date_before_birth_progresses_backwards(self) -> None:
        target = self.birth - timedelta(days=10 * TROPICAL_YEAR_DAYS)
        instant, years = progressed_instant(self.birth, target, SECONDARY_PROGRESSION_V1)
        self.assertAlmostEqual(years, -10.0, places=9)
        self.assertLess(instant, self.birth)


@unittest.skipUnless(_swiss_available(), "Progressions need Swiss Ephemeris data")
class ProgressedChartTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.natal = self.engine.natal(*BIRTH)
        self.birth = datetime.fromisoformat(
            self.natal.subject.utc_datetime.replace("Z", "+00:00")
        )

    def _at_age(self, years: float) -> datetime:
        return self.birth + timedelta(days=years * TROPICAL_YEAR_DAYS)

    def test_the_chart_at_age_zero_is_the_natal_chart(self) -> None:
        progressed = self.engine.progressions(self.natal, self._at_age(0.0))
        for body_id, body in self.natal.bodies.items():
            with self.subTest(body=body_id):
                self.assertAlmostEqual(
                    progressed.bodies[body_id].longitude, body.longitude, places=6
                )

    def test_the_progressed_chart_is_a_real_chart(self) -> None:
        """Real positions, real speeds, real houses; only the mapping is symbolic."""
        progressed = self.engine.progressions(self.natal, self._at_age(30.0))
        for body in progressed.bodies.values():
            self.assertIsNotNone(body.speed_longitude)
            self.assertIsNotNone(body.retrograde)
        self.assertTrue(progressed.angles)
        self.assertIn(
            "PROGRESSED_CHART_IS_A_REAL_CHART",
            {warning.code for warning in progressed.warnings},
        )

    def test_provenance_records_both_instants_and_the_profile(self) -> None:
        target = self._at_age(30.0)
        progressed = self.engine.progressions(self.natal, target)
        self.assertAlmostEqual(float(progressed.meta["elapsedYears"]), 30.0, places=6)
        self.assertEqual(
            progressed.meta["progressionProfile"]["yearLength"], "tropical"
        )
        self.assertTrue(progressed.meta["progressedInstant"])
        self.assertTrue(progressed.meta["targetInstant"])

    def test_an_unknown_birth_time_is_refused(self) -> None:
        unknown = self.engine.natal(
            "1992-11-03", "Asia/Ho_Chi_Minh", 21.0285, 105.8542, unknown_time=True
        )
        with self.assertRaises(InvalidCalculationProfileError):
            self.engine.progressions(unknown, self._at_age(30.0))

    def test_a_naive_target_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.progressions(self.natal, datetime(2022, 1, 1))


@unittest.skipUnless(_swiss_available(), "Solar arc needs Swiss Ephemeris data")
class SolarArcTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.natal = self.engine.natal(*BIRTH)
        self.birth = datetime.fromisoformat(
            self.natal.subject.utc_datetime.replace("Z", "+00:00")
        )

    def _at_age(self, years: float) -> datetime:
        return self.birth + timedelta(days=years * TROPICAL_YEAR_DAYS)

    def test_the_arc_is_zero_at_birth(self) -> None:
        directed = self.engine.solar_arc(self.natal, self._at_age(0.0))
        self.assertAlmostEqual(float(directed.meta["solarArcDegrees"]), 0.0, places=6)

    def test_the_arc_grows_at_about_a_degree_a_year(self) -> None:
        """The Sun covers roughly one degree a day, so one degree a symbolic year."""
        for age in (1.0, 10.0, 40.0):
            with self.subTest(age=age):
                directed = self.engine.solar_arc(self.natal, self._at_age(age))
                rate = float(directed.meta["solarArcDegrees"]) / age
                self.assertGreater(rate, 0.95)
                self.assertLess(rate, 1.05)

    def test_the_arc_keeps_growing_past_a_full_circle_of_symbolism(self) -> None:
        """Unwrapped, not folded back by the shortest-arc convention."""
        early = float(self.engine.solar_arc(self.natal, self._at_age(10.0)).meta[
            "solarArcDegrees"
        ])
        late = float(self.engine.solar_arc(self.natal, self._at_age(80.0)).meta[
            "solarArcDegrees"
        ])
        self.assertGreater(late, early)
        self.assertGreater(late, 70.0)

    def test_every_point_advances_by_the_same_arc(self) -> None:
        directed = self.engine.solar_arc(self.natal, self._at_age(25.0))
        arc = float(directed.meta["solarArcDegrees"])
        for body_id, body in self.natal.bodies.items():
            with self.subTest(body=body_id):
                self.assertAlmostEqual(
                    shortest_angular_distance(
                        normalize_longitude(body.longitude + arc),
                        directed.bodies[body_id].longitude,
                    ),
                    0.0,
                    places=9,
                )

    def test_directed_aspects_are_the_natal_aspects(self) -> None:
        """Because one arc is applied to everything, this is a rotation."""
        directed = self.engine.solar_arc(self.natal, self._at_age(25.0))
        self.assertEqual(
            sorted(round(a.orb, 9) for a in self.natal.aspects),
            sorted(round(a.orb, 9) for a in directed.aspects),
        )
        self.assertIn(
            "SOLAR_ARC_IS_A_ROTATION", {w.code for w in directed.warnings}
        )

    def test_directed_points_carry_no_speed_or_houses(self) -> None:
        """A directed point is a symbolic construction, not a moving body."""
        directed = self.engine.solar_arc(self.natal, self._at_age(25.0))
        for body in directed.bodies.values():
            self.assertIsNone(body.speed_longitude)
            self.assertIsNone(body.retrograde)
            self.assertIsNone(body.house)
        self.assertIn("SOLAR_ARC_NO_HOUSES", {w.code for w in directed.warnings})

    def test_the_angles_are_directed_too(self) -> None:
        directed = self.engine.solar_arc(self.natal, self._at_age(25.0))
        arc = float(directed.meta["solarArcDegrees"])
        for name, angle in self.natal.angles.items():
            with self.subTest(angle=name):
                self.assertAlmostEqual(
                    shortest_angular_distance(
                        normalize_longitude(angle.longitude + arc),
                        directed.angles[name].longitude,
                    ),
                    0.0,
                    places=9,
                )

    def test_both_transforms_are_deterministic(self) -> None:
        target = self._at_age(25.0)
        self.assertEqual(
            self.engine.solar_arc(self.natal, target).to_json(),
            self.engine.solar_arc(self.natal, target).to_json(),
        )
        self.assertEqual(
            self.engine.progressions(self.natal, target).to_json(),
            self.engine.progressions(self.natal, target).to_json(),
        )
