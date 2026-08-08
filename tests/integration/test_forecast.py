"""Transit, event-search and return tests against the real ephemeris.

The v0.3 Definition of Done names one thing it will not accept: "no
daily-sampling masquerading as exact search". Several tests below exist purely
to prove that, by checking results a daily scan could not produce -- sub-second
precision, and events that begin and end between two daily samples.
"""

from __future__ import annotations

import os
import unittest
from collections import Counter
from datetime import datetime, timedelta, timezone

from gbc_astro import AstrologyEngine
from gbc_astro.astronomy.circular import shortest_angular_distance
from gbc_astro.errors import InvalidCalculationProfileError, UnsupportedBodyError
from gbc_astro.forecast.returns import solar_return_window
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.providers.swiss import SwissEphemerisProvider

SECONDS_PER_DAY = 86400.0


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


@unittest.skipUnless(_swiss_available(), "Forecast needs Swiss Ephemeris data")
class ForecastTestCase(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.natal = self.engine.natal(
            "1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542
        )


class TransitTests(ForecastTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.instant = datetime(2026, 8, 8, 12, tzinfo=timezone.utc)

    def test_snapshot_covers_every_body_and_places_them_in_natal_houses(self) -> None:
        transits = self.engine.transits(self.natal, self.instant)
        self.assertEqual(len(transits.transit_bodies), len(self.natal.bodies))
        self.assertEqual(len(transits.transit_house_placements), len(self.natal.bodies))
        for placement in transits.transit_house_placements:
            self.assertIn(placement.natal_house, range(1, 13))

    def test_applying_and_separating_are_real_here_unlike_synastry(self) -> None:
        """The transit moves and the natal point does not: a real shared timeline."""
        transits = self.engine.transits(self.natal, self.instant)
        phases = Counter(aspect.phase for aspect in transits.transit_to_natal_aspects)
        self.assertTrue(phases["applying"] > 0 and phases["separating"] > 0)
        self.assertEqual(phases["indeterminate"], 0)
        self.assertEqual(
            transits.meta["phaseBasis"], "transit_motion_against_fixed_natal_point"
        )

    def test_an_applying_aspect_is_tighter_a_moment_later(self) -> None:
        """Check the label against what the sky actually does next."""
        transits = self.engine.transits(self.natal, self.instant)
        later = self.engine.transits(self.natal, self.instant + timedelta(hours=6))
        later_orbs = {
            (aspect.transit_body, aspect.natal_body, aspect.aspect_type): aspect.orb
            for aspect in later.transit_to_natal_aspects
        }

        checked = 0
        for aspect in transits.transit_to_natal_aspects:
            if aspect.phase != "applying":
                continue
            key = (aspect.transit_body, aspect.natal_body, aspect.aspect_type)
            if key not in later_orbs or aspect.transit_body == "moon":
                continue  # the Moon can pass exactness inside six hours
            self.assertLess(later_orbs[key], aspect.orb, key)
            checked += 1
        self.assertGreater(checked, 0)

    def test_unknown_birth_time_omits_placements_rather_than_inventing_them(self) -> None:
        unknown = self.engine.natal(
            "1992-11-03", "Asia/Ho_Chi_Minh", 21.0285, 105.8542, unknown_time=True
        )
        transits = self.engine.transits(unknown, self.instant)

        self.assertEqual(transits.transit_house_placements, ())
        self.assertTrue(transits.transit_to_natal_aspects)
        self.assertIn(
            "TRANSIT_HOUSE_PLACEMENT_UNAVAILABLE", {w.code for w in transits.warnings}
        )

    def test_canonical_shape_matches_the_contract(self) -> None:
        payload = self.engine.transits(self.natal, self.instant).to_dict()
        self.assertEqual(
            set(payload),
            {
                "schemaVersion",
                "meta",
                "targetInstant",
                "transitBodies",
                "transitToNatalAspects",
                "transitHousePlacements",
                "warnings",
            },
        )

    def test_naive_instants_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.transits(self.natal, datetime(2026, 8, 8, 12))


class EventSearchTests(ForecastTestCase):
    def test_sun_enters_every_sign_exactly_once_a_year(self) -> None:
        result = self.engine.search_events(
            "sign_ingress",
            "sun",
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 12, 31, 23, 59, tzinfo=timezone.utc),
        )
        self.assertEqual(len(result.events), 12)
        self.assertEqual({event.direction for event in result.events}, {"direct"})

    def test_the_2024_equinox_matches_the_published_instant(self) -> None:
        """Reference validation: the March 2024 equinox was 2024-03-20 03:06 UTC."""
        result = self.engine.search_events(
            "exact_longitude",
            "sun",
            datetime(2024, 3, 19, tzinfo=timezone.utc),
            datetime(2024, 3, 21, tzinfo=timezone.utc),
            target_longitude=0.0,
        )
        self.assertEqual(len(result.events), 1)
        found = datetime.fromisoformat(result.events[0].instant_utc.replace("Z", "+00:00"))
        expected = datetime(2024, 3, 20, 3, 6, tzinfo=timezone.utc)
        self.assertLess(abs((found - expected).total_seconds()), 90.0)

    def test_precision_is_far_finer_than_any_daily_sample(self) -> None:
        """A daily scan is wrong by up to twelve hours; this is sub-second."""
        result = self.engine.search_events(
            "station",
            "mercury",
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 12, 31, tzinfo=timezone.utc),
        )
        self.assertTrue(result.events)
        for event in result.events:
            self.assertLess(event.precision_seconds, 1.0)

    def test_mercury_has_three_retrograde_periods_in_2024(self) -> None:
        """Known: 1-25 April, 5-28 August, 26 November - 15 December."""
        result = self.engine.search_events(
            "station",
            "mercury",
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 12, 31, tzinfo=timezone.utc),
        )
        retrograde = [e for e in result.events if e.event_type == "station_retrograde"]
        self.assertEqual(len(retrograde), 3)
        self.assertEqual([e.instant_utc[5:7] for e in retrograde], ["04", "08", "11"])

    def test_a_station_is_where_speed_changes_sign(self) -> None:
        result = self.engine.search_events(
            "station",
            "mercury",
            datetime(2024, 3, 1, tzinfo=timezone.utc),
            datetime(2024, 5, 31, tzinfo=timezone.utc),
        )
        for event in result.events:
            before = float(event.detail["speedBefore"])  # type: ignore[arg-type]
            after = float(event.detail["speedAfter"])  # type: ignore[arg-type]
            self.assertLess(before * after, 0.0)

    def test_a_retrograde_body_crosses_the_same_degree_three_times(self) -> None:
        """The case a daily nearest-sample scan cannot represent at all."""
        stations = self.engine.search_events(
            "station",
            "mercury",
            datetime(2024, 3, 1, tzinfo=timezone.utc),
            datetime(2024, 5, 31, tzinfo=timezone.utc),
        )
        loop_longitude = stations.events[0].longitude - 3.0

        crossings = self.engine.search_events(
            "exact_longitude",
            "mercury",
            datetime(2024, 3, 20, tzinfo=timezone.utc),
            datetime(2024, 5, 20, tzinfo=timezone.utc),
            target_longitude=loop_longitude,
        )
        self.assertEqual(len(crossings.events), 3)
        self.assertEqual(
            [event.direction for event in crossings.events],
            ["direct", "retrograde", "direct"],
        )

    def test_every_located_longitude_really_is_the_target(self) -> None:
        result = self.engine.search_events(
            "exact_longitude",
            "venus",
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 12, 31, tzinfo=timezone.utc),
            target_longitude=100.0,
        )
        self.assertTrue(result.events)
        for event in result.events:
            self.assertLess(shortest_angular_distance(event.longitude, 100.0), 1e-6)

    def test_exact_aspect_search_finds_both_sides_of_the_reference(self) -> None:
        result = self.engine.search_events(
            "exact_aspect",
            "mars",
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 12, 31, tzinfo=timezone.utc),
            target_longitude=0.0,
            aspect_angle=90.0,
        )
        self.assertTrue(result.events)
        for event in result.events:
            separation = shortest_angular_distance(event.longitude, 0.0)
            self.assertAlmostEqual(separation, 90.0, places=5)

    def test_events_are_returned_in_time_order(self) -> None:
        result = self.engine.search_events(
            "sign_ingress",
            "mercury",
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 12, 31, tzinfo=timezone.utc),
        )
        stamps = [event.instant_utc for event in result.events]
        self.assertEqual(stamps, sorted(stamps))

    def test_missing_parameters_are_refused(self) -> None:
        for event_type, kwargs in (
            ("exact_longitude", {}),
            ("exact_aspect", {"target_longitude": 0.0}),
            ("nonsense", {}),
        ):
            with self.subTest(event_type=event_type), self.assertRaises(
                InvalidCalculationProfileError
            ):
                self.engine.search_events(
                        event_type,
                        "sun",
                        datetime(2024, 1, 1, tzinfo=timezone.utc),
                    datetime(2024, 2, 1, tzinfo=timezone.utc),
                    **kwargs,  # type: ignore[arg-type]
                )


class ReturnTests(ForecastTestCase):
    def test_saturn_returns_three_times_across_its_retrograde_loop(self) -> None:
        """The multi-hit case the Definition of Done names explicitly."""
        result = self.engine.returns(
            self.natal,
            "saturn",
            datetime(2021, 1, 1, tzinfo=timezone.utc),
            datetime(2023, 12, 31, tzinfo=timezone.utc),
        )
        self.assertEqual(len(result.hits), 3)
        self.assertEqual(
            [hit.direction for hit in result.hits], ["direct", "retrograde", "direct"]
        )
        self.assertEqual([hit.ordinal for hit in result.hits], [1, 2, 3])

    def test_every_hit_lands_on_the_natal_longitude(self) -> None:
        result = self.engine.returns(
            self.natal,
            "saturn",
            datetime(2021, 1, 1, tzinfo=timezone.utc),
            datetime(2023, 12, 31, tzinfo=timezone.utc),
        )
        for hit in result.hits:
            self.assertLess(
                shortest_angular_distance(hit.longitude, result.natal_longitude), 1e-6
            )

    def test_the_solar_return_is_a_single_hit_the_sun_never_retrogrades(self) -> None:
        birth = datetime.fromisoformat(self.natal.subject.utc_datetime.replace("Z", "+00:00"))
        start, end = solar_return_window(birth, 2026)
        result = self.engine.returns(self.natal, "sun", start, end)

        self.assertEqual(len(result.hits), 1)
        self.assertEqual(result.hits[0].direction, "direct")
        self.assertAlmostEqual(
            result.hits[0].longitude, self.natal.bodies["sun"].longitude, places=6
        )

    def test_the_lunar_return_is_a_single_hit_in_one_cycle(self) -> None:
        from gbc_astro.forecast.returns import lunar_return_window

        start, end = lunar_return_window(datetime(2026, 1, 1, tzinfo=timezone.utc))
        result = self.engine.returns(self.natal, "moon", start, end)
        self.assertEqual(len(result.hits), 1)

    def test_return_charts_are_cast_at_the_natal_location(self) -> None:
        birth = datetime.fromisoformat(self.natal.subject.utc_datetime.replace("Z", "+00:00"))
        start, end = solar_return_window(birth, 2026)
        result = self.engine.returns(self.natal, "sun", start, end, include_charts=True)

        chart = result.hits[0].chart
        self.assertIsNotNone(chart)
        assert chart is not None
        self.assertAlmostEqual(chart.subject.latitude, self.natal.subject.latitude)
        self.assertAlmostEqual(chart.subject.longitude, self.natal.subject.longitude)
        self.assertEqual(len(chart.houses), 12)

    def test_precision_is_sub_second_not_a_daily_sample(self) -> None:
        birth = datetime.fromisoformat(self.natal.subject.utc_datetime.replace("Z", "+00:00"))
        start, end = solar_return_window(birth, 2026)
        result = self.engine.returns(self.natal, "sun", start, end)
        self.assertLess(result.hits[0].precision_seconds, 1.0)

    def test_a_window_with_no_return_says_so_rather_than_guessing(self) -> None:
        result = self.engine.returns(
            self.natal,
            "saturn",
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 2, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(result.hits, ())
        self.assertIn("NO_RETURN_IN_WINDOW", {w.code for w in result.warnings})

    def test_an_unknown_body_is_refused(self) -> None:
        with self.assertRaises(UnsupportedBodyError):
            self.engine.returns(
                self.natal,
                "nibiru",
                datetime(2024, 1, 1, tzinfo=timezone.utc),
                datetime(2025, 1, 1, tzinfo=timezone.utc),
            )

    def test_an_inverted_window_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.returns(
                self.natal,
                "sun",
                datetime(2025, 1, 1, tzinfo=timezone.utc),
                datetime(2024, 1, 1, tzinfo=timezone.utc),
            )

    def test_the_result_states_its_method(self) -> None:
        birth = datetime.fromisoformat(self.natal.subject.utc_datetime.replace("Z", "+00:00"))
        start, end = solar_return_window(birth, 2026)
        result = self.engine.returns(self.natal, "sun", start, end)

        self.assertEqual(result.meta["method"], "bracketed_root_find_bisection_refined")
        self.assertTrue(
            any("not from" in note or "never" in note for note in result.notes)
        )
