"""Product house-system settings: Placidus, Whole Sign, Equal."""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from gbc_astro import AstrologyEngine, calculate_chart
from gbc_astro.api.app import create_app
from gbc_astro.errors import HouseCalculationUnavailableError
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.houses.systems import PRODUCT_HOUSE_SYSTEMS
from gbc_astro.profiles.defaults import WESTERN_MODERN_V1
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
POLAR = {
    "local_datetime": "1990-12-15T11:30:00",
    "timezone": "Europe/Oslo",
    "latitude": 69.6492,
    "longitude": 18.9553,
}


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


def _longitudes(chart) -> dict[str, float]:
    return {body_id: body.longitude for body_id, body in chart.bodies.items()}


def _signs(chart) -> dict[str, str]:
    return {body_id: body.sign for body_id, body in chart.bodies.items()}


def _retrogrades(chart) -> dict[str, bool | None]:
    return {body_id: body.retrograde for body_id, body in chart.bodies.items()}


def _aspect_ids(chart) -> set[tuple[str, str, str]]:
    return {(aspect.body_a, aspect.body_b, aspect.aspect_type) for aspect in chart.aspects}


class FacadeDefaultEquivalenceTests(unittest.TestCase):
    def test_omitted_none_and_explicit_placidus_match(self) -> None:
        engine = AstrologyEngine(
            provider=FixtureProvider(),
            house_calculator=FixtureHouseCalculator(),
        )
        kwargs = {
            "date": "1992-11-03",
            "time": "14:35:00",
            "latitude": 21.0285,
            "longitude": 105.8542,
            "timezone": "Asia/Ho_Chi_Minh",
            "engine": engine,
        }
        omitted = calculate_chart(**kwargs)
        none = calculate_chart(**kwargs, house_system=None)
        explicit = calculate_chart(**kwargs, house_system="placidus")
        self.assertEqual(omitted.to_json(), none.to_json())
        self.assertEqual(omitted.to_json(), explicit.to_json())
        self.assertEqual(calculation_hash(omitted), calculation_hash(explicit))
        self.assertEqual(omitted.meta.house_system, "placidus")
        self.assertEqual(omitted.meta.requested_house_system, "placidus")
        self.assertEqual(omitted.meta.zodiac, WESTERN_MODERN_V1.zodiac)
        self.assertEqual(omitted.meta.node_type, WESTERN_MODERN_V1.node_type)


@unittest.skipUnless(_swiss_available(), "Product house settings need Swiss Ephemeris data")
class ProductHouseSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _swiss_engine()
        self.charts = {
            system: self.engine.natal(**HANOI, house_system=system)
            for system in PRODUCT_HOUSE_SYSTEMS
        }

    def test_product_tuple_is_the_three_public_systems(self) -> None:
        self.assertEqual(PRODUCT_HOUSE_SYSTEMS, ("placidus", "whole_sign", "equal"))

    def test_whole_sign_cusp_one_is_the_ascendant_sign_boundary(self) -> None:
        chart = self.charts["whole_sign"]
        asc = chart.angles["ascendant"].longitude
        cusp = chart.houses[0].cusp_longitude
        self.assertEqual(cusp, (int(asc // 30) * 30.0) % 360.0)
        self.assertEqual(chart.houses[0].number, 1)

    def test_equal_cusp_one_equals_ascendant(self) -> None:
        chart = self.charts["equal"]
        self.assertAlmostEqual(
            chart.houses[0].cusp_longitude,
            chart.angles["ascendant"].longitude,
        )

    def test_cusp_ten_is_not_mc_for_equal_or_whole_sign(self) -> None:
        for system in ("equal", "whole_sign"):
            chart = self.charts[system]
            cusp_ten = chart.houses[9].cusp_longitude
            mc = chart.angles["mc"].longitude
            self.assertGreater(abs(((cusp_ten - mc + 180) % 360) - 180), 1.0)

    def test_a_planet_changes_house_while_sky_facts_stay_put(self) -> None:
        placidus = self.charts["placidus"]
        whole = self.charts["whole_sign"]
        equal = self.charts["equal"]
        self.assertEqual(_longitudes(placidus), _longitudes(whole))
        self.assertEqual(_longitudes(placidus), _longitudes(equal))
        self.assertEqual(_signs(placidus), _signs(whole))
        self.assertEqual(_retrogrades(placidus), _retrogrades(equal))
        self.assertEqual(_aspect_ids(placidus), _aspect_ids(whole))
        self.assertEqual(_aspect_ids(placidus), _aspect_ids(equal))
        moved = [
            body_id
            for body_id, body in placidus.bodies.items()
            if body.house != whole.bodies[body_id].house
            or body.house != equal.bodies[body_id].house
        ]
        self.assertTrue(moved)

    def test_derived_house_facts_follow_the_selected_system(self) -> None:
        placidus = self.charts["placidus"]
        whole = self.charts["whole_sign"]
        self.assertNotEqual(
            [ruler.to_dict() for ruler in placidus.derived.house_rulers],
            [ruler.to_dict() for ruler in whole.derived.house_rulers],
        )
        self.assertNotEqual(placidus.derived.hemispheres, whole.derived.hemispheres)

    def test_metadata_reports_requested_and_effective_system(self) -> None:
        for system, chart in self.charts.items():
            payload = chart.to_dict()["meta"]
            self.assertEqual(payload["houseSystem"], system)
            self.assertEqual(payload["requestedHouseSystem"], system)
            self.assertEqual(chart.schema_version, "1.9.0")

    def test_unknown_time_has_no_effective_houses(self) -> None:
        for system in PRODUCT_HOUSE_SYSTEMS:
            chart = self.engine.natal(
                local_datetime="1992-11-03",
                timezone="Asia/Ho_Chi_Minh",
                latitude=21.0285,
                longitude=105.8542,
                house_system=system,
                unknown_time=True,
            )
            self.assertIsNone(chart.meta.house_system)
            self.assertEqual(chart.meta.requested_house_system, system)
            self.assertEqual(chart.houses, ())
            self.assertEqual(chart.angles, {})

    def test_polar_placidus_fails_without_fallback_and_product_alternatives_work(self) -> None:
        with self.assertRaises(HouseCalculationUnavailableError) as raised:
            self.engine.natal(**POLAR, house_system="placidus")
        self.assertEqual(raised.exception.code, "HOUSE_CALCULATION_UNAVAILABLE")
        self.assertEqual(
            raised.exception.details["suggestedHouseSystems"],
            ["whole_sign", "equal"],
        )
        for system in ("whole_sign", "equal"):
            chart = self.engine.natal(**POLAR, house_system=system)
            self.assertEqual(len(chart.houses), 12)
            self.assertEqual(chart.meta.house_system, system)


@unittest.skipUnless(_swiss_available(), "Product house settings need Swiss Ephemeris data")
class DownstreamHouseConsumerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _swiss_engine()
        self.a_placidus = self.engine.natal(**HANOI, house_system="placidus")
        self.a_whole = self.engine.natal(**HANOI, house_system="whole_sign")
        self.b = self.engine.natal(
            local_datetime="1990-06-21T08:20:00",
            timezone="Europe/Berlin",
            latitude=52.52,
            longitude=13.405,
            house_system="placidus",
        )

    def test_synastry_overlays_use_the_selected_houses_not_cached_placidus(self) -> None:
        overlay_p = self.engine.synastry(self.a_placidus, self.b)
        overlay_w = self.engine.synastry(self.a_whole, self.b)
        houses_p = {item.body: item.house for item in overlay_p.b_bodies_in_a_houses}
        houses_w = {item.body: item.house for item in overlay_w.b_bodies_in_a_houses}
        self.assertNotEqual(houses_p, houses_w)

    def test_transits_read_the_natal_chart_houses(self) -> None:
        instant = datetime(2026, 8, 8, 12, tzinfo=timezone.utc)
        transit_p = self.engine.transits(self.a_placidus, instant)
        transit_w = self.engine.transits(self.a_whole, instant)
        self.assertEqual(transit_p.meta["natalHouseSystem"], "placidus")
        self.assertEqual(transit_w.meta["natalHouseSystem"], "whole_sign")
        houses_p = {
            item.transit_body: item.natal_house for item in transit_p.transit_house_placements
        }
        houses_w = {
            item.transit_body: item.natal_house for item in transit_w.transit_house_placements
        }
        self.assertNotEqual(houses_p, houses_w)


@unittest.skipUnless(_swiss_available(), "Product house settings need Swiss Ephemeris data")
class HttpPythonParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _swiss_engine()
        self.client = TestClient(create_app())

    def test_http_and_python_agree_for_each_public_system(self) -> None:
        for system in PRODUCT_HOUSE_SYSTEMS:
            with self.subTest(system=system):
                python = self.engine.natal(**HANOI, house_system=system).to_dict()
                response = self.client.post(
                    "/v1/charts/natal",
                    json={**HTTP_HANOI, "house_system": system},
                )
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload, python)
                self.assertEqual(payload["meta"]["houseSystem"], system)
                self.assertEqual(payload["meta"]["requestedHouseSystem"], system)

    def test_http_omitted_house_system_matches_legacy_default(self) -> None:
        python = self.engine.natal(**HANOI).to_dict()
        response = self.client.post("/v1/charts/natal", json=HTTP_HANOI)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), python)
        self.assertEqual(response.json()["meta"]["requestedHouseSystem"], "placidus")

    def test_http_rejects_unknown_house_system(self) -> None:
        response = self.client.post(
            "/v1/charts/natal",
            json={**HTTP_HANOI, "house_system": "not-a-system"},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
