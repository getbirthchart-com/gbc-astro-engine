"""Frozen relationship values for the v0.2 regression corpus.

Pinned from a run with full Swiss Ephemeris data. These catch silent drift in
midpoint arithmetic, overlay assignment and profile defaults: any change to the
numbers below is either a bug or a deliberate methodology change that must be
versioned in the relationship profile.
"""

from __future__ import annotations

import os
import unittest

from gbc_astro import AstrologyEngine
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.providers.swiss import SwissEphemerisProvider

CHART_A = ("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
CHART_B = ("1990-06-21T08:20:00", "Europe/Berlin", 52.52, 13.405)

EXPECTED_COMPOSITE_BODIES = {
    "sun": (155.38752593172458, "virgo", 5.387525931724582),
    "moon": (14.75116120868654, "aries", 14.75116120868654),
    "mercury": (160.40601423508105, "virgo", 10.406014235081045),
}
# Angles are DERIVED from the composite Midheaven, not averaged independently.
# The Ascendant differs by roughly 12.8 degrees from what independent averaging
# produced, which is the size of the error that method carried.
EXPECTED_COMPOSITE_ANGLES = {
    "ascendant": (72.76795156915098, "gemini"),
    "mc": (321.0547419221317, "aquarius"),
}
EXPECTED_COMPOSITE_HOUSE_OF = {"sun": 4, "moon": 11}
EXPECTED_DAVISON = {
    "utc": "1991-08-28T06:57:30Z",
    "latitude": 36.77425,
    "longitude": 59.629599999999996,
    "sun_longitude": 154.49022036916918,
    "ascendant": 220.82077071624454,
}
EXPECTED_OVERLAYS_A_IN_B = {"sun": 4, "moon": 7}
EXPECTED_OVERLAYS_B_IN_A = {"sun": 4, "moon": 3}
EXPECTED_COUNTS = {"crossAspects": 52, "angleInteractions": 39, "compositeAspects": 28}


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


@unittest.skipUnless(_swiss_available(), "Swiss Ephemeris data not configured")
class RelationshipGoldenTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.chart_a = self.engine.natal(*CHART_A)
        self.chart_b = self.engine.natal(*CHART_B)

    def test_composite_body_positions(self) -> None:
        composite = self.engine.composite(self.chart_a, self.chart_b)
        for body_id, (longitude, sign, degree) in EXPECTED_COMPOSITE_BODIES.items():
            with self.subTest(body=body_id):
                body = composite.bodies[body_id]
                self.assertAlmostEqual(body.longitude, longitude, places=9)
                self.assertEqual(body.sign, sign)
                self.assertAlmostEqual(body.degree_in_sign, degree, places=9)

    def test_composite_angles(self) -> None:
        composite = self.engine.composite(self.chart_a, self.chart_b)
        for angle_id, (longitude, sign) in EXPECTED_COMPOSITE_ANGLES.items():
            with self.subTest(angle=angle_id):
                angle = composite.angles[angle_id]
                self.assertAlmostEqual(angle.longitude, longitude, places=9)
                self.assertEqual(angle.sign, sign)

    def test_house_overlays(self) -> None:
        synastry = self.engine.synastry(self.chart_a, self.chart_b)
        a_in_b = {overlay.body: overlay.house for overlay in synastry.a_bodies_in_b_houses}
        b_in_a = {overlay.body: overlay.house for overlay in synastry.b_bodies_in_a_houses}

        for body, house in EXPECTED_OVERLAYS_A_IN_B.items():
            self.assertEqual(a_in_b[body], house, f"A.{body} in B houses")
        for body, house in EXPECTED_OVERLAYS_B_IN_A.items():
            self.assertEqual(b_in_a[body], house, f"B.{body} in A houses")

    def test_composite_house_placements(self) -> None:
        composite = self.engine.composite(self.chart_a, self.chart_b)
        for body_id, house in EXPECTED_COMPOSITE_HOUSE_OF.items():
            self.assertEqual(composite.bodies[body_id].house, house, body_id)

    def test_davison_derived_instant_and_place(self) -> None:
        davison = self.engine.davison(self.chart_a, self.chart_b)
        self.assertEqual(davison.derived_utc_datetime, EXPECTED_DAVISON["utc"])
        self.assertAlmostEqual(davison.derived_latitude, EXPECTED_DAVISON["latitude"], places=9)
        self.assertAlmostEqual(davison.derived_longitude, EXPECTED_DAVISON["longitude"], places=9)
        self.assertAlmostEqual(
            davison.chart.bodies["sun"].longitude, EXPECTED_DAVISON["sun_longitude"], places=9
        )
        self.assertAlmostEqual(
            davison.chart.angles["ascendant"].longitude, EXPECTED_DAVISON["ascendant"], places=9
        )

    def test_result_counts(self) -> None:
        synastry = self.engine.synastry(self.chart_a, self.chart_b)
        composite = self.engine.composite(self.chart_a, self.chart_b)

        self.assertEqual(len(synastry.cross_aspects), EXPECTED_COUNTS["crossAspects"])
        self.assertEqual(len(synastry.angle_interactions), EXPECTED_COUNTS["angleInteractions"])
        self.assertEqual(len(composite.aspects), EXPECTED_COUNTS["compositeAspects"])
