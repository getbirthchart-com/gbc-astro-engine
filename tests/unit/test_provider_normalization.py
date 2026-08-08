from __future__ import annotations

import unittest

from gbc_astro.models.position import RawBodyPosition
from gbc_astro.providers.normalization import normalize_body_position


class ProviderNormalizationTests(unittest.TestCase):
    def test_normalizes_body_position_and_retrograde(self) -> None:
        body = normalize_body_position(
            "mercury",
            RawBodyPosition(
                longitude_deg=390.5,
                latitude_deg=-1.25,
                distance=0.9,
                longitude_speed_deg_per_day=-0.42,
            ),
        )
        self.assertEqual(body.longitude, 30.5)
        self.assertEqual(body.sign, "taurus")
        self.assertEqual(body.degree_in_sign, 0.5)
        self.assertTrue(body.retrograde)

    def test_unknown_speed_has_indeterminate_retrograde(self) -> None:
        body = normalize_body_position(
            "chiron",
            RawBodyPosition(
                longitude_deg=29.0,
                latitude_deg=0.0,
                distance=None,
                longitude_speed_deg_per_day=None,
            ),
        )
        self.assertIsNone(body.retrograde)


if __name__ == "__main__":
    unittest.main()

