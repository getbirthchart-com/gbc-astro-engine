"""Every path that reaches a provider must honour the engine's zodiac.

Five bugs of one shape were found by auditing the v1.0 modules: the zodiac was
applied as a final transform inside `natal()`, and every other path -- transits,
returns, event search, the ephemeris table -- went straight to the provider and
got tropical positions. A sidereal chart was then compared against them.

The failures were silent. Transits were out by the whole ayanamsa, a solar
return was searched for at a longitude the Sun would not reach for weeks and the
engine reported NO_RETURN_IN_WINDOW as though that were an answer, and
astrocartography moved its lines 2,500 km because it let a labelling convention
change a geographic fact.

These tests fix the shape of the mistake in place, so a sixth path cannot repeat
it: each asserts what must rotate, what must not, and that the result declares
which zodiac it is in.
"""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone

from gbc_astro import AstrologyEngine
from gbc_astro.astronomy.circular import normalize_longitude, shortest_angular_distance
from gbc_astro.forecast.returns import solar_return_window
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.defaults import VEDIC_SIDEREAL_V1
from gbc_astro.providers.swiss import SwissEphemerisProvider

BIRTH = ("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
TARGET = datetime(2026, 8, 8, 12, tzinfo=timezone.utc)


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


@unittest.skipUnless(_swiss_available(), "Zodiac coherence needs Swiss Ephemeris data")
class ZodiacCoherenceTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        provider = SwissEphemerisProvider(ephemeris_path=path)
        houses = SwissHouseCalculator(ephemeris_path=path)
        self.sidereal = AstrologyEngine(
            provider=provider, house_calculator=houses, profile=VEDIC_SIDEREAL_V1
        )
        self.tropical = AstrologyEngine(provider=provider, house_calculator=houses)
        self.sidereal_natal = self.sidereal.natal(*BIRTH)
        self.tropical_natal = self.tropical.natal(*BIRTH)

    # --- must rotate -----------------------------------------------------

    def test_transit_positions_are_in_the_charts_zodiac(self) -> None:
        sidereal = self.sidereal.transits(self.sidereal_natal, TARGET)
        tropical = self.tropical.transits(self.tropical_natal, TARGET)
        offset = float(sidereal.meta["zodiacOffsetDegrees"])

        self.assertGreater(offset, 20.0)
        for body_id, body in tropical.transit_bodies.items():
            with self.subTest(body=body_id):
                self.assertAlmostEqual(
                    shortest_angular_distance(
                        normalize_longitude(body.longitude - offset),
                        sidereal.transit_bodies[body_id].longitude,
                    ),
                    0.0,
                    places=9,
                )

    def test_transits_declare_their_zodiac(self) -> None:
        meta = self.sidereal.transits(self.sidereal_natal, TARGET).meta
        self.assertEqual(meta["zodiac"], "sidereal")
        self.assertEqual(meta["ayanamsa"], "lahiri")

    def test_a_sidereal_solar_return_is_found_at_all(self) -> None:
        """It used to report NO_RETURN_IN_WINDOW, which looked like an answer."""
        birth = datetime.fromisoformat(
            self.sidereal_natal.subject.utc_datetime.replace("Z", "+00:00")
        )
        result = self.sidereal.returns(
            self.sidereal_natal, "sun", *solar_return_window(birth, 2026)
        )
        self.assertEqual(len(result.hits), 1)
        self.assertEqual(result.meta["zodiac"], "sidereal")

    def test_the_sidereal_return_lags_the_tropical_one_by_the_ayanamsa_drift(
        self,
    ) -> None:
        """Not an arbitrary difference: it is the drift since birth, in Sun-days.

        The ayanamsa moves about 50 arcseconds a year, so over 34 years it grows
        by roughly half a degree -- which the Sun covers in about twelve hours.
        """
        birth = datetime.fromisoformat(
            self.sidereal_natal.subject.utc_datetime.replace("Z", "+00:00")
        )
        window = solar_return_window(birth, 2026)
        sidereal = self.sidereal.returns(self.sidereal_natal, "sun", *window).hits[0]
        tropical = self.tropical.returns(self.tropical_natal, "sun", *window).hits[0]

        lag_hours = (
            datetime.fromisoformat(sidereal.instant_utc.replace("Z", "+00:00"))
            - datetime.fromisoformat(tropical.instant_utc.replace("Z", "+00:00"))
        ).total_seconds() / 3600.0
        self.assertGreater(lag_hours, 6.0)
        self.assertLess(lag_hours, 18.0)

    def test_sidereal_sign_ingresses_are_not_the_tropical_ones(self) -> None:
        """The Sun enters sidereal Aries in mid-April, not at the equinox."""
        window = (
            datetime(2026, 3, 1, tzinfo=timezone.utc),
            datetime(2026, 4, 30, tzinfo=timezone.utc),
        )
        sidereal = self.sidereal.search_events("sign_ingress", "sun", *window)
        tropical = self.tropical.search_events("sign_ingress", "sun", *window)

        sidereal_aries = next(
            event for event in sidereal.events if event.detail["enteringSign"] == "aries"
        )
        tropical_aries = next(
            event for event in tropical.events if event.detail["enteringSign"] == "aries"
        )
        self.assertEqual(sidereal_aries.instant_utc[5:7], "04")
        self.assertEqual(tropical_aries.instant_utc[5:7], "03")
        self.assertEqual(sidereal.meta["zodiac"], "sidereal")

    def test_the_ephemeris_table_is_in_the_engines_zodiac_and_says_so(self) -> None:
        window = (
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 3, tzinfo=timezone.utc),
        )
        sidereal = self.sidereal.ephemeris(("sun",), *window, timedelta(days=1))
        tropical = self.tropical.ephemeris(("sun",), *window, timedelta(days=1))

        self.assertEqual(sidereal["zodiac"], "sidereal")
        self.assertEqual(sidereal["ayanamsa"], "lahiri")
        self.assertEqual(tropical["zodiac"], "tropical")
        self.assertIsNone(tropical["ayanamsa"])

        difference = shortest_angular_distance(
            sidereal["rows"][0]["bodies"]["sun"]["longitude"],
            tropical["rows"][0]["bodies"]["sun"]["longitude"],
        )
        self.assertGreater(difference, 20.0)

    # --- must NOT depend on the zodiac -----------------------------------

    def test_astrocartography_lines_are_the_same_in_either_zodiac(self) -> None:
        """Where a body is angular on Earth is a fact, not a labelling choice."""
        sidereal = self.sidereal.astrocartography(
            self.sidereal_natal, bodies=("sun", "moon", "jupiter")
        )
        tropical = self.tropical.astrocartography(
            self.tropical_natal, bodies=("sun", "moon", "jupiter")
        )
        sidereal_lines = {line["id"]: line for line in sidereal["lines"]}

        for line in tropical["lines"]:
            with self.subTest(line=line["id"]):
                other = sidereal_lines[line["id"]]
                self.assertEqual(len(line["points"]), len(other["points"]))
                for first, second in zip(line["points"], other["points"], strict=True):
                    self.assertAlmostEqual(
                        first["longitude"], second["longitude"], places=9
                    )

    def test_station_instants_do_not_depend_on_the_zodiac(self) -> None:
        """A station is where speed changes sign; relabelling cannot move it."""
        window = (
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 12, 31, tzinfo=timezone.utc),
        )
        sidereal = self.sidereal.search_events("station", "mercury", *window)
        tropical = self.tropical.search_events("station", "mercury", *window)

        self.assertEqual(
            [event.instant_utc for event in sidereal.events],
            [event.instant_utc for event in tropical.events],
        )

    def test_draconic_is_the_same_chart_in_either_zodiac(self) -> None:
        """Subtracting the node cancels the ayanamsa; both bodies carry it."""
        sidereal = self.sidereal.draconic(self.sidereal_natal)
        tropical = self.tropical.draconic(self.tropical_natal)
        for body_id, body in tropical.bodies.items():
            with self.subTest(body=body_id):
                self.assertAlmostEqual(
                    shortest_angular_distance(
                        body.longitude, sidereal.bodies[body_id].longitude
                    ),
                    0.0,
                    places=6,
                )

    def test_progressions_use_the_ayanamsa_of_the_progressed_instant(self) -> None:
        """Not the natal one: the progressed chart is a real chart at its own time."""
        sidereal = self.sidereal.progressions(self.sidereal_natal, TARGET)
        tropical = self.tropical.progressions(self.tropical_natal, TARGET)

        difference = shortest_angular_distance(
            tropical.bodies["sun"].longitude, sidereal.bodies["sun"].longitude
        )
        natal_ayanamsa = self.sidereal_natal.meta.ayanamsa_degrees
        assert natal_ayanamsa is not None

        # Larger than the natal ayanamsa, by the drift over the progressed days.
        self.assertGreater(difference, natal_ayanamsa)
        self.assertLess(difference - natal_ayanamsa, 0.01)
