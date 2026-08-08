"""The published response schemas must describe what the engine actually sends.

Every v1 route used to publish `{}` as its response schema, because each one
returns a bare `JSONResponse` and FastAPI had nothing to introspect. A client
vendoring the contract got request types and no response types, and hand-wrote
the shape of every chart from an example.

The schemas added to fix that are documentation, not enforcement: they are
declared under `responses={200: {"model": ...}}` rather than as
`response_model=`, so FastAPI does not coerce the payload through them. That is
deliberate -- coercion would silently drop any field the model forgot, turning a
documentation defect into a data defect -- but it means nothing structural stops
the two from drifting apart.

These tests are what stops it. Real engine output is validated against each
published model, so a schema that stops describing the wire format fails here.
"""

from __future__ import annotations

import json
import os
import unittest

from fastapi.testclient import TestClient

from gbc_astro.api.app import create_app
from gbc_astro.api.responses import (
    AstrocartographyResponse,
    CapabilitiesResponse,
    CompatibilityResponse,
    CompositeChartResponse,
    DavisonChartResponse,
    EphemerisResponse,
    EventSearchResponse,
    NatalChartResponse,
    PatternsResponse,
    ReturnSearchResponse,
    SynastryResponse,
    TransformedChartResponse,
    TransitChartResponse,
)

NATAL = {
    "local_date": "1992-11-03",
    "local_time": "14:35:00",
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542,
}
# A chart that actually contains figures, so the pattern schema is exercised
# against populated output rather than an empty list.
PATTERNED = {
    "local_date": "1975-04-22",
    "local_time": "08:15:00",
    "timezone": "UTC",
    "latitude": 40.0,
    "longitude": -3.0,
}


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    return bool(path and os.path.exists(os.path.join(path, "sepl_18.se1")))


@unittest.skipUnless(_swiss_available(), "Schema parity needs Swiss Ephemeris data")
class ResponseSchemaParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_a_real_natal_payload_satisfies_the_published_schema(self) -> None:
        response = self.client.post("/v1/charts/natal", json=NATAL)
        self.assertEqual(response.status_code, 200)
        NatalChartResponse.model_validate(response.json())

    def test_an_unknown_time_natal_payload_also_satisfies_it(self) -> None:
        """The shape has to hold for the degraded chart too, not only the full one.

        This is where an over-tight schema shows up: no angles, no houses, no
        chart ruler, and `house` null on every body.
        """
        response = self.client.post(
            "/v1/charts/natal",
            json={
                "local_date": "1992-11-03",
                "timezone": "Asia/Ho_Chi_Minh",
                "latitude": 21.0285,
                "longitude": 105.8542,
                "unknown_time": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        NatalChartResponse.model_validate(payload)
        self.assertEqual(payload["angles"], {})
        self.assertIsNone(payload["derived"]["chartRuler"])

    def test_a_sidereal_natal_payload_satisfies_it(self) -> None:
        """Sidereal adds three meta fields that the tropical payload never carries."""
        response = self.client.post(
            "/v1/charts/natal", json={**NATAL, "zodiac": "sidereal", "ayanamsa": "lahiri"}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        NatalChartResponse.model_validate(payload)
        self.assertIn("ayanamsaDegrees", payload["meta"])

    def test_a_populated_patterns_payload_satisfies_the_published_schema(self) -> None:
        response = self.client.post("/v1/analysis/patterns", json={"natal": PATTERNED})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreater(payload["patternCount"], 0)
        PatternsResponse.model_validate(payload)

    def test_an_empty_patterns_payload_satisfies_it_too(self) -> None:
        response = self.client.post("/v1/analysis/patterns", json={"natal": NATAL})
        self.assertEqual(response.status_code, 200)
        PatternsResponse.model_validate(response.json())

    def test_declaring_a_schema_does_not_filter_the_payload(self) -> None:
        """The reason these are `responses={200: {"model": ...}}` and not `response_model=`.

        Under `response_model` FastAPI coerces the payload through the model, so
        a field the model forgot would vanish from the response and the engine
        would ship less data than it calculated. This asserts the payload is
        still whatever `to_dict()` produced, model or no model.
        """
        payload = self.client.post("/v1/charts/natal", json=NATAL).json()

        engine_payload = json.loads(
            json.dumps(_chart_from_engine())
        )
        self.assertEqual(sorted(payload), sorted(engine_payload))
        self.assertEqual(sorted(payload["derived"]), sorted(engine_payload["derived"]))
        self.assertEqual(sorted(payload["meta"]), sorted(engine_payload["meta"]))


def _chart_from_engine() -> dict:
    """The same chart straight from the engine, bypassing HTTP entirely."""
    from gbc_astro import AstrologyEngine
    from gbc_astro.houses.swiss import SwissHouseCalculator
    from gbc_astro.providers.swiss import SwissEphemerisProvider

    path = os.environ["GBC_SWISS_EPHE_PATH"]
    engine = AstrologyEngine(
        provider=SwissEphemerisProvider(ephemeris_path=path),
        house_calculator=SwissHouseCalculator(ephemeris_path=path),
    )
    return engine.natal(
        "1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542
    ).to_dict()


@unittest.skipUnless(_swiss_available(), "Schema publication needs Swiss Ephemeris data")
class SchemaPublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())
        self.schema = self.client.get("/openapi.json").json()

    def _response_schema(self, path: str) -> dict:
        return self.schema["paths"][path]["post"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]

    def test_the_typed_routes_no_longer_publish_an_empty_schema(self) -> None:
        for path in ("/v1/charts/natal", "/v1/analysis/patterns"):
            with self.subTest(path=path):
                self.assertIn("$ref", self._response_schema(path))

    def test_the_contract_names_the_rulership_fields(self) -> None:
        """A client cannot type what the contract does not mention."""
        serialised = json.dumps(self.schema)
        for field in ("chartRuler", "dignities", "dispositors", "dominantPlanets"):
            with self.subTest(field=field):
                self.assertIn(field, serialised)

    def test_the_schemas_allow_unknown_fields(self) -> None:
        """They describe a floor, not a ceiling.

        A caller may rely on every named field being present; the engine may add
        fields in a minor release without any client's parser rejecting the
        payload.
        """
        natal = self.schema["components"]["schemas"]["NatalChartResponse"]
        self.assertNotEqual(natal.get("additionalProperties"), False)


@unittest.skipUnless(_swiss_available(), "Schema parity needs Swiss Ephemeris data")
class EveryRouteSchemaParityTests(unittest.TestCase):
    """One real call per route, validated against the schema that route publishes.

    Table-driven on purpose: a new route added without a response model shows up
    as a missing entry here rather than as an empty schema a client only
    discovers at integration time.
    """

    OTHER = {
        "local_date": "1988-02-14",
        "local_time": "09:20:00",
        "timezone": "Europe/Paris",
        "latitude": 48.8566,
        "longitude": 2.3522,
    }
    INSTANT = "2026-08-08T12:00:00Z"

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_every_route_payload_satisfies_its_published_schema(self) -> None:
        pair = {"chart_a": NATAL, "chart_b": self.OTHER}
        cases = (
            ("/v1/charts/synastry", pair, SynastryResponse),
            ("/v1/charts/composite", pair, CompositeChartResponse),
            ("/v1/charts/davison", pair, DavisonChartResponse),
            ("/v1/charts/compatibility", pair, CompatibilityResponse),
            ("/v1/charts/draconic", {"natal": NATAL}, TransformedChartResponse),
            (
                "/v1/charts/harmonic",
                {"natal": NATAL, "harmonic": 5},
                TransformedChartResponse,
            ),
            (
                "/v1/charts/relocated",
                {"natal": NATAL, "latitude": 35.68, "longitude": 139.65},
                NatalChartResponse,
            ),
            (
                "/v1/forecast/transits",
                {"natal": NATAL, "target_instant": self.INSTANT},
                TransitChartResponse,
            ),
            (
                "/v1/forecast/returns",
                {
                    "natal": NATAL,
                    "body": "sun",
                    "window_start": "2026-11-01T00:00:00Z",
                    "window_end": "2026-11-06T00:00:00Z",
                },
                ReturnSearchResponse,
            ),
            (
                "/v1/forecast/events",
                {
                    "event_type": "station",
                    "body": "mercury",
                    "start": "2026-01-01T00:00:00Z",
                    "end": "2026-06-01T00:00:00Z",
                },
                EventSearchResponse,
            ),
            (
                "/v1/forecast/progressions",
                {"natal": NATAL, "target_instant": self.INSTANT},
                TransformedChartResponse,
            ),
            (
                "/v1/forecast/solar-arc",
                {"natal": NATAL, "target_instant": self.INSTANT},
                TransformedChartResponse,
            ),
            (
                "/v1/ephemeris",
                {
                    "bodies": ["sun"],
                    "start": "2026-01-01T00:00:00Z",
                    "end": "2026-01-03T00:00:00Z",
                    "step_seconds": 86400,
                },
                EphemerisResponse,
            ),
            (
                "/v1/maps/astrocartography",
                {"natal": NATAL},
                AstrocartographyResponse,
            ),
        )

        for path, body, model in cases:
            with self.subTest(path=path):
                response = self.client.post(path, json=body)
                self.assertEqual(response.status_code, 200, response.text)
                model.model_validate(response.json())

    def test_the_capabilities_payload_satisfies_its_schema(self) -> None:
        response = self.client.get("/v1/capabilities")
        self.assertEqual(response.status_code, 200)
        CapabilitiesResponse.model_validate(response.json())

    def test_no_route_publishes_an_empty_response_schema(self) -> None:
        """The defect this whole module exists to close, asserted directly."""
        schema = self.client.get("/openapi.json").json()
        empty = []
        for path, operations in schema["paths"].items():
            for operation in operations.values():
                ok = (operation.get("responses") or {}).get("200")
                if not ok:
                    continue
                content = (ok.get("content") or {}).get("application/json") or {}
                if not content.get("schema"):
                    empty.append(path)
        self.assertEqual(empty, [])
