from __future__ import annotations

import unittest

from gbc_astro.derived.balances import (
    element_counts,
    hemisphere_counts,
    modality_counts,
    polarity_counts,
    quadrant_counts,
)
from gbc_astro.derived.moon_phase import calculate_moon_phase
from gbc_astro.models.position import BodyPosition


def body(body_id: str, longitude: float, sign: str, house: int | None = None) -> BodyPosition:
    return BodyPosition(
        body_id=body_id,
        longitude=longitude,
        latitude=0.0,
        distance=None,
        speed_longitude=1.0,
        retrograde=False,
        sign=sign,
        degree_in_sign=longitude % 30,
        house=house,
    )


class DerivedTests(unittest.TestCase):
    def test_moon_phase(self) -> None:
        phase = calculate_moon_phase(body("sun", 10.0, "aries"), body("moon", 190.0, "libra"))
        self.assertEqual(phase.name, "full")
        self.assertEqual(phase.phase_angle, 180.0)
        self.assertFalse(phase.waxing)

    def test_balance_counts(self) -> None:
        bodies = {
            "sun": body("sun", 10.0, "aries"),
            "moon": body("moon", 40.0, "taurus"),
            "mercury": body("mercury", 70.0, "gemini"),
        }
        selected = ("sun", "moon", "mercury")
        self.assertEqual(
            element_counts(bodies, selected),
            {"fire": 1, "earth": 1, "air": 1, "water": 0},
        )
        self.assertEqual(
            modality_counts(bodies, selected),
            {"cardinal": 1, "fixed": 1, "mutable": 1},
        )
        self.assertEqual(polarity_counts(bodies, selected), {"positive": 2, "negative": 1})

    def test_hemisphere_and_quadrant_counts(self) -> None:
        bodies = {
            "sun": body("sun", 10.0, "aries", house=1),
            "moon": body("moon", 40.0, "taurus", house=7),
            "mercury": body("mercury", 70.0, "gemini", house=10),
        }
        selected = ("sun", "moon", "mercury")
        self.assertEqual(
            hemisphere_counts(bodies, selected),
            {"above_horizon": 2, "below_horizon": 1, "eastern": 2, "western": 1},
        )
        self.assertEqual(quadrant_counts(bodies, selected), {"q1": 1, "q2": 0, "q3": 1, "q4": 1})


if __name__ == "__main__":
    unittest.main()
