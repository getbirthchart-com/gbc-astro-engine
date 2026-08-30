"""Unknown-time uncertainty assessment: bodies, aspects, hash, API, bounds."""

from __future__ import annotations

import os
import unittest
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from gbc_astro import AstrologyEngine, calculate_chart
from gbc_astro.api.app import create_app
from gbc_astro.constants import BODY_IDS
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.resolve import resolve_calculation_profile
from gbc_astro.providers.swiss import SwissEphemerisProvider
from gbc_astro.uncertainty.constants import (
    ANCHOR,
    ASSESSMENT_VERSION,
    MAX_ASSESSMENT_EVALUATIONS,
    PROPERTY_LONGITUDE,
    PROPERTY_SIGN,
    REASON_EVALUATION_LIMIT,
    UNAVAILABLE_WITHOUT_BIRTH_TIME,
)
from gbc_astro.validation.reproducibility import (
    calculation_hash,
    calculation_identity_payload,
)
from tests.helpers import FixtureHouseCalculator, FixtureProvider

HANOI = {
    "local_datetime": "1992-11-03T14:35:00",
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542,
}
UNKNOWN_HANOI = {
    "local_datetime": "1992-11-03",
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542,
    "unknown_time": True,
}


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


def _swiss_engine(profile=None) -> AstrologyEngine:
    path = os.environ["GBC_SWISS_EPHE_PATH"]
    kwargs = {
        "provider": SwissEphemerisProvider(ephemeris_path=path),
        "house_calculator": SwissHouseCalculator(ephemeris_path=path),
    }
    if profile is not None:
        kwargs["profile"] = profile
    return AstrologyEngine(**kwargs)


def _fixture_engine(profile=None) -> AstrologyEngine:
    kwargs = {
        "provider": FixtureProvider(),
        "house_calculator": FixtureHouseCalculator(),
    }
    if profile is not None:
        kwargs["profile"] = profile
    return AstrologyEngine(**kwargs)


class CountingProvider:
    def __init__(self, inner: SwissEphemerisProvider | FixtureProvider) -> None:
        self._inner = inner
        self.calls = 0

    def __getattr__(self, name: str):
        return getattr(self._inner, name)

    def position(self, body: str, instant_utc: datetime):
        self.calls += 1
        return self._inner.position(body, instant_utc)


class FixtureUnknownTimeTests(unittest.TestCase):
    def test_known_time_does_not_run_or_emit_assessment(self) -> None:
        counter = CountingProvider(FixtureProvider())
        engine = AstrologyEngine(
            provider=counter,
            house_calculator=FixtureHouseCalculator(),
        )
        chart = engine.natal(**HANOI)
        self.assertIsNone(chart.unknown_time_assessment)
        self.assertNotIn("unknownTimeAssessment", chart.to_dict())
        self.assertNotIn("unknownTimeAssessment", calculation_identity_payload(chart))
        self.assertEqual(counter.calls, len(BODY_IDS))

    def test_unknown_time_keeps_midnight_anchor_and_lists_unavailable(self) -> None:
        chart = _fixture_engine().natal(**UNKNOWN_HANOI)
        self.assertFalse(chart.subject.birth_time_known)
        self.assertEqual(chart.subject.local_datetime, "1992-11-03T00:00:00")
        self.assertEqual(chart.angles, {})
        self.assertEqual(chart.houses, ())
        self.assertNotIn("vertex", chart.points)
        self.assertNotIn("part_of_fortune", chart.points)
        self.assertEqual(chart.warnings[0].code, "UNKNOWN_BIRTH_TIME")
        assessment = chart.unknown_time_assessment
        assert assessment is not None
        self.assertEqual(assessment.version, ASSESSMENT_VERSION)
        self.assertEqual(assessment.anchor, ANCHOR)
        self.assertEqual(assessment.unavailable, UNAVAILABLE_WITHOUT_BIRTH_TIME)
        payload = chart.to_dict()["unknownTimeAssessment"]
        self.assertEqual(payload["anchor"], "start_of_local_day")
        self.assertIn("vertex", payload["unavailable"])
        self.assertIn("partOfFortune", payload["unavailable"])
        self.assertAlmostEqual(
            assessment.bodies["moon"].start_longitude,
            chart.bodies["moon"].longitude,
        )
        self.assertAlmostEqual(
            assessment.bodies["moon"].anchor_longitude,
            chart.bodies["moon"].longitude,
        )
        moon = assessment.bodies["moon"]
        self.assertEqual(moon.longitude_status, "uncertain")
        self.assertIn(PROPERTY_LONGITUDE, moon.uncertain_properties)
        self.assertNotIn("longitude", moon.stable_properties)
        self.assertTrue(assessment.assessment_complete)
        self.assertTrue(chart.to_dict()["unknownTimeAssessment"]["assessmentComplete"])

    def test_unknown_time_placidus_still_has_no_houses(self) -> None:
        chart = _fixture_engine().natal(**UNKNOWN_HANOI, house_system="placidus")
        self.assertEqual(chart.houses, ())
        self.assertEqual(chart.angles, {})
        self.assertIsNone(chart.meta.house_system)
        self.assertEqual(chart.meta.requested_house_system, "placidus")

    def test_repeated_unknown_time_assessment_and_hash_are_deterministic(self) -> None:
        engine = _fixture_engine()
        first = engine.natal(**UNKNOWN_HANOI)
        second = engine.natal(**UNKNOWN_HANOI)
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(calculation_hash(first), calculation_hash(second))
        self.assertIn("unknownTimeAssessment", calculation_identity_payload(first))
        identity = calculation_identity_payload(first)["unknownTimeAssessment"]
        self.assertNotIn("ephemerisEvaluations", identity)
        self.assertNotIn("provenance", identity)
        self.assertIn("assessmentComplete", identity)
        self.assertTrue(identity["assessmentComplete"])
        self.assertEqual(identity["frame"]["zodiac"], "tropical")
        self.assertNotIn("ayanamsa", identity["frame"])

    def test_presentation_wording_does_not_change_hash(self) -> None:
        from dataclasses import replace

        chart = _fixture_engine().natal(**UNKNOWN_HANOI)
        noisy = replace(
            chart,
            warnings=(replace(chart.warnings[0], message="rewritten copy"),),
        )
        self.assertEqual(calculation_hash(chart), calculation_hash(noisy))

    def test_evaluation_bound_on_fixture_is_the_coarse_grid(self) -> None:
        counter = CountingProvider(FixtureProvider())
        engine = AstrologyEngine(
            provider=counter,
            house_calculator=FixtureHouseCalculator(),
        )
        chart = engine.natal(**UNKNOWN_HANOI)
        assert chart.unknown_time_assessment is not None
        self.assertGreaterEqual(
            chart.unknown_time_assessment.ephemeris_evaluations,
            156,
        )
        self.assertLessEqual(
            chart.unknown_time_assessment.ephemeris_evaluations,
            MAX_ASSESSMENT_EVALUATIONS,
        )
        self.assertLessEqual(counter.calls, len(BODY_IDS) + MAX_ASSESSMENT_EVALUATIONS)
        self.assertTrue(chart.unknown_time_assessment.assessment_complete)

    def test_python_unknown_time_includes_assessment(self) -> None:
        python = calculate_chart(
            "1992-11-03",
            time=None,
            latitude=21.0285,
            longitude=105.8542,
            timezone="Asia/Ho_Chi_Minh",
            engine=_fixture_engine(),
        ).to_dict()
        self.assertIn("unknownTimeAssessment", python)
        self.assertEqual(python["schemaVersion"], "1.9.0")
        self.assertNotIn("vertex", python["points"])
        self.assertEqual(python["unknownTimeAssessment"]["anchor"], ANCHOR)


@unittest.skipUnless(_swiss_available(), "Unknown-time astronomy needs Swiss Ephemeris data")
class SwissUnknownTimeAstronomyTests(unittest.TestCase):
    def _unknown(self, local_date: str, timezone: str, lat: float, lng: float, **kwargs):
        profile = kwargs.pop("profile", None)
        return _swiss_engine(profile).natal(
            local_date,
            timezone,
            lat,
            lng,
            unknown_time=True,
            **kwargs,
        )

    def test_moon_stays_in_one_sign_on_hanoi_1992_11_03(self) -> None:
        chart = self._unknown("1992-11-03", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
        moon = chart.unknown_time_assessment.bodies["moon"]
        self.assertFalse(moon.sign_changed)
        self.assertEqual(moon.classification, "stable")
        self.assertEqual(moon.sign_status, "stable")
        self.assertEqual(len(moon.possible_signs), 1)
        self.assertIn(PROPERTY_SIGN, moon.stable_properties)
        self.assertEqual(moon.longitude_status, "uncertain")
        self.assertIn(PROPERTY_LONGITUDE, moon.uncertain_properties)
        self.assertGreater(moon.longitude_range, 0.0)
        self.assertAlmostEqual(moon.anchor_longitude, chart.bodies["moon"].longitude)

    def test_moon_changes_sign_during_the_day(self) -> None:
        chart = self._unknown("2024-01-03", "UTC", 0.0, 0.0)
        moon = chart.unknown_time_assessment.bodies["moon"]
        self.assertTrue(moon.sign_changed)
        self.assertGreaterEqual(len(moon.possible_signs), 2)
        self.assertEqual(moon.classification, "uncertain")

    def test_sun_near_zero_aries_is_a_non_moon_boundary_and_wrap(self) -> None:
        chart = self._unknown("2024-03-20", "UTC", 0.0, 0.0)
        sun = chart.unknown_time_assessment.bodies["sun"]
        self.assertTrue(sun.sign_changed)
        self.assertEqual(set(sun.possible_signs), {"pisces", "aries"})
        self.assertLess(sun.longitude_range, 5.0)
        self.assertGreater(sun.start_longitude, 350.0)
        self.assertLess(sun.end_longitude, 10.0)
        self.assertIn("wrap_unwrapped", sun.reasons)

    def test_moon_wrap_range_is_not_near_360(self) -> None:
        chart = self._unknown("2024-01-16", "UTC", 0.0, 0.0)
        moon = chart.unknown_time_assessment.bodies["moon"]
        self.assertLess(moon.longitude_range, 30.0)
        self.assertGreater(moon.start_longitude, 340.0)
        self.assertLess(moon.end_longitude, 30.0)

    def test_aspect_all_day_versus_partial(self) -> None:
        chart = self._unknown("1992-11-03", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
        assessments = chart.unknown_time_assessment.aspects
        self.assertTrue(assessments)
        self.assertTrue(any(item.presence == "all_day" for item in assessments.values()))
        changing = self._unknown("2024-01-03", "UTC", 0.0, 0.0)
        partial = [
            item
            for item in changing.unknown_time_assessment.aspects.values()
            if item.presence == "partial"
        ]
        self.assertTrue(partial)
        self.assertTrue(any(item.enter_at is not None for item in partial))
        self.assertTrue(any(item.leave_at is not None for item in partial))

    def test_exact_hit_marks_phase_uncertain(self) -> None:
        chart = self._unknown("2024-01-03", "UTC", 0.0, 0.0)
        hits = [
            item
            for item in chart.unknown_time_assessment.aspects.values()
            if item.exact_hit
        ]
        self.assertTrue(hits)
        for item in hits:
            self.assertEqual(item.classification, "uncertain")
            self.assertFalse(item.phase_stable)

    def test_custom_orb_changes_presence(self) -> None:
        wide = resolve_calculation_profile(
            aspect_preset="custom",
            custom_aspect_rules=[{"type": "conjunction", "exact_angle": 0, "orb": 12}],
        )
        tight = resolve_calculation_profile(
            aspect_preset="custom",
            custom_aspect_rules=[{"type": "conjunction", "exact_angle": 0, "orb": 1}],
        )
        wide_chart = self._unknown(
            "1992-11-03",
            "Asia/Ho_Chi_Minh",
            21.0285,
            105.8542,
            profile=wide,
        )
        tight_chart = self._unknown(
            "1992-11-03",
            "Asia/Ho_Chi_Minh",
            21.0285,
            105.8542,
            profile=tight,
        )
        self.assertGreater(
            len(wide_chart.unknown_time_assessment.aspects),
            len(tight_chart.unknown_time_assessment.aspects),
        )
        self.assertTrue(
            all(
                item.exact_angle == 0.0
                for item in wide_chart.unknown_time_assessment.aspects.values()
            )
        )

    def test_extended_assessment_is_a_superset_of_standard_keys(self) -> None:
        standard = self._unknown("1992-11-03", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
        extended = self._unknown(
            "1992-11-03",
            "Asia/Ho_Chi_Minh",
            21.0285,
            105.8542,
            profile=resolve_calculation_profile(aspect_preset="extended"),
        )
        standard_keys = set(standard.unknown_time_assessment.aspects)
        extended_keys = set(extended.unknown_time_assessment.aspects)
        self.assertTrue(standard_keys <= extended_keys)
        self.assertGreater(len(extended_keys), len(standard_keys))

    def test_mean_versus_true_node_assessment(self) -> None:
        true_chart = self._unknown("1992-11-03", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
        mean_chart = self._unknown(
            "1992-11-03",
            "Asia/Ho_Chi_Minh",
            21.0285,
            105.8542,
            profile=resolve_calculation_profile(node_type="mean"),
        )
        true_keys = set(true_chart.unknown_time_assessment.aspects)
        mean_keys = set(mean_chart.unknown_time_assessment.aspects)
        self.assertTrue(any("true_node" in key for key in true_keys))
        self.assertFalse(any("mean_node" in key for key in true_keys))
        self.assertTrue(any("mean_node" in key for key in mean_keys))
        self.assertFalse(any("true_node" in key for key in mean_keys))
        self.assertIn("true_node", true_chart.unknown_time_assessment.bodies)
        self.assertIn("mean_node", mean_chart.unknown_time_assessment.bodies)

    def test_opt_in_lilith_is_assessed_and_not_aspected(self) -> None:
        chart = self._unknown(
            "1992-11-03",
            "Asia/Ho_Chi_Minh",
            21.0285,
            105.8542,
            profile=resolve_calculation_profile(additional_points=["mean_lilith"]),
        )
        self.assertIn("mean_lilith", chart.unknown_time_assessment.bodies)
        self.assertIn("mean_lilith", chart.bodies)
        self.assertFalse(
            any("mean_lilith" in key for key in chart.unknown_time_assessment.aspects)
        )

    def test_dst_and_historical_dates_produce_assessments(self) -> None:
        spring = self._unknown("2024-03-10", "America/New_York", 40.7, -74.0)
        fall = self._unknown("2024-11-03", "America/New_York", 40.7, -74.0)
        historical = self._unknown("1950-06-15", "America/New_York", 40.7, -74.0)
        for chart in (spring, fall, historical):
            assessment = chart.unknown_time_assessment
            assert assessment is not None
            self.assertEqual(assessment.anchor, ANCHOR)
            self.assertEqual(chart.angles, {})
            duration = (
                datetime.fromisoformat(assessment.interval["endUtc"].replace("Z", "+00:00"))
                - datetime.fromisoformat(assessment.interval["startUtc"].replace("Z", "+00:00"))
            )
            hours = duration.total_seconds() / 3600.0
            self.assertGreater(hours, 20.0)
            self.assertLess(hours, 28.0)
        spring_hours = (
            datetime.fromisoformat(
                spring.unknown_time_assessment.interval["endUtc"].replace("Z", "+00:00")
            )
            - datetime.fromisoformat(
                spring.unknown_time_assessment.interval["startUtc"].replace("Z", "+00:00")
            )
        ).total_seconds() / 3600.0
        fall_hours = (
            datetime.fromisoformat(
                fall.unknown_time_assessment.interval["endUtc"].replace("Z", "+00:00")
            )
            - datetime.fromisoformat(
                fall.unknown_time_assessment.interval["startUtc"].replace("Z", "+00:00")
            )
        ).total_seconds() / 3600.0
        self.assertLess(spring_hours, 24.0)
        self.assertGreater(fall_hours, 24.0)

    def test_mercury_station_day_is_uncertain_motion(self) -> None:
        chart = self._unknown("2023-12-13", "UTC", 0.0, 0.0)
        mercury = chart.unknown_time_assessment.bodies["mercury"]
        self.assertTrue(mercury.station_in_interval or mercury.classification == "uncertain")
        self.assertGreaterEqual(len(mercury.motion_states), 1)

    def test_known_time_hanoi_astronomy_unchanged(self) -> None:
        engine = _swiss_engine()
        known = engine.natal(**HANOI)
        self.assertIsNone(known.unknown_time_assessment)
        self.assertEqual(known.schema_version, "1.9.0")
        self.assertIn("ascendant", known.angles)
        self.assertEqual(len(known.houses), 12)
        self.assertIn("vertex", known.points)
        self.assertIn("part_of_fortune", known.points)

    def test_http_unknown_time_matches_python(self) -> None:
        engine = _swiss_engine()
        python = engine.natal(**UNKNOWN_HANOI).to_dict()
        with TestClient(create_app()) as client:
            response = client.post(
                "/v1/charts/natal",
                json={
                    "local_date": "1992-11-03",
                    "unknown_time": True,
                    "timezone": "Asia/Ho_Chi_Minh",
                    "latitude": 21.0285,
                    "longitude": 105.8542,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), python)
        self.assertEqual(response.json()["unknownTimeAssessment"]["anchor"], ANCHOR)

    def test_swiss_evaluation_bound(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        counter = CountingProvider(SwissEphemerisProvider(ephemeris_path=path))
        engine = AstrologyEngine(
            provider=counter,
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        chart = engine.natal(**UNKNOWN_HANOI)
        assert chart.unknown_time_assessment is not None
        self.assertLessEqual(
            chart.unknown_time_assessment.ephemeris_evaluations,
            MAX_ASSESSMENT_EVALUATIONS,
        )
        self.assertFalse(chart.unknown_time_assessment.evaluation_budget_exhausted)
        self.assertTrue(chart.unknown_time_assessment.assessment_complete)
        self.assertLessEqual(counter.calls, len(BODY_IDS) + MAX_ASSESSMENT_EVALUATIONS)


class FailClosedCapTests(unittest.TestCase):
    def test_patched_cap_fail_closes_fixture_unknown_time(self) -> None:
        with patch("gbc_astro.uncertainty.assess.MAX_ASSESSMENT_EVALUATIONS", 8):
            counter = CountingProvider(FixtureProvider())
            engine = AstrologyEngine(
                provider=counter,
                house_calculator=FixtureHouseCalculator(),
            )
            chart = engine.natal(**UNKNOWN_HANOI)
        assessment = chart.unknown_time_assessment
        assert assessment is not None
        self.assertFalse(assessment.assessment_complete)
        self.assertTrue(assessment.evaluation_budget_exhausted)
        self.assertEqual(
            chart.to_dict()["unknownTimeAssessment"]["assessmentComplete"],
            False,
        )
        self.assertGreater(counter.calls, len(BODY_IDS))
        for body in assessment.bodies.values():
            self.assertEqual(body.classification, "uncertain")
            self.assertIn(REASON_EVALUATION_LIMIT, body.reasons)
            self.assertEqual(body.stable_properties, ())
        for aspect in assessment.aspects.values():
            self.assertEqual(aspect.classification, "uncertain")

    def test_known_time_still_has_no_assessment_when_cap_is_patched(self) -> None:
        with patch("gbc_astro.uncertainty.assess.MAX_ASSESSMENT_EVALUATIONS", 8):
            chart = _fixture_engine().natal(**HANOI)
        self.assertIsNone(chart.unknown_time_assessment)
        self.assertNotIn("unknownTimeAssessment", chart.to_dict())


class LinearAspectClassificationTests(unittest.TestCase):
    """Synthetic longitudes: enter, leave, enter-then-leave, applying to separating."""

    def test_unwrap_helper_covers_enter_leave_math(self) -> None:
        from gbc_astro.astronomy.circular import shortest_angular_distance

        # Conjunction orb 5°. Body A fixed at 0°, B moves 10 → 0 → 10.
        longitudes = (10.0, 6.0, 4.0, 0.0, 4.0, 6.0, 10.0)
        orbs = [abs(shortest_angular_distance(0.0, lon) - 0.0) for lon in longitudes]
        in_orb = [orb <= 5.0 for orb in orbs]
        self.assertEqual(in_orb[0], False)
        self.assertEqual(in_orb[2], True)
        self.assertEqual(in_orb[3], True)
        self.assertEqual(in_orb[-1], False)
        self.assertTrue(any(in_orb) and not all(in_orb))
        self.assertEqual(min(orbs), 0.0)


if __name__ == "__main__":
    unittest.main()
