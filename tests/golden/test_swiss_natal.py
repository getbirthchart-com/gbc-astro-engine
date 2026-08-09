from __future__ import annotations

import os
import unittest

from gbc_astro import AstrologyEngine
from gbc_astro.errors import HouseCalculationUnavailableError
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.providers.swiss import SwissEphemerisProvider


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


@unittest.skipUnless(_swiss_available(), "Swiss Ephemeris data not configured")
class SwissNatalGoldenTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )

    def test_hanoi_1992_placidus_sample(self) -> None:
        chart = self.engine.natal(
            local_datetime="1992-11-03T14:35:00",
            timezone="Asia/Ho_Chi_Minh",
            latitude=21.0285,
            longitude=105.8542,
            house_system="placidus",
        )
        self.assertAlmostEqual(chart.bodies["sun"].longitude, 221.14154838535987)
        self.assertAlmostEqual(chart.bodies["moon"].longitude, 321.2929834918872)
        self.assertAlmostEqual(chart.bodies["chiron"].longitude, 142.609580564659)
        self.assertAlmostEqual(chart.angles["ascendant"].longitude, 350.1088136374758)
        self.assertAlmostEqual(chart.angles["mc"].longitude, 263.03877867919044)
        self.assertAlmostEqual(chart.houses[1].cusp_longitude, 27.07390716301976)
        self.assertEqual(chart.derived.big_three["sun"], "scorpio")
        self.assertEqual(chart.derived.big_three["moon"], "aquarius")
        self.assertEqual(chart.derived.big_three["rising"], "pisces")
        # 14, not 18. Four of the old aspects were the mean node repeating what
        # the true node already said, including a "true_node conjunct mean_node"
        # that appeared in every chart the engine had ever produced.
        self.assertEqual(len(chart.aspects), 14)

    def test_high_latitude_placidus_is_explicit_error(self) -> None:
        with self.assertRaises(HouseCalculationUnavailableError):
            self.engine.natal(
                local_datetime="1992-06-21T12:00:00",
                timezone="UTC",
                latitude=70.0,
                longitude=0.0,
                house_system="placidus",
            )


if __name__ == "__main__":
    unittest.main()
