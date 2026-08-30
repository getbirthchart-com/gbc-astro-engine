from __future__ import annotations

import unittest

from gbc_astro.aspects.engine import classify_aspect
from gbc_astro.models.position import BodyPosition
from gbc_astro.profiles.defaults import MODERN_MAJOR_V1


def body(body_id: str, longitude: float, speed: float) -> BodyPosition:
    return BodyPosition(
        body_id=body_id,
        longitude=longitude,
        latitude=0.0,
        distance=None,
        speed_longitude=speed,
        retrograde=speed < 0,
        sign="aries",
        degree_in_sign=longitude % 30,
        house=None,
    )


class AspectTests(unittest.TestCase):
    def test_classifies_major_aspect(self) -> None:
        aspect = classify_aspect(body("sun", 10.0, 1.0), body("moon", 69.0, 13.0), MODERN_MAJOR_V1)
        self.assertIsNotNone(aspect)
        assert aspect is not None
        self.assertEqual(aspect.aspect_type, "sextile")
        self.assertEqual(aspect.actual_angle, 59.0)
        self.assertEqual(aspect.orb, 1.0)
        self.assertEqual(aspect.phase, "applying")

    def test_returns_none_outside_orb(self) -> None:
        aspect = classify_aspect(body("sun", 10.0, 1.0), body("moon", 43.0, 1.0), MODERN_MAJOR_V1)
        self.assertIsNone(aspect)

    def test_exact_phase(self) -> None:
        aspect = classify_aspect(body("sun", 10.0, 1.0), body("moon", 70.0, 1.0), MODERN_MAJOR_V1)
        self.assertIsNotNone(aspect)
        assert aspect is not None
        self.assertEqual(aspect.phase, "exact")

    def test_indeterminate_phase_when_speed_missing(self) -> None:
        slow = body("sun", 10.0, 1.0)
        no_speed = BodyPosition(
            body_id="moon",
            longitude=69.0,
            latitude=0.0,
            distance=None,
            speed_longitude=None,
            retrograde=None,
            sign="gemini",
            degree_in_sign=9.0,
            house=None,
        )
        aspect = classify_aspect(slow, no_speed, MODERN_MAJOR_V1)
        self.assertIsNotNone(aspect)
        assert aspect is not None
        self.assertEqual(aspect.phase, "indeterminate")

    def test_conjunction_wraps_around_zero_longitude(self) -> None:
        aspect = classify_aspect(
            body("sun", 359.5, 1.0), body("moon", 0.5, 13.0), MODERN_MAJOR_V1
        )
        self.assertIsNotNone(aspect)
        assert aspect is not None
        self.assertEqual(aspect.aspect_type, "conjunction")
        self.assertEqual(aspect.actual_angle, 1.0)
        self.assertEqual(aspect.exact_angle, 0.0)
        self.assertEqual(aspect.orb, 1.0)

    def test_separating_phase_when_orb_widens(self) -> None:
        aspect = classify_aspect(
            body("sun", 10.0, 1.0), body("moon", 72.0, 13.0), MODERN_MAJOR_V1
        )
        self.assertIsNotNone(aspect)
        assert aspect is not None
        self.assertEqual(aspect.aspect_type, "sextile")
        self.assertEqual(aspect.phase, "separating")

    def test_extended_classifies_minor_geometry(self) -> None:
        from gbc_astro.profiles.aspects import MODERN_EXTENDED_V1

        cases = (
            (30.0, "semisextile"),
            (45.0, "semisquare"),
            (135.0, "sesquiquadrate"),
            (150.0, "quincunx"),
        )
        for angle, name in cases:
            with self.subTest(aspect=name):
                aspect = classify_aspect(
                    body("sun", 0.0, 1.0), body("moon", angle, 13.0), MODERN_EXTENDED_V1
                )
                self.assertIsNotNone(aspect)
                assert aspect is not None
                self.assertEqual(aspect.aspect_type, name)
                self.assertEqual(aspect.exact_angle, angle)
                self.assertEqual(aspect.actual_angle, angle)
                self.assertIsNone(
                    classify_aspect(
                        body("sun", 0.0, 1.0), body("moon", angle, 13.0), MODERN_MAJOR_V1
                    )
                )

    def test_custom_orb_includes_the_boundary_and_excludes_just_outside(self) -> None:
        from gbc_astro.profiles.aspects import custom_aspect_profile, normalize_custom_aspect_rules

        profile = custom_aspect_profile(
            normalize_custom_aspect_rules(
                [{"type": "conjunction", "exact_angle": 0, "orb": 6}]
            )
        )
        included = classify_aspect(
            body("sun", 0.0, 1.0), body("moon", 6.0, 13.0), profile
        )
        excluded = classify_aspect(
            body("sun", 0.0, 1.0), body("moon", 6.01, 13.0), profile
        )
        self.assertIsNotNone(included)
        assert included is not None
        self.assertEqual(included.orb, 6.0)
        self.assertIsNone(excluded)


if __name__ == "__main__":
    unittest.main()
