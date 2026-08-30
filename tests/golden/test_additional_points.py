"""Public additional natal points: Chiron default, opt-in Lilith, Vertex, PoF."""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone
from importlib import import_module

from fastapi.testclient import TestClient

from gbc_astro import AstrologyEngine, calculate_chart
from gbc_astro.api.app import create_app
from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.cli import _build_parser, _parse_additional_points_arg
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.defaults import WESTERN_MODERN_V1
from gbc_astro.profiles.resolve import resolve_calculation_profile
from gbc_astro.providers.swiss import SwissEphemerisProvider
from gbc_astro.validation.reproducibility import calculation_hash
from tests.helpers import FixtureHouseCalculator, FixtureProvider

HANOI = {
    "local_datetime": "1992-11-03T14:35:00",
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542,
}
HTTP_HANOI = {
    "local_date": "1992-11-03",
    "local_time": "14:35:00",
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542,
}
FACADE = {
    "date": "1992-11-03",
    "time": "14:35:00",
    "latitude": 21.0285,
    "longitude": 105.8542,
    "timezone": "Asia/Ho_Chi_Minh",
}


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


def _swiss_engine(profile=WESTERN_MODERN_V1) -> AstrologyEngine:
    path = os.environ["GBC_SWISS_EPHE_PATH"]
    return AstrologyEngine(
        provider=SwissEphemerisProvider(ephemeris_path=path),
        house_calculator=SwissHouseCalculator(ephemeris_path=path),
        profile=profile,
    )


def _fixture_engine(profile=WESTERN_MODERN_V1) -> AstrologyEngine:
    return AstrologyEngine(
        provider=FixtureProvider(),
        house_calculator=FixtureHouseCalculator(),
        profile=profile,
    )


def _lilith_aspect_ids(chart) -> set[tuple[str, str, str]]:
    return {
        (aspect.body_a, aspect.body_b, aspect.aspect_type)
        for aspect in chart.aspects
        if aspect.body_a in {"mean_lilith", "true_lilith"}
        or aspect.body_b in {"mean_lilith", "true_lilith"}
    }


class OmittedAdditionalPointsTests(unittest.TestCase):
    def test_omitted_and_empty_keep_legacy_bodies_and_hash(self) -> None:
        engine = _fixture_engine()
        omitted = engine.natal(**HANOI)
        empty = _fixture_engine(
            resolve_calculation_profile(additional_points=[])
        ).natal(**HANOI)
        facade = calculate_chart(**FACADE, engine=engine, additional_points=[])
        self.assertIn("chiron", omitted.bodies)
        self.assertNotIn("mean_lilith", omitted.bodies)
        self.assertNotIn("true_lilith", omitted.bodies)
        self.assertEqual(omitted.meta.additional_points, ())
        self.assertEqual(omitted.to_dict()["meta"]["additionalPoints"], [])
        self.assertEqual(omitted.to_json(), empty.to_json())
        self.assertEqual(omitted.to_json(), facade.to_json())
        self.assertEqual(calculation_hash(omitted), calculation_hash(empty))
        self.assertEqual(len(omitted.aspects), len(empty.aspects))


class FixtureLilithTests(unittest.TestCase):
    def test_selecting_lilith_adds_the_body_not_standard_aspects(self) -> None:
        omitted = _fixture_engine().natal(**HANOI)
        mean = _fixture_engine(
            resolve_calculation_profile(additional_points=["mean_lilith"])
        ).natal(**HANOI)
        true = _fixture_engine(
            resolve_calculation_profile(additional_points=["true_lilith"])
        ).natal(**HANOI)
        both = _fixture_engine(
            resolve_calculation_profile(
                additional_points=["mean_lilith", "true_lilith"]
            )
        ).natal(**HANOI)
        self.assertNotIn("mean_lilith", omitted.bodies)
        self.assertIn("mean_lilith", mean.bodies)
        self.assertIn("true_lilith", true.bodies)
        self.assertNotIn("mean_lilith", mean.points)
        self.assertAlmostEqual(mean.bodies["mean_lilith"].longitude, 310.0)
        self.assertAlmostEqual(true.bodies["true_lilith"].longitude, 312.5)
        self.assertNotAlmostEqual(
            both.bodies["mean_lilith"].longitude,
            both.bodies["true_lilith"].longitude,
        )
        self.assertFalse(_lilith_aspect_ids(mean))
        self.assertFalse(_lilith_aspect_ids(true))
        self.assertFalse(_lilith_aspect_ids(both))
        self.assertEqual(
            {(a.body_a, a.body_b, a.aspect_type) for a in omitted.aspects},
            {(a.body_a, a.body_b, a.aspect_type) for a in mean.aspects},
        )
        self.assertEqual(mean.meta.additional_points, ("mean_lilith",))
        self.assertNotEqual(calculation_hash(omitted), calculation_hash(mean))

    def test_unknown_time_omits_pof_vertex_and_can_still_publish_lilith(self) -> None:
        default_unknown = _fixture_engine().natal(
            local_datetime="1992-11-03",
            timezone="Asia/Ho_Chi_Minh",
            latitude=21.0285,
            longitude=105.8542,
            unknown_time=True,
        )
        requested = _fixture_engine(
            resolve_calculation_profile(
                additional_points=["mean_lilith", "part_of_fortune", "vertex"]
            )
        ).natal(
            local_datetime="1992-11-03",
            timezone="Asia/Ho_Chi_Minh",
            latitude=21.0285,
            longitude=105.8542,
            unknown_time=True,
        )
        self.assertEqual([w.code for w in default_unknown.warnings], ["UNKNOWN_BIRTH_TIME"])
        self.assertNotIn("vertex", default_unknown.points)
        self.assertNotIn("part_of_fortune", default_unknown.points)
        self.assertNotIn("mean_lilith", default_unknown.bodies)
        self.assertIn("mean_lilith", requested.bodies)
        self.assertIsNone(requested.bodies["mean_lilith"].house)
        self.assertNotIn("vertex", requested.points)
        self.assertNotIn("part_of_fortune", requested.points)
        self.assertEqual(
            [w.code for w in requested.warnings],
            ["UNKNOWN_BIRTH_TIME", "ADDITIONAL_POINT_UNAVAILABLE"],
        )
        self.assertEqual(
            set(requested.warnings[1].fields_affected),
            {"points.part_of_fortune", "points.vertex"},
        )
        self.assertNotIn("noon", requested.warnings[1].message.lower())

    def test_explicit_pof_does_not_change_known_time_astronomy(self) -> None:
        omitted = _fixture_engine().natal(**HANOI)
        explicit = _fixture_engine(
            resolve_calculation_profile(
                additional_points=["part_of_fortune", "vertex"]
            )
        ).natal(**HANOI)
        self.assertIn("part_of_fortune", omitted.points)
        self.assertNotIn("vertex", omitted.points)
        self.assertAlmostEqual(
            omitted.points["part_of_fortune"].longitude,
            explicit.points["part_of_fortune"].longitude,
        )
        self.assertNotIn("vertex", explicit.points)
        self.assertEqual(
            explicit.meta.additional_points, ("part_of_fortune", "vertex")
        )
        self.assertNotEqual(calculation_hash(omitted), calculation_hash(explicit))


@unittest.skipUnless(_swiss_available(), "Additional points need Swiss Ephemeris data")
class SwissLilithAndVertexTests(unittest.TestCase):
    def test_mean_and_true_lilith_match_the_provider_and_differ(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        provider = SwissEphemerisProvider(ephemeris_path=path)
        mean = _swiss_engine(
            resolve_calculation_profile(additional_points=["mean_lilith"])
        ).natal(**HANOI)
        true = _swiss_engine(
            resolve_calculation_profile(additional_points=["true_lilith"])
        ).natal(**HANOI)
        utc = datetime.fromisoformat(mean.subject.utc_datetime.replace("Z", "+00:00"))
        if utc.tzinfo is None:
            utc = utc.replace(tzinfo=timezone.utc)
        self.assertAlmostEqual(
            mean.bodies["mean_lilith"].longitude,
            provider.position("mean_lilith", utc).longitude_deg,
            places=10,
        )
        self.assertAlmostEqual(
            true.bodies["true_lilith"].longitude,
            provider.position("true_lilith", utc).longitude_deg,
            places=10,
        )
        self.assertNotAlmostEqual(
            mean.bodies["mean_lilith"].longitude,
            true.bodies["true_lilith"].longitude,
            places=4,
        )
        self.assertFalse(_lilith_aspect_ids(mean))
        self.assertIn("chiron", mean.bodies)

    def test_vertex_matches_houses_ex_ascmc_index_3(self) -> None:
        chart = _swiss_engine().natal(**HANOI)
        swe = import_module("swisseph")
        swe.set_ephe_path(os.environ["GBC_SWISS_EPHE_PATH"])
        _cusps, ascmc = swe.houses_ex(
            chart.subject.julian_day,
            chart.subject.latitude,
            chart.subject.longitude,
            b"P",
        )
        self.assertAlmostEqual(
            chart.points["vertex"].longitude,
            normalize_longitude(float(ascmc[3])),
            places=10,
        )

    def test_part_of_fortune_keeps_sect_method_on_a_day_chart(self) -> None:
        lot = _swiss_engine().natal(**HANOI).points["part_of_fortune"]
        self.assertEqual(lot.method, "ascendant_plus_moon_minus_sun")
        self.assertIsNone(lot.alternative_longitude)


class InvalidAdditionalPointTests(unittest.TestCase):
    def test_invalid_combinations_are_structured_errors(self) -> None:
        cases: tuple[object, ...] = (
            ["lilith"],
            ["mean_lilith", "mean_lilith"],
            ["true_lilith", "osculating_lilith"],
            "mean_lilith",
        )
        for raw in cases:
            with self.subTest(raw=raw):
                with self.assertRaises(InvalidCalculationProfileError) as raised:
                    resolve_calculation_profile(additional_points=raw)
                self.assertEqual(raised.exception.code, "INVALID_CALCULATION_PROFILE")
                self.assertEqual(raised.exception.details["field"], "additional_points")


@unittest.skipUnless(_swiss_available(), "Additional points need Swiss Ephemeris data")
class HttpPythonCliParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _swiss_engine()
        self.client = TestClient(create_app())

    def test_http_python_agree_for_mean_lilith(self) -> None:
        python = calculate_chart(
            **FACADE, engine=self.engine, additional_points=["mean_lilith"]
        ).to_dict()
        response = self.client.post(
            "/v1/charts/natal",
            json={**HTTP_HANOI, "additional_points": ["mean_lilith"]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), python)
        self.assertEqual(response.json()["meta"]["additionalPoints"], ["mean_lilith"])
        self.assertIn("mean_lilith", response.json()["bodies"])
        self.assertEqual(python["schemaVersion"], "1.9.0")

    def test_http_rejects_unknown_and_duplicate_ids(self) -> None:
        unknown = self.client.post(
            "/v1/charts/natal",
            json={**HTTP_HANOI, "additional_points": ["lilith"]},
        )
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(unknown.json()["error"]["code"], "INVALID_CALCULATION_PROFILE")
        self.assertEqual(unknown.json()["error"]["field"], "additional_points")

        duplicate = self.client.post(
            "/v1/charts/natal",
            json={
                **HTTP_HANOI,
                "additional_points": ["true_lilith", "osculating_lilith"],
            },
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(duplicate.json()["error"]["code"], "INVALID_CALCULATION_PROFILE")

    def test_http_omitted_matches_python_default(self) -> None:
        python = calculate_chart(**FACADE, engine=self.engine).to_dict()
        response = self.client.post("/v1/charts/natal", json=HTTP_HANOI)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), python)
        self.assertEqual(response.json()["meta"]["additionalPoints"], [])

    def test_cli_parses_comma_separated_and_json_lists(self) -> None:
        parser = _build_parser()
        natal = parser.parse_args(
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
                "--additional-points",
                "mean_lilith,vertex",
            ]
        )
        self.assertEqual(natal.additional_points, "mean_lilith,vertex")
        self.assertEqual(
            _parse_additional_points_arg(natal.additional_points),
            ["mean_lilith", "vertex"],
        )
        self.assertEqual(
            _parse_additional_points_arg('["true_lilith"]'),
            ["true_lilith"],
        )
        self.assertEqual(_parse_additional_points_arg("[]"), [])


if __name__ == "__main__":
    unittest.main()
