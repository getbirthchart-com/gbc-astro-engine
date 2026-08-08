from __future__ import annotations

import math
import unittest

from hypothesis import given, settings
from hypothesis import strategies as st

from gbc_astro.astronomy.circular import (
    normalize_longitude,
    shortest_angular_distance,
    shortest_arc_midpoint,
)
from gbc_astro.houses.equal import equal_cusp_longitudes
from gbc_astro.houses.whole_sign import whole_sign_cusp_longitudes
from gbc_astro.zodiac.tropical import longitude_to_tropical

FINITE_DEGREES = st.floats(
    min_value=-1_000_000.0,
    max_value=1_000_000.0,
    allow_nan=False,
    allow_infinity=False,
)


class PropertyInvariantTests(unittest.TestCase):
    @settings(max_examples=200)
    @given(FINITE_DEGREES)
    def test_normalized_longitude_range(self, value: float) -> None:
        normalized = normalize_longitude(value)
        self.assertGreaterEqual(normalized, 0.0)
        self.assertLess(normalized, 360.0)

    @settings(max_examples=200)
    @given(FINITE_DEGREES, st.integers(min_value=-1000, max_value=1000))
    def test_normalization_periodicity(self, value: float, turns: int) -> None:
        self.assertTrue(
            math.isclose(
                normalize_longitude(value),
                normalize_longitude(value + 360.0 * turns),
                abs_tol=1e-9,
            )
        )

    @settings(max_examples=200)
    @given(FINITE_DEGREES, FINITE_DEGREES)
    def test_circular_distance_symmetry_and_range(self, a: float, b: float) -> None:
        distance_ab = shortest_angular_distance(a, b)
        distance_ba = shortest_angular_distance(b, a)
        self.assertTrue(math.isclose(distance_ab, distance_ba, abs_tol=1e-12))
        self.assertGreaterEqual(distance_ab, 0.0)
        self.assertLessEqual(distance_ab, 180.0)

    @settings(max_examples=200)
    @given(FINITE_DEGREES)
    def test_opposite_point_identity(self, value: float) -> None:
        opposite = normalize_longitude(value + 180.0)
        self.assertTrue(
            math.isclose(shortest_angular_distance(value, opposite), 180.0, abs_tol=1e-9)
        )

    @settings(max_examples=200)
    @given(st.floats(min_value=0.0, max_value=359.999999, allow_nan=False, allow_infinity=False))
    def test_zodiac_maps_every_normalized_longitude(self, value: float) -> None:
        position = longitude_to_tropical(value)
        self.assertGreaterEqual(position.degree_in_sign, 0.0)
        self.assertLess(position.degree_in_sign, 30.0)

    @settings(max_examples=100)
    @given(FINITE_DEGREES)
    def test_equal_house_adjacent_cusps_are_30_degrees(self, ascendant: float) -> None:
        cusps = equal_cusp_longitudes(ascendant)
        for index, cusp in enumerate(cusps):
            next_cusp = cusps[(index + 1) % 12]
            self.assertTrue(
                math.isclose(shortest_angular_distance(cusp + 30.0, next_cusp), 0.0, abs_tol=1e-9)
            )

    @settings(max_examples=100)
    @given(FINITE_DEGREES)
    def test_whole_sign_each_house_spans_one_sign(self, ascendant: float) -> None:
        cusps = whole_sign_cusp_longitudes(ascendant)
        for cusp in cusps:
            self.assertTrue(math.isclose(cusp % 30.0, 0.0, abs_tol=1e-9))

    def test_midpoint_wrap_regressions(self) -> None:
        self.assertEqual(shortest_arc_midpoint(359.0, 1.0), 0.0)
        self.assertEqual(shortest_arc_midpoint(350.0, 10.0), 0.0)


if __name__ == "__main__":
    unittest.main()

