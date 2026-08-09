"""HTTP adapter tests for the relationship routes."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from gbc_astro.api.app import create_app

CHART_A = {
    "local_date": "1992-11-03",
    "local_time": "14:35",
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542,
}
CHART_B = {
    "local_date": "1990-06-21",
    "local_time": "08:20",
    "timezone": "Europe/Berlin",
    "latitude": 52.52,
    "longitude": 13.405,
}


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


class RelationshipContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_routes_are_published_in_the_openapi_document(self) -> None:
        paths = self.client.get("/openapi.json").json()["paths"]
        self.assertIn("/v1/charts/synastry", paths)
        self.assertIn("/v1/charts/composite", paths)

    def test_missing_second_chart_is_a_validation_error(self) -> None:
        response = self.client.post("/v1/charts/synastry", json={"chart_a": CHART_A})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "REQUEST_VALIDATION_ERROR")

    def test_unknown_field_is_rejected(self) -> None:
        response = self.client.post(
            "/v1/charts/composite",
            json={"chart_a": CHART_A, "chart_b": CHART_B, "surprise": 1},
        )
        self.assertEqual(response.status_code, 422)


@unittest.skipUnless(_swiss_available(), "Relationship routes need Swiss Ephemeris data")
class RelationshipRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_synastry_returns_the_canonical_document_unwrapped(self) -> None:
        response = self.client.post(
            "/v1/charts/synastry", json={"chart_a": CHART_A, "chart_b": CHART_B}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertNotIn("chart", payload)
        self.assertEqual(payload["schemaVersion"], "1.1.0")
        for key in ("crossAspects", "aBodiesInBHouses", "bBodiesInAHouses", "angleInteractions"):
            self.assertIn(key, payload)
        self.assertTrue(payload["crossAspects"])

    def test_composite_reports_its_methodology(self) -> None:
        response = self.client.post(
            "/v1/charts/composite", json={"chart_a": CHART_A, "chart_b": CHART_B}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["meta"]["compositePositionMethod"], "shortest_arc_midpoint")
        self.assertEqual(payload["meta"]["compositeHouseMethod"], "armc_from_midpoint_mc")
        self.assertEqual(payload["meta"]["compositeHouseSystem"], "placidus")
        self.assertEqual(len(payload["houses"]), 12)
        self.assertNotIn(
            "COMPOSITE_HOUSES_UNAVAILABLE",
            {warning["code"] for warning in payload["warnings"]},
        )

    def test_http_matches_the_library_result(self) -> None:
        from gbc_astro import AstrologyEngine

        engine = AstrologyEngine()
        library = engine.synastry(
            engine.natal("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542),
            engine.natal("1990-06-21T08:20:00", "Europe/Berlin", 52.52, 13.405),
        ).to_dict()
        http = self.client.post(
            "/v1/charts/synastry", json={"chart_a": CHART_A, "chart_b": CHART_B}
        ).json()

        self.assertEqual(http, library)

    def test_ambiguous_dst_still_returns_a_structured_error(self) -> None:
        response = self.client.post(
            "/v1/charts/synastry",
            json={
                "chart_a": CHART_A,
                "chart_b": {
                    "local_date": "2024-10-27",
                    "local_time": "02:30",
                    "timezone": "Europe/Berlin",
                    "latitude": 52.52,
                    "longitude": 13.405,
                },
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "AMBIGUOUS_LOCAL_TIME")


@unittest.skipUnless(_swiss_available(), "Davison route needs Swiss Ephemeris data")
class DavisonRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_davison_returns_a_real_chart_with_speeds_and_houses(self) -> None:
        response = self.client.post(
            "/v1/charts/davison", json={"chart_a": CHART_A, "chart_b": CHART_B}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertIn("derivedFrom", payload)
        self.assertEqual(len(payload["chart"]["houses"]), 12)
        self.assertIsNotNone(payload["chart"]["bodies"]["sun"]["speedLongitude"])
        self.assertEqual(
            payload["meta"]["davisonLocationMethod"], "mean_latitude_circular_mean_longitude"
        )

    def test_unknown_birth_time_is_refused(self) -> None:
        response = self.client.post(
            "/v1/charts/davison",
            json={
                "chart_a": CHART_A,
                "chart_b": {
                    "local_date": "1990-06-21",
                    "local_time": None,
                    "unknown_time": True,
                    "timezone": "Europe/Berlin",
                    "latitude": 52.52,
                    "longitude": 13.405,
                },
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "UNKNOWN_BIRTH_TIME")


@unittest.skipUnless(_swiss_available(), "Compatibility route needs Swiss Ephemeris data")
class CompatibilityRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_returns_three_totals_and_a_full_breakdown(self) -> None:
        response = self.client.post(
            "/v1/charts/compatibility", json={"chart_a": CHART_A, "chart_b": CHART_B}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        totals = payload["totals"]
        for key in ("supportive", "challenging", "activity", "balance"):
            self.assertIn(key, totals)
        self.assertEqual(len(payload["contributions"]), payload["contributionCount"])
        self.assertEqual(payload["meta"]["scoringProfile"], "synastry-scoring-v1")

    def test_publishes_no_percentage(self) -> None:
        payload = self.client.post(
            "/v1/charts/compatibility", json={"chart_a": CHART_A, "chart_b": CHART_B}
        ).json()
        self.assertNotIn("percent", payload["totals"])
        self.assertNotIn("score", payload["totals"])

    def test_route_is_published(self) -> None:
        paths = self.client.get("/openapi.json").json()["paths"]
        self.assertIn("/v1/charts/compatibility", paths)
