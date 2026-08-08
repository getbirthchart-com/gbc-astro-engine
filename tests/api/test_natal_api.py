"""HTTP adapter tests — validation, errors, library/API parity."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from gbc_astro import AstrologyEngine
from gbc_astro.api.app import create_app
from gbc_astro.api.dependencies import get_engine
from gbc_astro.api.export_openapi import export_openapi
from tests.helpers import FixtureHouseCalculator, FixtureProvider

ROOT = Path(__file__).resolve().parents[2]
OPENAPI_SNAPSHOT = ROOT / "openapi" / "gbc-astro-v1.json"


def _fixture_engine() -> AstrologyEngine:
    return AstrologyEngine(
        provider=FixtureProvider(),
        house_calculator=FixtureHouseCalculator(),
    )


def _client() -> TestClient:
    app = create_app()

    def override_engine():
        yield _fixture_engine()

    app.dependency_overrides[get_engine] = override_engine
    return TestClient(app)


class HealthEndpointTests(unittest.TestCase):
    def test_health_ok(self) -> None:
        with _client() as client:
            response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["engine"], "gbc-astro")
        self.assertIn("engine_version", payload)
        self.assertEqual(payload["api_version"], "v1")


class NatalValidationTests(unittest.TestCase):
    def test_missing_time_when_known(self) -> None:
        with _client() as client:
            response = client.post(
                "/v1/charts/natal",
                json={
                    "local_date": "1996-06-14",
                    "local_time": None,
                    "unknown_time": False,
                    "timezone": "Europe/Lisbon",
                    "latitude": 38.7223,
                    "longitude": -9.1393,
                },
            )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "REQUEST_VALIDATION_ERROR")

    def test_contradictory_unknown_time_with_clock(self) -> None:
        with _client() as client:
            response = client.post(
                "/v1/charts/natal",
                json={
                    "local_date": "1996-06-14",
                    "local_time": "04:12",
                    "unknown_time": True,
                    "timezone": "Europe/Lisbon",
                    "latitude": 38.7223,
                    "longitude": -9.1393,
                },
            )
        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertEqual(body["error"]["code"], "REQUEST_VALIDATION_ERROR")
        self.assertIn("local_time must be null", body["error"]["message"])

    def test_invalid_latitude(self) -> None:
        with _client() as client:
            response = client.post(
                "/v1/charts/natal",
                json={
                    "local_date": "1996-06-14",
                    "local_time": "04:12",
                    "unknown_time": False,
                    "timezone": "Europe/Lisbon",
                    "latitude": 99.0,
                    "longitude": -9.1393,
                },
            )
        self.assertEqual(response.status_code, 422)

    def test_invalid_longitude(self) -> None:
        with _client() as client:
            response = client.post(
                "/v1/charts/natal",
                json={
                    "local_date": "1996-06-14",
                    "local_time": "04:12",
                    "unknown_time": False,
                    "timezone": "Europe/Lisbon",
                    "latitude": 38.7223,
                    "longitude": -200.0,
                },
            )
        self.assertEqual(response.status_code, 422)

    def test_malformed_date(self) -> None:
        with _client() as client:
            response = client.post(
                "/v1/charts/natal",
                json={
                    "local_date": "14-06-1996",
                    "local_time": "04:12",
                    "unknown_time": False,
                    "timezone": "Europe/Lisbon",
                    "latitude": 38.7223,
                    "longitude": -9.1393,
                },
            )
        self.assertEqual(response.status_code, 422)

    def test_malformed_time(self) -> None:
        with _client() as client:
            response = client.post(
                "/v1/charts/natal",
                json={
                    "local_date": "1996-06-14",
                    "local_time": "4pm",
                    "unknown_time": False,
                    "timezone": "Europe/Lisbon",
                    "latitude": 38.7223,
                    "longitude": -9.1393,
                },
            )
        self.assertEqual(response.status_code, 422)

    def test_unknown_timezone(self) -> None:
        with _client() as client:
            response = client.post(
                "/v1/charts/natal",
                json={
                    "local_date": "1996-06-14",
                    "local_time": "04:12",
                    "unknown_time": False,
                    "timezone": "Not/A_Zone",
                    "latitude": 38.7223,
                    "longitude": -9.1393,
                },
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "UNKNOWN_TIMEZONE")


class NatalDomainErrorTests(unittest.TestCase):
    def test_ambiguous_local_time(self) -> None:
        with _client() as client:
            response = client.post(
                "/v1/charts/natal",
                json={
                    "local_date": "2024-11-03",
                    "local_time": "01:30",
                    "unknown_time": False,
                    "timezone": "America/New_York",
                    "latitude": 40.7128,
                    "longitude": -74.006,
                    "house_system": "equal",
                },
            )
        self.assertEqual(response.status_code, 409)
        body = response.json()
        self.assertEqual(body["error"]["code"], "AMBIGUOUS_LOCAL_TIME")
        self.assertEqual(body["error"]["field"], "local_time")

    def test_nonexistent_local_time(self) -> None:
        with _client() as client:
            response = client.post(
                "/v1/charts/natal",
                json={
                    "local_date": "2024-03-10",
                    "local_time": "02:30",
                    "unknown_time": False,
                    "timezone": "America/New_York",
                    "latitude": 40.7128,
                    "longitude": -74.006,
                    "house_system": "equal",
                },
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "NONEXISTENT_LOCAL_TIME")

    def test_house_calculation_unavailable_no_silent_fallback(self) -> None:
        from gbc_astro.errors import HouseCalculationUnavailableError
        from gbc_astro.houses.base import HouseCalculation

        class FailingHouseCalculator:
            id = "failing-house"

            def calculate(
                self,
                julian_day: float,
                latitude: float,
                longitude: float,
                house_system: str,
            ) -> HouseCalculation:
                raise HouseCalculationUnavailableError(
                    "Placidus houses are unavailable for this location.",
                    {"houseSystem": house_system, "latitude": latitude},
                )

        app = create_app()

        def override_engine():
            yield AstrologyEngine(
                provider=FixtureProvider(),
                house_calculator=FailingHouseCalculator(),
            )

        app.dependency_overrides[get_engine] = override_engine
        with TestClient(app) as client:
            response = client.post(
                "/v1/charts/natal",
                json={
                    "local_date": "1992-06-21",
                    "local_time": "12:00",
                    "unknown_time": False,
                    "timezone": "UTC",
                    "latitude": 70.0,
                    "longitude": 0.0,
                    "house_system": "placidus",
                },
            )
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["error"]["code"], "HOUSE_CALCULATION_UNAVAILABLE")
        self.assertNotIn("angles", body)
        self.assertNotIn("bodies", body)

class LibraryApiParityTests(unittest.TestCase):
    def test_known_time_parity_lisbon(self) -> None:
        engine = _fixture_engine()
        direct = engine.natal(
            local_datetime="1996-06-14T04:12:00",
            timezone="Europe/Lisbon",
            latitude=38.7223,
            longitude=-9.1393,
            house_system="equal",
        ).to_dict()

        with _client() as client:
            response = client.post(
                "/v1/charts/natal",
                json={
                    "local_date": "1996-06-14",
                    "local_time": "04:12",
                    "unknown_time": False,
                    "timezone": "Europe/Lisbon",
                    "latitude": 38.7223,
                    "longitude": -9.1393,
                    "house_system": "equal",
                },
            )
        self.assertEqual(response.status_code, 200)
        http_payload = response.json()
        self.assertEqual(http_payload, direct)
        self.assertTrue(http_payload["subject"]["birthTimeKnown"])
        self.assertIn("ascendant", http_payload["angles"])
        self.assertEqual(len(http_payload["houses"]), 12)

    def test_unknown_time_parity(self) -> None:
        engine = _fixture_engine()
        direct = engine.natal(
            local_datetime="1996-06-14",
            timezone="Europe/Lisbon",
            latitude=38.7223,
            longitude=-9.1393,
            unknown_time=True,
        ).to_dict()

        with _client() as client:
            response = client.post(
                "/v1/charts/natal",
                json={
                    "local_date": "1996-06-14",
                    "local_time": None,
                    "unknown_time": True,
                    "timezone": "Europe/Lisbon",
                    "latitude": 38.7223,
                    "longitude": -9.1393,
                },
            )
        self.assertEqual(response.status_code, 200)
        http_payload = response.json()
        self.assertEqual(http_payload, direct)
        self.assertFalse(http_payload["subject"]["birthTimeKnown"])
        self.assertEqual(http_payload["angles"], {})
        self.assertEqual(http_payload["houses"], [])
        self.assertIsNone(http_payload["meta"]["houseSystem"])
        self.assertIsNone(http_payload["derived"]["bigThree"]["rising"])
        self.assertEqual(http_payload["warnings"][0]["code"], "UNKNOWN_BIRTH_TIME")
        # No fabricated clock time in subject localDateTime beyond date-start.
        self.assertTrue(http_payload["subject"]["localDateTime"].startswith("1996-06-14"))
        self.assertTrue(
            http_payload["subject"]["localDateTime"].endswith("T00:00:00")
            or http_payload["subject"]["localDateTime"] == "1996-06-14"
        )


class OpenApiExportTests(unittest.TestCase):
    def test_export_matches_committed_snapshot(self) -> None:
        self.assertTrue(OPENAPI_SNAPSHOT.exists(), "Committed OpenAPI snapshot missing")
        generated = ROOT / "openapi" / ".generated-test.json"
        try:
            export_openapi(generated)
            committed = json.loads(OPENAPI_SNAPSHOT.read_text(encoding="utf-8"))
            fresh = json.loads(generated.read_text(encoding="utf-8"))
            self.assertEqual(fresh, committed)
        finally:
            if generated.exists():
                generated.unlink()

    def test_openapi_json_route(self) -> None:
        with _client() as client:
            response = client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()
        self.assertEqual(schema["info"]["version"], "v1")
        self.assertIn("/v1/charts/natal", schema["paths"])
        self.assertIn("/health", schema["paths"])


if __name__ == "__main__":
    unittest.main()
