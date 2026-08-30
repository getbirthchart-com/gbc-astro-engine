from __future__ import annotations

import unittest

from gbc_astro.astronomy.circular import shortest_angular_distance
from gbc_astro.houses.base import assign_house, build_house_cusps
from gbc_astro.houses.equal import equal_cusp_longitudes
from gbc_astro.houses.systems import HOUSE_SYSTEMS
from gbc_astro.houses.whole_sign import whole_sign_cusp_longitudes


class HouseTests(unittest.TestCase):
    def test_whole_sign_cusps_start_at_asc_sign(self) -> None:
        self.assertEqual(whole_sign_cusp_longitudes(44.2)[0], 30.0)

    def test_equal_cusps_start_at_asc_degree(self) -> None:
        self.assertEqual(equal_cusp_longitudes(44.2)[0], 44.2)
        self.assertAlmostEqual(equal_cusp_longitudes(350.0)[1], 20.0)

    def test_assign_house_wraparound_and_cusp_policy(self) -> None:
        houses = build_house_cusps(equal_cusp_longitudes(350.0))
        self.assertEqual(assign_house(355.0, houses), 1)
        self.assertEqual(assign_house(10.0, houses), 1)
        self.assertEqual(assign_house(20.0, houses), 2)

    def test_equal_cusp_ten_is_not_the_midheaven(self) -> None:
        """Equal houses from the Ascendant; MC is an independent angle."""
        ascendant = 44.2
        midheaven = 263.0
        cusps = equal_cusp_longitudes(ascendant)
        self.assertAlmostEqual(cusps[0], ascendant)
        self.assertGreater(shortest_angular_distance(cusps[9], midheaven), 1.0)

    def test_whole_sign_cusp_ten_is_not_the_midheaven(self) -> None:
        ascendant = 44.2
        midheaven = 263.0
        cusps = whole_sign_cusp_longitudes(ascendant)
        self.assertEqual(cusps[0], 30.0)
        self.assertGreater(shortest_angular_distance(cusps[9], midheaven), 1.0)

    def test_equal_quadrant_based_does_not_mean_cusp_ten_is_mc(self) -> None:
        """The flag records that cusp 1 is the Ascendant, not that cusp 10 is MC."""
        self.assertTrue(HOUSE_SYSTEMS["equal"].quadrant_based)
        self.assertFalse(HOUSE_SYSTEMS["whole_sign"].quadrant_based)
        self.assertIn("not the Midheaven", HOUSE_SYSTEMS["equal"].description)


if __name__ == "__main__":
    unittest.main()

