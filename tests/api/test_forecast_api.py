"""HTTP adapter tests for the forecast routes."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from gbc_astro.api.app import create_app

NATAL = {
    "local_date": "1992-11-03",
    "local_time": "14:35",
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542,
}


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


class ForecastContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_routes_are_published(self) -> None:
        paths = self.client.get("/openapi.json").json()["paths"]
        for route in ("/v1/forecast/transits", "/v1/forecast/returns", "/v1/forecast/events"):
            self.assertIn(route, paths)

    def test_unknown_event_type_is_a_validation_error(self) -> None:
        response = self.client.post(
            "/v1/forecast/events",
            json={
                "event_type": "moon_landing",
                "body": "sun",
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-02-01T00:00:00Z",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_a_malformed_instant_is_reported_as_a_structured_error(self) -> None:
        response = self.client.post(
            "/v1/forecast/events",
            json={
                "event_type": "station",
                "body": "mercury",
                "start": "not-a-date",
                "end": "2024-02-01T00:00:00Z",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "INVALID_CALCULATION_PROFILE")


@unittest.skipUnless(_swiss_available(), "Forecast routes need Swiss Ephemeris data")
class ForecastRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_transits_return_the_canonical_document(self) -> None:
        response = self.client.post(
            "/v1/forecast/transits",
            json={"natal": NATAL, "target_instant": "2026-08-08T12:00:00Z"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["targetInstant"], "2026-08-08T12:00:00Z")
        self.assertTrue(payload["transitToNatalAspects"])
        self.assertEqual(len(payload["transitHousePlacements"]), 13)

    def test_returns_report_every_hit_with_its_precision(self) -> None:
        response = self.client.post(
            "/v1/forecast/returns",
            json={
                "natal": NATAL,
                "body": "saturn",
                "window_start": "2021-01-01T00:00:00Z",
                "window_end": "2023-12-31T00:00:00Z",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["hitCount"], 3)
        for hit in payload["hits"]:
            self.assertLess(hit["precisionSeconds"], 1.0)

    def test_event_search_reports_its_method(self) -> None:
        payload = self.client.post(
            "/v1/forecast/events",
            json={
                "event_type": "sign_ingress",
                "body": "sun",
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:00Z",
            },
        ).json()

        self.assertEqual(payload["eventCount"], 12)
        self.assertEqual(payload["meta"]["method"], "coarse_bracket_then_bisection")

    def test_http_matches_the_library_result(self) -> None:
        from datetime import datetime, timezone

        from gbc_astro import AstrologyEngine

        engine = AstrologyEngine()
        library = engine.transits(
            engine.natal("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542),
            datetime(2026, 8, 8, 12, tzinfo=timezone.utc),
        ).to_dict()
        http = self.client.post(
            "/v1/forecast/transits",
            json={"natal": NATAL, "target_instant": "2026-08-08T12:00:00Z"},
        ).json()

        self.assertEqual(http, library)
