from __future__ import annotations

import unittest

from gbc_astro.astronomy.circular import (
    directed_circular_delta,
    normalize_longitude,
    shortest_angular_distance,
    shortest_arc_midpoint,
)


class CircularMathTests(unittest.TestCase):
    def test_normalize_longitude(self) -> None:
        self.assertEqual(normalize_longitude(0), 0)
        self.assertEqual(normalize_longitude(360), 0)
        self.assertEqual(normalize_longitude(-1), 359)
        self.assertEqual(normalize_longitude(721), 1)

    def test_shortest_angular_distance_wraps(self) -> None:
        self.assertEqual(shortest_angular_distance(359, 1), 2)
        self.assertEqual(shortest_angular_distance(10, 350), 20)
        self.assertEqual(shortest_angular_distance(0, 180), 180)

    def test_directed_delta(self) -> None:
        self.assertEqual(directed_circular_delta(350, 10), 20)
        self.assertEqual(directed_circular_delta(10, 350), -20)

    def test_shortest_arc_midpoint(self) -> None:
        self.assertEqual(shortest_arc_midpoint(359, 1), 0)
        self.assertEqual(shortest_arc_midpoint(350, 10), 0)
        self.assertEqual(shortest_arc_midpoint(90, 150), 120)


if __name__ == "__main__":
    unittest.main()

