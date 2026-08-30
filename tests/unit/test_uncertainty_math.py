"""Circular unwrap, civil-day interval, and classification math."""

from __future__ import annotations

import math
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

from gbc_astro import AstrologyEngine
from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.errors import AmbiguousLocalTimeError, NonexistentLocalTimeError
from gbc_astro.models.position import RawBodyPosition
from gbc_astro.profiles.resolve import resolve_calculation_profile
from gbc_astro.uncertainty.constants import (
    PROPERTY_LONGITUDE,
    PROPERTY_SIGN,
    REASON_EVALUATION_LIMIT,
    conservative_speed,
    segment_may_station,
)
from gbc_astro.uncertainty.interval import resolve_civil_day_interval, sample_julian_days
from gbc_astro.uncertainty.motion import circular_range_deg, signs_covering, unwrap_longitudes
from tests.helpers import FixtureHouseCalculator, FixtureProvider

_EPOCH = datetime(1992, 11, 3, 0, 0, tzinfo=timezone.utc)
_CONJUNCTION_ONLY = resolve_calculation_profile(
    aspect_preset="custom",
    custom_aspect_rules=[{"type": "conjunction", "exact_angle": 0, "orb": 5}],
)


class SweepingMoonProvider(FixtureProvider):
    """Sun fixed at 0°. Moon longitude = start + speed × days from UTC midnight."""

    def __init__(self, moon_start: float, moon_speed: float) -> None:
        self._moon_start = moon_start
        self._moon_speed = moon_speed

    def position(self, body: str, instant_utc: datetime) -> RawBodyPosition:
        aware = (
            instant_utc
            if instant_utc.tzinfo is not None
            else instant_utc.replace(tzinfo=timezone.utc)
        )
        days = (aware - _EPOCH).total_seconds() / 86400.0
        if body == "sun":
            return RawBodyPosition(
                longitude_deg=0.0,
                latitude_deg=0.0,
                distance=None,
                longitude_speed_deg_per_day=0.0,
            )
        if body == "moon":
            return RawBodyPosition(
                longitude_deg=normalize_longitude(
                    self._moon_start + self._moon_speed * days
                ),
                latitude_deg=0.0,
                distance=None,
                longitude_speed_deg_per_day=self._moon_speed,
            )
        return super().position(body, instant_utc)


class MercuryStationProvider(FixtureProvider):
    """Mercury longitude speed changes sign during the UTC civil day."""

    def position(self, body: str, instant_utc: datetime) -> RawBodyPosition:
        if body != "mercury":
            return super().position(body, instant_utc)
        aware = (
            instant_utc
            if instant_utc.tzinfo is not None
            else instant_utc.replace(tzinfo=timezone.utc)
        )
        days = (aware - _EPOCH).total_seconds() / 86400.0
        speed = 0.5 - days
        longitude = normalize_longitude(200.0 + 0.5 * days - 0.5 * days * days)
        return RawBodyPosition(
            longitude_deg=longitude,
            latitude_deg=0.0,
            distance=None,
            longitude_speed_deg_per_day=speed,
        )


_FIRST_INTERVAL = 1.0 / 12.0


def _mid_bump(days: float) -> float:
    """1 at the midpoint of the first coarse interval, 0 at its endpoints."""

    if days <= 0.0 or days >= _FIRST_INTERVAL:
        return 0.0
    return math.sin(math.pi * days / _FIRST_INTERVAL) ** 2


class HiddenStationProvider(FixtureProvider):
    """Mercury stations between coarse samples; endpoints stay direct."""

    def position(self, body: str, instant_utc: datetime) -> RawBodyPosition:
        if body != "mercury":
            return super().position(body, instant_utc)
        aware = (
            instant_utc
            if instant_utc.tzinfo is not None
            else instant_utc.replace(tzinfo=timezone.utc)
        )
        days = (aware - _EPOCH).total_seconds() / 86400.0
        speed = 0.05 - 1.0 * _mid_bump(days)
        return RawBodyPosition(
            longitude_deg=normalize_longitude(200.0 + 0.05 * days),
            latitude_deg=0.0,
            distance=None,
            longitude_speed_deg_per_day=speed,
        )


class HiddenEnterLeaveProvider(FixtureProvider):
    """Sun-Moon conjunction only near the first-interval midpoint."""

    def position(self, body: str, instant_utc: datetime) -> RawBodyPosition:
        aware = (
            instant_utc
            if instant_utc.tzinfo is not None
            else instant_utc.replace(tzinfo=timezone.utc)
        )
        days = (aware - _EPOCH).total_seconds() / 86400.0
        if body == "sun":
            return RawBodyPosition(
                longitude_deg=0.0,
                latitude_deg=0.0,
                distance=None,
                longitude_speed_deg_per_day=0.0,
            )
        if body == "moon":
            return RawBodyPosition(
                longitude_deg=normalize_longitude(6.0 - 6.0 * _mid_bump(days)),
                latitude_deg=0.0,
                distance=None,
                longitude_speed_deg_per_day=0.0,
            )
        return super().position(body, instant_utc)


def _utc_unknown(provider: FixtureProvider):
    return AstrologyEngine(
        provider=provider,
        house_calculator=FixtureHouseCalculator(),
        profile=_CONJUNCTION_ONLY,
    ).natal("1992-11-03", "UTC", 0.0, 0.0, unknown_time=True)


class UnwrapTests(unittest.TestCase):
    def test_wrap_from_359_to_0_is_a_small_range(self) -> None:
        unwrapped = unwrap_longitudes((359.8, 0.0, 0.2))
        self.assertAlmostEqual(unwrapped[0], 359.8)
        self.assertAlmostEqual(unwrapped[-1], 360.2)
        self.assertAlmostEqual(circular_range_deg(unwrapped), 0.4)
        self.assertEqual(signs_covering(unwrapped), ("pisces", "aries"))

    def test_monotonic_direct_motion_does_not_invent_a_wrap(self) -> None:
        unwrapped = unwrap_longitudes((10.0, 12.0, 15.0))
        self.assertAlmostEqual(circular_range_deg(unwrapped), 5.0)
        self.assertEqual(signs_covering(unwrapped), ("aries",))

    def test_retrograde_unwrap_goes_backward(self) -> None:
        unwrapped = unwrap_longitudes((1.0, 0.2, 359.8))
        self.assertLess(unwrapped[-1], unwrapped[0])
        self.assertAlmostEqual(circular_range_deg(unwrapped), 1.2, places=5)


class CivilDayIntervalTests(unittest.TestCase):
    def test_endpoints_are_converted_independently(self) -> None:
        interval = resolve_civil_day_interval(date(1992, 11, 3), "Asia/Ho_Chi_Minh")
        self.assertEqual(interval.start_local, datetime(1992, 11, 3, 0, 0, 0))
        self.assertEqual(interval.end_local, datetime(1992, 11, 3, 23, 59, 59, 999999))
        self.assertGreater(interval.duration_days, 0.99)
        self.assertLess(interval.duration_days, 1.01)
        payload = interval.to_dict()
        self.assertTrue(payload["startUtc"].endswith("Z"))
        self.assertTrue(payload["endUtc"].endswith("Z"))
        self.assertNotEqual(payload["startUtc"], payload["endUtc"])

    def test_dst_spring_forward_day_is_shorter_than_24_hours(self) -> None:
        interval = resolve_civil_day_interval(date(2024, 3, 10), "America/New_York")
        self.assertAlmostEqual(interval.duration_days, 23.0 / 24.0, places=3)
        samples = sample_julian_days(interval, 12)
        self.assertEqual(len(samples), 13)
        self.assertEqual(samples[0], interval.start_jd)
        self.assertEqual(samples[-1], interval.end_jd)

    def test_dst_fall_back_day_is_longer_than_24_hours(self) -> None:
        interval = resolve_civil_day_interval(date(2024, 11, 3), "America/New_York")
        self.assertAlmostEqual(interval.duration_days, 25.0 / 24.0, places=3)

    def test_historical_timezone_converts_both_ends(self) -> None:
        interval = resolve_civil_day_interval(date(1950, 6, 15), "America/New_York")
        self.assertGreater(interval.duration_days, 0.9)
        self.assertEqual(interval.start.utc_datetime.utcoffset().total_seconds(), 0)
        # 1950-06-15 00:00 EDT is UTC-4.
        self.assertEqual(interval.start.utc_datetime.hour, 4)

    def test_nonexistent_and_ambiguous_interior_times_are_not_invented_as_births(self) -> None:
        with self.assertRaises(NonexistentLocalTimeError):
            from gbc_astro.astronomy.time import normalize_local_datetime

            normalize_local_datetime(datetime(2024, 3, 10, 2, 30), "America/New_York")
        with self.assertRaises(AmbiguousLocalTimeError):
            from gbc_astro.astronomy.time import normalize_local_datetime

            normalize_local_datetime(datetime(2024, 11, 3, 1, 30), "America/New_York")
        interval = resolve_civil_day_interval(date(2024, 3, 10), "America/New_York")
        self.assertEqual(interval.start_local.hour, 0)
        self.assertEqual(interval.end_local.hour, 23)


class SyntheticAspectIntervalTests(unittest.TestCase):
    def _conjunction(self, moon_start: float, moon_speed: float):
        return self._conjunction_from(SweepingMoonProvider(moon_start, moon_speed))

    def _conjunction_from(self, provider: FixtureProvider):
        chart = _utc_unknown(provider)
        assessment = chart.unknown_time_assessment
        assert assessment is not None
        return assessment.aspects["sun|moon|conjunction"]

    def test_aspect_enters_orb_during_the_day(self) -> None:
        item = self._conjunction(10.0, -15.0)
        self.assertEqual(item.presence, "partial")
        self.assertIsNotNone(item.enter_at)
        self.assertEqual(item.classification, "uncertain")

    def test_aspect_leaves_orb_during_the_day(self) -> None:
        item = self._conjunction(0.0, 15.0)
        self.assertEqual(item.presence, "partial")
        self.assertIsNotNone(item.leave_at)
        self.assertEqual(item.classification, "uncertain")

    def test_aspect_enters_and_leaves_the_same_day(self) -> None:
        item = self._conjunction(12.0, -30.0)
        self.assertEqual(item.presence, "partial")
        self.assertIsNotNone(item.enter_at)
        self.assertIsNotNone(item.leave_at)
        self.assertLess(item.enter_at, item.leave_at)

    def test_applying_becomes_separating_around_exact(self) -> None:
        item = self._conjunction(12.0, -30.0)
        self.assertTrue(item.exact_hit)
        self.assertFalse(item.phase_stable)
        self.assertIn("applying", item.phases)
        self.assertIn("separating", item.phases)
        self.assertEqual(item.classification, "uncertain")

    def test_all_day_conjunction_is_stable_when_bound_cannot_leave(self) -> None:
        item = self._conjunction(1.0, 0.1)
        self.assertEqual(item.presence, "all_day")
        self.assertEqual(item.classification, "stable")
        self.assertTrue(item.phase_stable)

    def test_mercury_station_is_uncertain_motion(self) -> None:
        chart = _utc_unknown(MercuryStationProvider())
        assert chart.unknown_time_assessment is not None
        mercury = chart.unknown_time_assessment.bodies["mercury"]
        self.assertTrue(mercury.station_in_interval)
        self.assertEqual(mercury.classification, "uncertain")
        self.assertEqual(mercury.motion_status, "uncertain")
        self.assertNotIn("motionDirection", mercury.stable_properties)


class BoundEnclosureTests(unittest.TestCase):
    def test_endpoint_speed_is_not_proof_without_accel_enclosure(self) -> None:
        dt = 1.0 / 12.0
        self.assertTrue(segment_may_station("mercury", 0.05, 0.05, dt))
        self.assertFalse(segment_may_station("sun", 1.0, 1.0, dt))
        self.assertGreater(conservative_speed("moon", 0.1), 0.1 * 1.25)

    def test_hidden_station_between_coarse_samples(self) -> None:
        chart = _utc_unknown(HiddenStationProvider())
        assert chart.unknown_time_assessment is not None
        mercury = chart.unknown_time_assessment.bodies["mercury"]
        self.assertTrue(
            mercury.station_in_interval or mercury.motion_status == "uncertain"
        )
        self.assertEqual(mercury.classification, "uncertain")
        self.assertNotIn("motionDirection", mercury.stable_properties)

    def test_hidden_aspect_enter_leave_between_coarse_samples(self) -> None:
        item = SyntheticAspectIntervalTests()._conjunction_from(HiddenEnterLeaveProvider())
        self.assertEqual(item.presence, "partial")
        self.assertIsNotNone(item.enter_at)
        self.assertIsNotNone(item.leave_at)
        self.assertEqual(item.classification, "uncertain")

    def test_moon_same_sign_still_has_time_dependent_longitude(self) -> None:
        chart = _utc_unknown(SweepingMoonProvider(10.0, 0.5))
        assert chart.unknown_time_assessment is not None
        moon = chart.unknown_time_assessment.bodies["moon"]
        self.assertFalse(moon.sign_changed)
        self.assertEqual(moon.sign_status, "stable")
        self.assertIn(PROPERTY_SIGN, moon.stable_properties)
        self.assertEqual(moon.longitude_status, "uncertain")
        self.assertIn(PROPERTY_LONGITUDE, moon.uncertain_properties)
        self.assertGreater(moon.longitude_range, 0.0)
        self.assertAlmostEqual(moon.anchor_longitude, chart.bodies["moon"].longitude)
        self.assertNotIn("longitude", moon.to_dict()["stableProperties"])

    def test_evaluation_cap_fail_closed_never_returns_stable(self) -> None:
        with patch("gbc_astro.uncertainty.assess.MAX_ASSESSMENT_EVALUATIONS", 8):
            chart = AstrologyEngine(
                provider=HiddenStationProvider(),
                house_calculator=FixtureHouseCalculator(),
            ).natal("1992-11-03", "UTC", 0.0, 0.0, unknown_time=True)
        assessment = chart.unknown_time_assessment
        assert assessment is not None
        self.assertFalse(assessment.assessment_complete)
        self.assertTrue(assessment.evaluation_budget_exhausted)
        payload = chart.to_dict()["unknownTimeAssessment"]
        self.assertFalse(payload["assessmentComplete"])
        self.assertFalse(payload["provenance"]["assessmentComplete"])
        self.assertTrue(assessment.bodies)
        for body in assessment.bodies.values():
            self.assertEqual(body.classification, "uncertain")
            self.assertEqual(body.sign_status, "uncertain")
            self.assertEqual(body.motion_status, "uncertain")
            self.assertIn(REASON_EVALUATION_LIMIT, body.reasons)
            self.assertEqual(body.stable_properties, ())
            self.assertIn(PROPERTY_LONGITUDE, body.uncertain_properties)
        for aspect in assessment.aspects.values():
            self.assertEqual(aspect.classification, "uncertain")
            self.assertIn(REASON_EVALUATION_LIMIT, aspect.reasons)


if __name__ == "__main__":
    unittest.main()
