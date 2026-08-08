from __future__ import annotations

import unittest
from datetime import datetime, timezone

from gbc_astro.astronomy.provider_time import julian_day_ut


class ProviderTimeTests(unittest.TestCase):
    def test_julian_day_ut(self) -> None:
        self.assertEqual(
            julian_day_ut(datetime(2000, 1, 1, 12, tzinfo=timezone.utc)),
            2451545.0,
        )

    def test_requires_aware_datetime(self) -> None:
        with self.assertRaises(ValueError):
            julian_day_ut(datetime(2000, 1, 1, 12))


if __name__ == "__main__":
    unittest.main()
