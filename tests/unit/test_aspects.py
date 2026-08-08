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


if __name__ == "__main__":
    unittest.main()
