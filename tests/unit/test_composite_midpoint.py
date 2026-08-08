"""Composite midpoint correctness, especially across 0 Aries.

The defining failure mode of a composite chart is linear averaging: the mean of
359 and 1 is 180, which is the opposite side of the zodiac from the correct
answer of 0. Every case below would pass under linear averaging only by
accident, and most would fail loudly.
"""

from __future__ import annotations

import unittest

from hypothesis import given
from hypothesis import strategies as st

from gbc_astro.astronomy.circular import (
    normalize_longitude,
    shortest_angular_distance,
    shortest_arc_midpoint,
)
from gbc_astro.relationship.composite import (
    OPPOSITION_AMBIGUITY_EPSILON_DEG,
    is_ambiguous_midpoint,
)

LONGITUDES = st.floats(min_value=0.0, max_value=360.0, allow_nan=False, allow_infinity=False)


class WrapAroundZeroAriesTests(unittest.TestCase):
    """The regression cases the v0.2 Definition of Done calls for by name."""

    def test_359_and_1_give_0_not_180(self) -> None:
        self.assertAlmostEqual(shortest_arc_midpoint(359.0, 1.0), 0.0, places=9)

    def test_1_and_359_give_0_regardless_of_order(self) -> None:
        self.assertAlmostEqual(shortest_arc_midpoint(1.0, 359.0), 0.0, places=9)

    def test_wrap_cases(self) -> None:
        cases = (
            (350.0, 10.0, 0.0),
            (10.0, 350.0, 0.0),
            (355.0, 5.0, 0.0),
            (300.0, 60.0, 0.0),
            (359.9, 0.1, 0.0),
            (330.0, 30.0, 0.0),
            (345.0, 15.0, 0.0),
            (358.0, 4.0, 1.0),
            (0.0, 0.0, 0.0),
            (359.999, 0.0, 359.9995),
        )
        for first, second, expected in cases:
            with self.subTest(first=first, second=second):
                self.assertAlmostEqual(
                    shortest_arc_midpoint(first, second), expected, places=6
                )

    def test_non_wrapping_cases_are_the_plain_average(self) -> None:
        for first, second in ((10.0, 50.0), (100.0, 140.0), (200.0, 260.0), (95.0, 96.0)):
            with self.subTest(first=first, second=second):
                self.assertAlmostEqual(
                    shortest_arc_midpoint(first, second), (first + second) / 2.0, places=9
                )


class MidpointPropertyTests(unittest.TestCase):
    @given(LONGITUDES, LONGITUDES)
    def test_midpoint_is_equidistant_from_both_inputs(self, first: float, second: float) -> None:
        midpoint = shortest_arc_midpoint(first, second)
        self.assertAlmostEqual(
            shortest_angular_distance(midpoint, first),
            shortest_angular_distance(midpoint, second),
            places=9,
        )

    @given(LONGITUDES, LONGITUDES)
    def test_midpoint_lies_on_the_shorter_arc(self, first: float, second: float) -> None:
        """Half the separation, not half the long way round."""
        midpoint = shortest_arc_midpoint(first, second)
        separation = shortest_angular_distance(first, second)
        self.assertLessEqual(shortest_angular_distance(midpoint, first), separation / 2.0 + 1e-9)

    @given(LONGITUDES, LONGITUDES)
    def test_midpoint_is_always_a_valid_longitude(self, first: float, second: float) -> None:
        midpoint = shortest_arc_midpoint(first, second)
        self.assertGreaterEqual(midpoint, 0.0)
        self.assertLess(midpoint, 360.0)

    @given(LONGITUDES, LONGITUDES)
    def test_midpoint_is_order_independent(self, first: float, second: float) -> None:
        """Except for exact oppositions, where both answers are equally valid."""
        if is_ambiguous_midpoint(first, second):
            return
        self.assertAlmostEqual(
            shortest_arc_midpoint(first, second),
            shortest_arc_midpoint(second, first),
            places=9,
        )

    @given(LONGITUDES, st.floats(min_value=-720.0, max_value=720.0))
    def test_midpoint_is_rotation_equivariant(self, first: float, offset: float) -> None:
        """Rotating both inputs rotates the midpoint: no privileged zero point."""
        second = normalize_longitude(first + 47.0)
        rotated = shortest_arc_midpoint(
            normalize_longitude(first + offset), normalize_longitude(second + offset)
        )
        expected = normalize_longitude(shortest_arc_midpoint(first, second) + offset)
        self.assertAlmostEqual(shortest_angular_distance(rotated, expected), 0.0, places=6)


class OppositionAmbiguityTests(unittest.TestCase):
    """Two points 180 degrees apart have two equally valid midpoints."""

    def test_exact_opposition_is_flagged_ambiguous(self) -> None:
        for first, second in ((0.0, 180.0), (90.0, 270.0), (359.0, 179.0), (45.5, 225.5)):
            with self.subTest(first=first, second=second):
                self.assertTrue(is_ambiguous_midpoint(first, second))

    def test_near_opposition_outside_epsilon_is_not_ambiguous(self) -> None:
        offset = OPPOSITION_AMBIGUITY_EPSILON_DEG * 100.0
        self.assertFalse(is_ambiguous_midpoint(0.0, 180.0 - offset))
        self.assertFalse(is_ambiguous_midpoint(0.0, 180.0 + offset))

    def test_ordinary_separations_are_not_ambiguous(self) -> None:
        for first, second in ((0.0, 90.0), (10.0, 350.0), (100.0, 200.0), (0.0, 0.0)):
            with self.subTest(first=first, second=second):
                self.assertFalse(is_ambiguous_midpoint(first, second))

    def test_the_two_valid_answers_are_180_apart(self) -> None:
        """Document what ambiguity means: the discarded answer is the opposite point."""
        forward = shortest_arc_midpoint(0.0, 180.0)
        backward = shortest_arc_midpoint(180.0, 0.0)
        self.assertAlmostEqual(shortest_angular_distance(forward, backward), 180.0, places=9)
