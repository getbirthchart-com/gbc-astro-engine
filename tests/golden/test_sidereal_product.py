"""Sidereal Lahiri product-facing readiness: frame, settings, hash, parity."""

from __future__ import annotations

import json
import os
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from gbc_astro import AstrologyEngine, calculate_chart
from gbc_astro.api.app import create_app
from gbc_astro.astronomy.circular import normalize_longitude, shortest_angular_distance
from gbc_astro.cli import _build_parser
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.ayanamsa import RECOMMENDED_PRODUCT_AYANAMSHA
from gbc_astro.providers.swiss import SwissEphemerisProvider
from gbc_astro.uncertainty.constants import (
    PROPERTY_LONGITUDE,
    REASON_EVALUATION_LIMIT,
    UNAVAILABLE_WITHOUT_BIRTH_TIME,
)
from gbc_astro.validation.reproducibility import (
    calculation_hash,
    calculation_identity_payload,
)
from gbc_astro.zodiac.sidereal import AyanamsaCalculator, resolve_ayanamsa_profile

FACADE = {
    "date": "1992-11-03",
    "time": "14:35:00",
    "latitude": 21.0285,
    "longitude": 105.8542,
    "timezone": "Asia/Ho_Chi_Minh",
}
HTTP_HANOI = {
    "local_date": "1992-11-03",
    "local_time": "14:35:00",
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542,
}
GOLDEN = Path(__file__).parents[1] / "fixtures" / "public_golden_cases.json"
SIDEREAL = {"zodiac": "sidereal", "ayanamsa": "lahiri"}


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


def _swiss_engine() -> AstrologyEngine:
    path = os.environ["GBC_SWISS_EPHE_PATH"]
    return AstrologyEngine(
        provider=SwissEphemerisProvider(ephemeris_path=path),
        house_calculator=SwissHouseCalculator(ephemeris_path=path),
    )


@unittest.skipUnless(_swiss_available(), "Sidereal product tests need Swiss Ephemeris data")
class SiderealLahiriContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _swiss_engine()
        self.tropical = calculate_chart(**FACADE, engine=self.engine)
        self.sidereal = calculate_chart(**FACADE, engine=self.engine, **SIDEREAL)

    def test_omitted_tropical_equals_explicit_tropical(self) -> None:
        explicit = calculate_chart(**FACADE, engine=self.engine, zodiac="tropical")
        self.assertEqual(self.tropical.to_json(), explicit.to_json())
        self.assertEqual(calculation_hash(self.tropical), calculation_hash(explicit))
        self.assertEqual(self.tropical.meta.zodiac, "tropical")
        self.assertIsNone(self.tropical.meta.ayanamsa)
        self.assertNotIn("productExposureApproved", self.tropical.to_dict()["meta"])

    def test_lahiri_matches_swiss_ayanamsa_ut(self) -> None:
        profile = resolve_ayanamsa_profile("lahiri")
        swiss = AyanamsaCalculator(ephemeris_path=os.environ["GBC_SWISS_EPHE_PATH"])
        expected = swiss.value(self.sidereal.subject.julian_day, profile)
        assert self.sidereal.meta.ayanamsa_degrees is not None
        self.assertAlmostEqual(self.sidereal.meta.ayanamsa_degrees, expected, places=9)
        rotated = normalize_longitude(self.tropical.bodies["sun"].longitude - expected)
        self.assertAlmostEqual(self.sidereal.bodies["sun"].longitude, rotated, places=9)

    def test_tropical_then_sidereal_then_tropical_does_not_leak(self) -> None:
        baseline = calculate_chart(**FACADE, engine=self.engine)
        calculate_chart(**FACADE, engine=self.engine, **SIDEREAL)
        after = calculate_chart(**FACADE, engine=self.engine)
        self.assertEqual(baseline.to_json(), after.to_json())
        self.assertEqual(calculation_hash(baseline), calculation_hash(after))

    def test_planet_to_planet_separations_are_invariant(self) -> None:
        bodies = sorted(self.tropical.bodies)
        for i, left in enumerate(bodies):
            for right in bodies[i + 1 :]:
                tropical_sep = abs(
                    shortest_angular_distance(
                        self.tropical.bodies[left].longitude,
                        self.tropical.bodies[right].longitude,
                    )
                )
                sidereal_sep = abs(
                    shortest_angular_distance(
                        self.sidereal.bodies[left].longitude,
                        self.sidereal.bodies[right].longitude,
                    )
                )
                self.assertAlmostEqual(tropical_sep, sidereal_sep, places=9)

    def test_signs_and_placidus_houses_follow_the_frame(self) -> None:
        differing_signs = [
            body_id
            for body_id, body in self.tropical.bodies.items()
            if body.sign != self.sidereal.bodies[body_id].sign
        ]
        self.assertGreater(len(differing_signs), 5)
        for body_id, body in self.tropical.bodies.items():
            self.assertEqual(body.house, self.sidereal.bodies[body_id].house, body_id)

    def test_hanoi_golden_tropical_longitudes_and_aspect_count_unchanged(self) -> None:
        expected = json.loads(GOLDEN.read_text())[0]["expected"]
        self.assertAlmostEqual(
            self.tropical.bodies["sun"].longitude, expected["sun_longitude"]
        )
        self.assertAlmostEqual(
            self.tropical.bodies["moon"].longitude, expected["moon_longitude"]
        )
        self.assertEqual(len(self.tropical.aspects), expected["aspect_count"])
        self.assertEqual(self.tropical.to_dict()["schemaVersion"], "1.9.0")

    def test_metadata_records_lahiri_without_product_gate_on_the_chart(self) -> None:
        meta = self.sidereal.to_dict()["meta"]
        self.assertEqual(meta["zodiac"], "sidereal")
        self.assertEqual(meta["ayanamsa"], "lahiri")
        self.assertEqual(meta["ayanamsha"], "lahiri")
        self.assertEqual(meta["ayanamsaVersion"], "1.0.0")
        self.assertGreater(meta["ayanamsaDegrees"], 23.0)
        self.assertLess(meta["ayanamsaDegrees"], 25.0)
        self.assertNotIn("productExposureApproved", meta)

    def test_hash_identity_separates_frames_and_ignores_product_gate(self) -> None:
        again = calculate_chart(**FACADE, engine=self.engine, zodiac="sidereal", ayanamsha="lahiri")
        self.assertEqual(calculation_hash(self.sidereal), calculation_hash(again))
        self.assertNotEqual(calculation_hash(self.tropical), calculation_hash(self.sidereal))
        identity = calculation_identity_payload(self.sidereal)
        self.assertEqual(identity["settings"]["zodiac"], "sidereal")
        self.assertEqual(identity["settings"]["ayanamsa"], "lahiri")
        self.assertIn("ayanamsaDegrees", identity["settings"])
        encoded = json.dumps(identity)
        self.assertNotIn("productExposureApproved", encoded)
        self.assertNotIn("ayanamsha", encoded)

    def test_two_sidereal_setting_profiles_do_not_mutate_shared_engine(self) -> None:
        whole = self.engine.with_settings(
            zodiac="sidereal", ayanamsa="lahiri", house_system="whole_sign"
        )
        equal = self.engine.with_settings(
            zodiac="sidereal", ayanamsa="lahiri", house_system="equal"
        )
        whole_chart = whole.natal(
            "1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542
        )
        equal_chart = equal.natal(
            "1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542
        )
        leftover = self.engine.natal(
            "1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542
        )
        self.assertEqual(whole_chart.meta.house_system, "whole_sign")
        self.assertEqual(equal_chart.meta.house_system, "equal")
        self.assertEqual(leftover.meta.zodiac, "tropical")
        self.assertEqual(leftover.meta.house_system, "placidus")
        self.assertNotEqual(calculation_hash(whole_chart), calculation_hash(equal_chart))


@unittest.skipUnless(_swiss_available(), "Sidereal settings need Swiss Ephemeris data")
class SiderealSettingsInteractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _swiss_engine()

    def _chart(self, **overrides: object):
        return calculate_chart(**FACADE, engine=self.engine, **SIDEREAL, **overrides)

    def test_sidereal_placidus_whole_sign_and_equal(self) -> None:
        placidus = self._chart(house_system="placidus")
        whole = self._chart(house_system="whole_sign")
        equal = self._chart(house_system="equal")
        for chart, system in (
            (placidus, "placidus"),
            (whole, "whole_sign"),
            (equal, "equal"),
        ):
            self.assertEqual(chart.meta.zodiac, "sidereal")
            self.assertEqual(chart.meta.ayanamsa, "lahiri")
            self.assertEqual(chart.meta.house_system, system)
        tropical_whole = calculate_chart(
            **FACADE, engine=self.engine, house_system="whole_sign"
        )
        self.assertNotEqual(
            tropical_whole.houses[0].cusp_longitude, whole.houses[0].cusp_longitude
        )
        self.assertAlmostEqual(whole.houses[0].degree_in_sign, 0.0, places=9)

    def test_sidereal_true_and_mean_node(self) -> None:
        true_chart = self._chart(node_type="true")
        mean_chart = self._chart(node_type="mean")
        self.assertEqual(true_chart.meta.node_type, "true")
        self.assertEqual(mean_chart.meta.node_type, "mean")
        self.assertIn("true_node", true_chart.bodies)
        self.assertIn("mean_node", mean_chart.bodies)
        self.assertNotEqual(
            true_chart.bodies["true_node"].longitude,
            mean_chart.bodies["mean_node"].longitude,
        )

    def test_sidereal_standard_extended_custom_aspects(self) -> None:
        standard = self._chart(aspect_preset="standard")
        extended = self._chart(aspect_preset="extended")
        custom = self._chart(
            aspect_preset="custom",
            custom_aspect_rules=[{"type": "conjunction", "exact_angle": 0, "orb": 6}],
        )
        self.assertEqual(standard.meta.aspect_preset, "standard")
        self.assertEqual(extended.meta.aspect_preset, "extended")
        self.assertEqual(custom.meta.aspect_preset, "custom")
        self.assertGreater(len(extended.aspects), len(standard.aspects))
        self.assertTrue(all(aspect.aspect_type == "conjunction" for aspect in custom.aspects))

    def test_sidereal_mean_and_true_lilith(self) -> None:
        chart = self._chart(additional_points=["mean_lilith", "true_lilith"])
        tropical = calculate_chart(
            **FACADE, engine=self.engine, additional_points=["mean_lilith", "true_lilith"]
        )
        self.assertIn("mean_lilith", chart.bodies)
        self.assertIn("true_lilith", chart.bodies)
        assert chart.meta.ayanamsa_degrees is not None
        self.assertAlmostEqual(
            normalize_longitude(
                tropical.bodies["mean_lilith"].longitude - chart.meta.ayanamsa_degrees
            ),
            chart.bodies["mean_lilith"].longitude,
            places=9,
        )
        self.assertEqual(chart.meta.additional_points, ("mean_lilith", "true_lilith"))

    def test_sidereal_pof_and_vertex_known_time(self) -> None:
        chart = self._chart()
        self.assertIn("vertex", chart.points)
        self.assertIn("part_of_fortune", chart.points)
        tropical = self.engine.natal(
            "1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542
        )
        assert chart.meta.ayanamsa_degrees is not None
        self.assertAlmostEqual(
            normalize_longitude(
                tropical.points["vertex"].longitude - chart.meta.ayanamsa_degrees
            ),
            chart.points["vertex"].longitude,
            places=9,
        )


@unittest.skipUnless(_swiss_available(), "Sidereal unknown-time needs Swiss Ephemeris data")
class SiderealUnknownTimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _swiss_engine()

    def test_sidereal_unknown_time_stays_in_lahiri_frame(self) -> None:
        chart = calculate_chart(
            "1992-11-03",
            None,
            latitude=21.0285,
            longitude=105.8542,
            timezone="Asia/Ho_Chi_Minh",
            engine=self.engine,
            **SIDEREAL,
        )
        assessment = chart.unknown_time_assessment
        assert assessment is not None
        self.assertEqual(chart.angles, {})
        self.assertEqual(chart.houses, ())
        self.assertNotIn("vertex", chart.points)
        self.assertNotIn("part_of_fortune", chart.points)
        self.assertEqual(tuple(assessment.unavailable), UNAVAILABLE_WITHOUT_BIRTH_TIME)
        payload = chart.to_dict()["unknownTimeAssessment"]
        self.assertEqual(payload["provenance"]["frame"]["zodiac"], "sidereal")
        self.assertEqual(payload["provenance"]["frame"]["ayanamsa"], "lahiri")
        self.assertEqual(payload["algorithmVersion"], "uniform-jd-v1.1")
        self.assertTrue(payload["assessmentComplete"])
        moon = assessment.bodies["moon"]
        self.assertEqual(moon.longitude_status, "uncertain")
        self.assertAlmostEqual(moon.anchor_longitude, chart.bodies["moon"].longitude)
        self.assertIn(chart.bodies["moon"].sign, moon.possible_signs)

    def test_tropical_and_sidereal_unknown_time_signs_differ(self) -> None:
        tropical = calculate_chart(
            "1992-11-03",
            None,
            latitude=21.0285,
            longitude=105.8542,
            timezone="Asia/Ho_Chi_Minh",
            engine=self.engine,
        )
        sidereal = calculate_chart(
            "1992-11-03",
            None,
            latitude=21.0285,
            longitude=105.8542,
            timezone="Asia/Ho_Chi_Minh",
            engine=self.engine,
            **SIDEREAL,
        )
        assert tropical.unknown_time_assessment is not None
        assert sidereal.unknown_time_assessment is not None
        tropical_signs = tropical.unknown_time_assessment.bodies["moon"].possible_signs
        sidereal_signs = sidereal.unknown_time_assessment.bodies["moon"].possible_signs
        self.assertNotEqual(tropical_signs, sidereal_signs)
        self.assertNotEqual(
            tropical.bodies["moon"].sign, sidereal.bodies["moon"].sign
        )

    def test_sidereal_unknown_time_respects_node_and_aspect_settings(self) -> None:
        mean = calculate_chart(
            "1992-11-03",
            None,
            latitude=21.0285,
            longitude=105.8542,
            timezone="Asia/Ho_Chi_Minh",
            engine=self.engine,
            node_type="mean",
            aspect_preset="extended",
            **SIDEREAL,
        )
        assert mean.unknown_time_assessment is not None
        self.assertEqual(mean.meta.node_type, "mean")
        self.assertEqual(mean.meta.aspect_preset, "extended")
        self.assertIn("mean_node", mean.unknown_time_assessment.bodies)
        self.assertFalse(
            any(
                "true_node" in (aspect.body_a, aspect.body_b)
                for aspect in mean.unknown_time_assessment.aspects.values()
            )
        )
        standard = calculate_chart(
            "1992-11-03",
            None,
            latitude=21.0285,
            longitude=105.8542,
            timezone="Asia/Ho_Chi_Minh",
            engine=self.engine,
            node_type="mean",
            **SIDEREAL,
        )
        assert standard.unknown_time_assessment is not None
        self.assertGreaterEqual(
            len(mean.unknown_time_assessment.aspects),
            len(standard.unknown_time_assessment.aspects),
        )

    def test_evaluation_cap_fail_closed_in_sidereal_unknown_time(self) -> None:
        with patch("gbc_astro.uncertainty.assess.MAX_ASSESSMENT_EVALUATIONS", 8):
            chart = calculate_chart(
                "1992-11-03",
                None,
                latitude=21.0285,
                longitude=105.8542,
                timezone="Asia/Ho_Chi_Minh",
                engine=self.engine,
                **SIDEREAL,
            )
        assessment = chart.unknown_time_assessment
        assert assessment is not None
        self.assertFalse(assessment.assessment_complete)
        self.assertTrue(assessment.evaluation_budget_exhausted)
        for body in assessment.bodies.values():
            self.assertEqual(body.classification, "uncertain")
            self.assertIn(REASON_EVALUATION_LIMIT, body.reasons)
            self.assertEqual(body.stable_properties, ())
            self.assertIn(PROPERTY_LONGITUDE, body.uncertain_properties)
        for aspect in assessment.aspects.values():
            self.assertEqual(aspect.classification, "uncertain")
            self.assertIn(REASON_EVALUATION_LIMIT, aspect.reasons)


@unittest.skipUnless(_swiss_available(), "Mixed-zodiac concurrency needs Swiss Ephemeris data")
class MixedZodiacConcurrencyTests(unittest.TestCase):
    def test_concurrent_tropical_and_sidereal_stay_deterministic(self) -> None:
        engine = _swiss_engine()
        tropical_expected = calculate_chart(**FACADE, engine=engine).bodies["sun"].longitude
        sidereal_expected = calculate_chart(
            **FACADE, engine=engine, **SIDEREAL
        ).bodies["sun"].longitude
        tropical_values: list[float] = []
        sidereal_values: list[float] = []
        errors: list[str] = []

        def tropical_worker() -> None:
            try:
                for _ in range(40):
                    tropical_values.append(
                        calculate_chart(**FACADE, engine=engine).bodies["sun"].longitude
                    )
            except Exception as exc:  # pragma: no cover - failure is the assertion
                errors.append(f"tropical:{exc}")

        def sidereal_worker() -> None:
            try:
                for _ in range(40):
                    sidereal_values.append(
                        calculate_chart(
                            **FACADE, engine=engine, **SIDEREAL
                        ).bodies["sun"].longitude
                    )
            except Exception as exc:  # pragma: no cover
                errors.append(f"sidereal:{exc}")

        original = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)
        try:
            threads = [
                threading.Thread(target=tropical_worker),
                threading.Thread(target=sidereal_worker),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        finally:
            sys.setswitchinterval(original)

        self.assertEqual(errors, [])
        self.assertTrue(tropical_values)
        self.assertTrue(sidereal_values)
        self.assertTrue(all(value == tropical_expected for value in tropical_values))
        self.assertTrue(all(value == sidereal_expected for value in sidereal_values))
        after = calculate_chart(**FACADE, engine=engine)
        self.assertEqual(after.bodies["sun"].longitude, tropical_expected)


@unittest.skipUnless(
    _swiss_available(), "HTTP/Python/CLI Sidereal parity needs Swiss Ephemeris data"
)
class SiderealPublicParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _swiss_engine()
        self.client = TestClient(create_app())

    def test_http_python_agree_for_sidereal_lahiri(self) -> None:
        python = calculate_chart(**FACADE, engine=self.engine, **SIDEREAL).to_dict()
        response = self.client.post(
            "/v1/charts/natal", json={**HTTP_HANOI, **SIDEREAL}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), python)

    def test_cli_exposes_zodiac_and_ayanamsa(self) -> None:
        natal = _build_parser().parse_args(
            [
                "natal",
                "--date",
                "1992-11-03",
                "--time",
                "14:35:00",
                "--timezone",
                "Asia/Ho_Chi_Minh",
                "--lat",
                "21.0285",
                "--lng",
                "105.8542",
                "--zodiac",
                "sidereal",
                "--ayanamsa",
                "lahiri",
            ]
        )
        self.assertEqual(natal.zodiac, "sidereal")
        self.assertEqual(natal.ayanamsa, "lahiri")

    def test_invalid_zodiac_and_ayanamsa_combinations(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError):
            calculate_chart(**FACADE, engine=self.engine, zodiac="sidereal")
        raman = calculate_chart(
            **FACADE, engine=self.engine, zodiac="sidereal", ayanamsa="raman"
        )
        lahiri = calculate_chart(**FACADE, engine=self.engine, **SIDEREAL)
        self.assertEqual(raman.meta.ayanamsa, "raman")
        self.assertNotEqual(calculation_hash(lahiri), calculation_hash(raman))
        with self.assertRaises(InvalidCalculationProfileError):
            calculate_chart(
                **FACADE, engine=self.engine, zodiac="tropical", ayanamsa="lahiri"
            )
        with self.assertRaises(InvalidCalculationProfileError):
            calculate_chart(**FACADE, engine=self.engine, zodiac="draconic")
        self.assertEqual(RECOMMENDED_PRODUCT_AYANAMSHA, "lahiri")

        missing = self.client.post(
            "/v1/charts/natal", json={**HTTP_HANOI, "zodiac": "sidereal"}
        )
        self.assertEqual(missing.status_code, 422)
        raman_http = self.client.post(
            "/v1/charts/natal",
            json={**HTTP_HANOI, "zodiac": "sidereal", "ayanamsa": "raman"},
        )
        self.assertEqual(raman_http.status_code, 200)
        self.assertEqual(raman_http.json()["meta"]["ayanamsa"], "raman")
        self.assertNotIn("productExposureApproved", raman_http.json()["meta"])
        tropical_ayanamsa = self.client.post(
            "/v1/charts/natal",
            json={**HTTP_HANOI, "zodiac": "tropical", "ayanamsa": "lahiri"},
        )
        self.assertEqual(tropical_ayanamsa.status_code, 422)


if __name__ == "__main__":
    unittest.main()
