"""Draconic and harmonic chart tests.

Both transforms have exact defining properties, which makes them unusually
testable: the node must land on 0 Aries, not near it, and the harmonics must
compose. Nothing here is asserted to a tolerance that hides an error.
"""

from __future__ import annotations

import os
import unittest
from dataclasses import replace

from gbc_astro import AstrologyEngine
from gbc_astro.astronomy.circular import normalize_longitude, shortest_angular_distance
from gbc_astro.errors import InvalidCalculationProfileError, UnsupportedBodyError
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.defaults import VEDIC_SIDEREAL_V1, WESTERN_MODERN_V1
from gbc_astro.providers.swiss import SwissEphemerisProvider
from gbc_astro.transforms.harmonic import MAX_HARMONIC

BIRTH = ("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


@unittest.skipUnless(_swiss_available(), "Transforms need Swiss Ephemeris data")
class TransformTestCase(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.natal = self.engine.natal(*BIRTH)


class DraconicTests(TransformTestCase):
    def test_the_node_lands_on_exactly_zero_aries(self) -> None:
        """The definition of the transform, so it holds exactly."""
        draconic = self.engine.draconic(self.natal)
        self.assertEqual(draconic.bodies["true_node"].longitude, 0.0)
        self.assertEqual(draconic.bodies["true_node"].sign, "aries")
        self.assertEqual(draconic.bodies["true_node"].degree_in_sign, 0.0)

    def test_every_point_shifts_by_the_node_longitude(self) -> None:
        draconic = self.engine.draconic(self.natal)
        offset = self.natal.bodies["true_node"].longitude
        for body_id, body in self.natal.bodies.items():
            with self.subTest(body=body_id):
                self.assertAlmostEqual(
                    shortest_angular_distance(
                        normalize_longitude(body.longitude - offset),
                        draconic.bodies[body_id].longitude,
                    ),
                    0.0,
                    places=9,
                )

    def test_aspects_and_orbs_survive_the_rotation(self) -> None:
        draconic = self.engine.draconic(self.natal)
        self.assertEqual(len(self.natal.aspects), len(draconic.aspects))
        self.assertEqual(
            sorted(round(a.orb, 9) for a in self.natal.aspects),
            sorted(round(a.orb, 9) for a in draconic.aspects),
        )

    def test_angles_rotate_with_the_bodies(self) -> None:
        draconic = self.engine.draconic(self.natal)
        offset = self.natal.bodies["true_node"].longitude
        for name, angle in self.natal.angles.items():
            with self.subTest(angle=name):
                self.assertAlmostEqual(
                    shortest_angular_distance(
                        normalize_longitude(angle.longitude - offset),
                        draconic.angles[name].longitude,
                    ),
                    0.0,
                    places=9,
                )

    def test_no_houses_are_produced(self) -> None:
        draconic = self.engine.draconic(self.natal)
        self.assertIn("DRACONIC_NO_HOUSES", {w.code for w in draconic.warnings})
        for body in draconic.bodies.values():
            self.assertIsNone(body.house)

    def test_provenance_names_the_node_it_used(self) -> None:
        draconic = self.engine.draconic(self.natal)
        self.assertEqual(draconic.transform, "draconic")
        self.assertEqual(draconic.meta["nodeBody"], "true_node")
        self.assertEqual(draconic.meta["nodeType"], "true")
        self.assertAlmostEqual(
            float(draconic.meta["nodeLongitude"]),
            self.natal.bodies["true_node"].longitude,
        )

    def test_the_mean_node_gives_a_different_chart(self) -> None:
        mean_engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=os.environ["GBC_SWISS_EPHE_PATH"]),
            house_calculator=SwissHouseCalculator(
                ephemeris_path=os.environ["GBC_SWISS_EPHE_PATH"]
            ),
            profile=replace(WESTERN_MODERN_V1, id="mean-node", node_type="mean"),
        )
        draconic = mean_engine.draconic(self.natal)
        self.assertEqual(draconic.bodies["mean_node"].longitude, 0.0)
        self.assertNotEqual(draconic.bodies["true_node"].longitude, 0.0)

    def test_an_unsupported_node_type_is_refused(self) -> None:
        broken = replace(WESTERN_MODERN_V1, id="bad-node", node_type="osculating")
        engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=os.environ["GBC_SWISS_EPHE_PATH"]),
            house_calculator=SwissHouseCalculator(
                ephemeris_path=os.environ["GBC_SWISS_EPHE_PATH"]
            ),
            profile=broken,
        )
        with self.assertRaises(UnsupportedBodyError):
            engine.draconic(self.natal)

    def test_draconic_works_on_a_sidereal_chart(self) -> None:
        engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=os.environ["GBC_SWISS_EPHE_PATH"]),
            house_calculator=SwissHouseCalculator(
                ephemeris_path=os.environ["GBC_SWISS_EPHE_PATH"]
            ),
            profile=VEDIC_SIDEREAL_V1,
        )
        draconic = engine.draconic(engine.natal(*BIRTH))
        self.assertEqual(draconic.bodies["true_node"].longitude, 0.0)
        self.assertEqual(draconic.meta["zodiac"], "sidereal")


class HarmonicTests(TransformTestCase):
    def test_the_first_harmonic_is_the_natal_chart(self) -> None:
        harmonic = self.engine.harmonic(self.natal, 1)
        for body_id, body in self.natal.bodies.items():
            with self.subTest(body=body_id):
                self.assertAlmostEqual(
                    harmonic.bodies[body_id].longitude, body.longitude, places=9
                )

    def test_longitudes_are_multiplied_modulo_the_circle(self) -> None:
        for number in (2, 3, 5, 7, 9):
            harmonic = self.engine.harmonic(self.natal, number)
            for body_id, body in self.natal.bodies.items():
                with self.subTest(harmonic=number, body=body_id):
                    self.assertAlmostEqual(
                        shortest_angular_distance(
                            normalize_longitude(body.longitude * number),
                            harmonic.bodies[body_id].longitude,
                        ),
                        0.0,
                        places=6,
                    )

    def test_harmonics_compose(self) -> None:
        """H3 of H2 is H6: the property that proves the transform is what it claims."""
        second = self.engine.harmonic(self.natal, 2)
        chained = self.engine.harmonic(replace(self.natal, bodies=second.bodies), 3)
        sixth = self.engine.harmonic(self.natal, 6)

        for body_id in self.natal.bodies:
            with self.subTest(body=body_id):
                self.assertAlmostEqual(
                    shortest_angular_distance(
                        chained.bodies[body_id].longitude, sixth.bodies[body_id].longitude
                    ),
                    0.0,
                    places=6,
                )

    def test_a_trine_becomes_a_conjunction_in_the_third_harmonic(self) -> None:
        """The reason harmonic charts exist, checked on a planted pair."""
        from gbc_astro.models.position import BodyPosition
        from gbc_astro.zodiac.tropical import longitude_to_tropical

        def planted(body_id: str, longitude: float) -> BodyPosition:
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

        chart = replace(
            self.natal,
            bodies={"sun": planted("sun", 10.0), "moon": planted("moon", 130.0)},
        )
        harmonic = self.engine.harmonic(chart, 3)
        self.assertAlmostEqual(
            shortest_angular_distance(
                harmonic.bodies["sun"].longitude, harmonic.bodies["moon"].longitude
            ),
            0.0,
            places=6,
        )

    def test_speed_is_multiplied_and_retrograde_is_not_flipped(self) -> None:
        harmonic = self.engine.harmonic(self.natal, 5)
        for body_id, body in self.natal.bodies.items():
            with self.subTest(body=body_id):
                other = harmonic.bodies[body_id]
                self.assertEqual(body.retrograde, other.retrograde)
                if body.speed_longitude is not None:
                    assert other.speed_longitude is not None
                    self.assertAlmostEqual(
                        other.speed_longitude, body.speed_longitude * 5.0, places=9
                    )

    def test_latitude_is_left_alone(self) -> None:
        """The transform is defined on longitude; multiplying latitude would invent."""
        harmonic = self.engine.harmonic(self.natal, 7)
        for body_id, body in self.natal.bodies.items():
            self.assertEqual(body.latitude, harmonic.bodies[body_id].latitude, body_id)

    def test_no_houses_and_the_reason_is_stated(self) -> None:
        harmonic = self.engine.harmonic(self.natal, 5)
        codes = {w.code for w in harmonic.warnings}
        self.assertIn("HARMONIC_NO_HOUSES", codes)
        self.assertIn("HARMONIC_ERROR_AMPLIFIED", codes)
        for body in harmonic.bodies.values():
            self.assertIsNone(body.house)

    def test_aspects_are_recomputed_not_carried_over(self) -> None:
        harmonic = self.engine.harmonic(self.natal, 5)
        self.assertNotEqual(
            sorted(round(a.orb, 6) for a in self.natal.aspects),
            sorted(round(a.orb, 6) for a in harmonic.aspects),
        )

    def test_out_of_range_harmonics_are_refused(self) -> None:
        for number in (0, -1, MAX_HARMONIC + 1):
            with self.subTest(harmonic=number), self.assertRaises(
                InvalidCalculationProfileError
            ):
                self.engine.harmonic(self.natal, number)

    def test_transforms_are_deterministic(self) -> None:
        self.assertEqual(
            self.engine.harmonic(self.natal, 5).to_json(),
            self.engine.harmonic(self.natal, 5).to_json(),
        )
        self.assertEqual(
            self.engine.draconic(self.natal).to_json(),
            self.engine.draconic(self.natal).to_json(),
        )

    def test_canonical_shape(self) -> None:
        payload = self.engine.harmonic(self.natal, 5).to_dict()
        self.assertEqual(
            set(payload),
            {
                "schemaVersion",
                "transform",
                "transformVersion",
                "meta",
                "subject",
                "bodies",
                "angles",
                "aspects",
                "warnings",
            },
        )
        self.assertEqual(payload["transform"], "harmonic-5")
