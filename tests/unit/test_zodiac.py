from __future__ import annotations

import unittest

from gbc_astro.constants import SIGN_IDS
from gbc_astro.zodiac.tropical import longitude_to_tropical


class TropicalZodiacTests(unittest.TestCase):
    def test_all_boundaries(self) -> None:
        for index, sign in enumerate(SIGN_IDS):
            position = longitude_to_tropical(index * 30.0)
            self.assertEqual(position.sign, sign)
            self.assertEqual(position.degree_in_sign, 0.0)

    def test_wrap_boundary(self) -> None:
        position = longitude_to_tropical(359.999)
        self.assertEqual(position.sign, "pisces")
        self.assertAlmostEqual(position.degree_in_sign, 29.999)
        self.assertEqual(longitude_to_tropical(360.0).sign, "aries")


if __name__ == "__main__":
    unittest.main()

