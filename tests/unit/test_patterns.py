"""Pattern detection tests against planted configurations.

There is no external reference for "is this a grand trine", so the figures are
built by hand at exact longitudes and the detector is asked to find them. Every
positive test has a matching negative one just outside the orb, because a
detector that finds everything is worth as little as one that finds nothing.
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from gbc_astro.derived.patterns import find_patterns
from gbc_astro.models.position import BodyPosition
from gbc_astro.profiles.pattern import PATTERN_PROFILE_V1
from gbc_astro.zodiac.tropical import longitude_to_tropical


def body(body_id: str, longitude: float) -> BodyPosition:
    zodiac = longitude_to_tropical(longitude)
    return BodyPosition(
        body_id=body_id,
        longitude=zodiac.longitude,
        latitude=0.0,
        distance=None,
        speed_longitude=1.0,
        retrograde=False,
        sign=zodiac.sign,
        degree_in_sign=zodiac.degree_in_sign,
        house=None,
    )


def chart(**placements: float) -> dict[str, BodyPosition]:
    return {name: body(name, longitude) for name, longitude in placements.items()}


def types_found(bodies: dict[str, BodyPosition]) -> set[str]:
    return {pattern.pattern_type for pattern in find_patterns(bodies, PATTERN_PROFILE_V1)}


class ProfileTests(unittest.TestCase):
    def test_pattern_orbs_are_tighter_than_natal_aspect_orbs(self) -> None:
        """A three-body figure accumulates its legs' error."""
        from gbc_astro.profiles.defaults import WESTERN_MODERN_V1

        natal = {r.aspect_type: r.orb for r in WESTERN_MODERN_V1.aspect_profile.rules}
        for aspect, orb in PATTERN_PROFILE_V1.leg_orbs.items():
            if aspect in natal:
                with self.subTest(aspect=aspect):
                    self.assertLessEqual(orb, natal[aspect])

    def test_the_quincunx_is_carried_here_not_borrowed(self) -> None:
        """Yods need it and the major-aspect profile does not have it."""
        self.assertIn("quincunx", PATTERN_PROFILE_V1.leg_orbs)

    def test_only_the_ten_planets_participate(self) -> None:
        self.assertEqual(len(PATTERN_PROFILE_V1.participating_bodies), 10)
        for excluded in ("true_node", "mean_node", "chiron"):
            self.assertNotIn(excluded, PATTERN_PROFILE_V1.participating_bodies)


class GrandTrineTests(unittest.TestCase):
    def test_an_exact_grand_trine_is_found(self) -> None:
        found = find_patterns(chart(sun=0.0, moon=120.0, mars=240.0), PATTERN_PROFILE_V1)
        trines = [p for p in found if p.pattern_type == "grand_trine"]
        self.assertEqual(len(trines), 1)
        self.assertEqual(trines[0].bodies, ("mars", "moon", "sun"))
        self.assertAlmostEqual(trines[0].max_leg_orb, 0.0, places=9)

    def test_a_grand_trine_just_inside_orb_is_found(self) -> None:
        self.assertIn("grand_trine", types_found(chart(sun=0.0, moon=125.0, mars=240.0)))

    def test_a_grand_trine_just_outside_orb_is_not(self) -> None:
        self.assertNotIn(
            "grand_trine", types_found(chart(sun=0.0, moon=127.0, mars=240.0))
        )

    def test_two_trines_without_the_third_leg_are_not_a_grand_trine(self) -> None:
        self.assertNotIn(
            "grand_trine", types_found(chart(sun=0.0, moon=120.0, mars=200.0))
        )


class TSquareAndGrandCrossTests(unittest.TestCase):
    def test_an_exact_t_square_is_found_with_its_apex(self) -> None:
        found = find_patterns(chart(sun=0.0, moon=180.0, mars=90.0), PATTERN_PROFILE_V1)
        squares = [p for p in found if p.pattern_type == "t_square"]
        self.assertEqual(len(squares), 1)
        self.assertEqual(squares[0].detail["apex"], "mars")

    def test_an_opposition_without_an_apex_is_not_a_t_square(self) -> None:
        self.assertNotIn("t_square", types_found(chart(sun=0.0, moon=180.0, mars=45.0)))

    def test_an_exact_grand_cross_is_found(self) -> None:
        found = find_patterns(
            chart(sun=0.0, moon=90.0, mars=180.0, venus=270.0), PATTERN_PROFILE_V1
        )
        crosses = [p for p in found if p.pattern_type == "grand_cross"]
        self.assertEqual(len(crosses), 1)
        self.assertEqual(crosses[0].bodies, ("mars", "moon", "sun", "venus"))

    def test_a_grand_cross_suppresses_its_contained_t_squares(self) -> None:
        """Every grand cross holds two; announcing all three says it three times."""
        found = types_found(chart(sun=0.0, moon=90.0, mars=180.0, venus=270.0))
        self.assertIn("grand_cross", found)
        self.assertNotIn("t_square", found)

    def test_suppression_can_be_switched_off(self) -> None:
        loud = replace(PATTERN_PROFILE_V1, id="loud", suppress_contained_patterns=False)
        found = {
            p.pattern_type
            for p in find_patterns(
                chart(sun=0.0, moon=90.0, mars=180.0, venus=270.0), loud
            )
        }
        self.assertIn("grand_cross", found)
        self.assertIn("t_square", found)


class YodTests(unittest.TestCase):
    def test_an_exact_yod_is_found_with_its_apex(self) -> None:
        found = find_patterns(chart(sun=0.0, moon=60.0, mars=210.0), PATTERN_PROFILE_V1)
        yods = [p for p in found if p.pattern_type == "yod"]
        self.assertEqual(len(yods), 1)
        self.assertEqual(yods[0].detail["apex"], "mars")
        self.assertEqual(sorted(yods[0].detail["base"]), ["moon", "sun"])

    def test_a_yod_outside_the_tight_quincunx_orb_is_not_found(self) -> None:
        """The quincunx leg is held to three degrees, not six."""
        self.assertNotIn("yod", types_found(chart(sun=0.0, moon=60.0, mars=215.0)))

    def test_a_sextile_without_quincunxes_is_not_a_yod(self) -> None:
        self.assertNotIn("yod", types_found(chart(sun=0.0, moon=60.0, mars=180.0)))


class KiteTests(unittest.TestCase):
    def test_an_exact_kite_is_found(self) -> None:
        found = find_patterns(
            chart(sun=0.0, moon=120.0, mars=240.0, venus=180.0), PATTERN_PROFILE_V1
        )
        kites = [p for p in found if p.pattern_type == "kite"]
        self.assertEqual(len(kites), 1)
        self.assertEqual(kites[0].detail["tail"], "venus")
        self.assertEqual(kites[0].detail["opposedCorner"], "sun")

    def test_a_kite_suppresses_its_contained_grand_trine(self) -> None:
        found = types_found(chart(sun=0.0, moon=120.0, mars=240.0, venus=180.0))
        self.assertIn("kite", found)
        self.assertNotIn("grand_trine", found)


class StelliumTests(unittest.TestCase):
    def test_three_bodies_in_one_sign_make_a_stellium(self) -> None:
        found = find_patterns(
            chart(sun=5.0, moon=15.0, mercury=25.0), PATTERN_PROFILE_V1
        )
        stelliums = [p for p in found if p.pattern_type == "stellium"]
        self.assertEqual(len(stelliums), 1)
        self.assertEqual(stelliums[0].detail["sign"], "aries")
        self.assertEqual(stelliums[0].detail["bodyCount"], 3)
        self.assertAlmostEqual(float(stelliums[0].detail["spanDegrees"]), 20.0, places=9)

    def test_two_bodies_are_not_a_stellium(self) -> None:
        self.assertNotIn("stellium", types_found(chart(sun=5.0, moon=15.0)))

    def test_bodies_straddling_a_sign_boundary_are_not_one_stellium(self) -> None:
        """Grouping is by sign, which the profile declares."""
        self.assertNotIn(
            "stellium", types_found(chart(sun=28.0, moon=29.0, mercury=31.0))
        )


class OutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bodies = chart(sun=0.0, moon=120.0, mars=240.0, venus=180.0, mercury=90.0)

    def test_identifiers_are_deterministic_and_sorted(self) -> None:
        for pattern in find_patterns(self.bodies, PATTERN_PROFILE_V1):
            with self.subTest(pattern=pattern.pattern_type):
                self.assertEqual(
                    pattern.id, f"pattern.{pattern.pattern_type}." + ".".join(pattern.bodies)
                )
                self.assertEqual(list(pattern.bodies), sorted(pattern.bodies))

    def test_ordering_is_stable_across_runs(self) -> None:
        runs = {
            tuple(p.id for p in find_patterns(self.bodies, PATTERN_PROFILE_V1))
            for _ in range(5)
        }
        self.assertEqual(len(runs), 1)

    def test_every_pattern_reports_its_widest_leg(self) -> None:
        loose = chart(sun=0.0, moon=123.0, mars=238.0)
        for pattern in find_patterns(loose, PATTERN_PROFILE_V1):
            if pattern.pattern_type == "grand_trine":
                self.assertGreater(pattern.max_leg_orb, 0.0)
                self.assertLessEqual(
                    pattern.max_leg_orb, PATTERN_PROFILE_V1.leg_orbs["trine"]
                )

    def test_an_empty_chart_yields_nothing(self) -> None:
        self.assertEqual(find_patterns({}, PATTERN_PROFILE_V1), ())

    def test_non_participating_bodies_are_ignored(self) -> None:
        """A grand trine that needs the node to close is not reported."""
        bodies = chart(sun=0.0, moon=120.0)
        bodies.update({"true_node": body("true_node", 240.0)})
        self.assertNotIn("grand_trine", types_found(bodies))
