from __future__ import annotations

import unittest

from gbc_astro.houses.base import assign_house, build_house_cusps
from gbc_astro.houses.equal import equal_cusp_longitudes
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


if __name__ == "__main__":
    unittest.main()

