"""HTTP coverage for the v1.0 professional modules.

The point of these routes is that everything the engine can do is reachable. The
first test asserts exactly that, by comparing the engine's public surface against
the published paths -- an engine capability with no route is, for a product whose
frontend speaks only HTTP, not implemented.
"""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from gbc_astro.api.app import create_app
from gbc_astro.api.models import Ayanamsa, HouseSystem
from gbc_astro.houses.systems import SUPPORTED_HOUSE_SYSTEMS
from gbc_astro.profiles.ayanamsa import AYANAMSA_PROFILES

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


class SurfaceCoverageTests(unittest.TestCase):
    """The enums and the routes must not lag the engine."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_the_house_system_enum_matches_the_engine(self) -> None:
        self.assertEqual(
            {member.value for member in HouseSystem}, set(SUPPORTED_HOUSE_SYSTEMS)
        )

    def test_the_ayanamsa_enum_matches_the_engine(self) -> None:
        self.assertEqual({member.value for member in Ayanamsa}, set(AYANAMSA_PROFILES))

    def test_every_engine_capability_has_a_route(self) -> None:
        """An engine method with no endpoint is unreachable from the product."""
        from gbc_astro.engine import AstrologyEngine

        routed = {
            "natal": "/v1/charts/natal",
            "synastry": "/v1/charts/synastry",
            "composite": "/v1/charts/composite",
            "davison": "/v1/charts/davison",
            "compatibility": "/v1/charts/compatibility",
            "draconic": "/v1/charts/draconic",
            "harmonic": "/v1/charts/harmonic",
            "relocate": "/v1/charts/relocated",
            "transits": "/v1/forecast/transits",
            "returns": "/v1/forecast/returns",
            "search_events": "/v1/forecast/events",
            "progressions": "/v1/forecast/progressions",
            "solar_arc": "/v1/forecast/solar-arc",
            "patterns": "/v1/analysis/patterns",
            "astrocartography": "/v1/maps/astrocartography",
            "ephemeris": "/v1/ephemeris",
            "optional_bodies": "/v1/capabilities",
            "evidence_context": "/v1/charts/evidence",
            "report_outline": "/v1/charts/report-outline",
        }
        capabilities = {
            name
            for name in dir(AstrologyEngine)
            if not name.startswith("_") and name != "provider_id"
        }
        self.assertEqual(capabilities, set(routed), "an engine capability lost its route")

        paths = self.client.get("/openapi.json").json()["paths"]
        for capability, path in routed.items():
            with self.subTest(capability=capability):
                self.assertIn(path, paths)


class ZodiacValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_sidereal_without_an_ayanamsa_is_refused(self) -> None:
        """No default: the schools disagree by more than a sign boundary."""
        response = self.client.post(
            "/v1/charts/natal", json={**NATAL, "zodiac": "sidereal"}
        )
        self.assertEqual(response.status_code, 422)

    def test_an_ayanamsa_on_a_tropical_chart_is_refused(self) -> None:
        response = self.client.post(
            "/v1/charts/natal", json={**NATAL, "ayanamsa": "lahiri"}
        )
        self.assertEqual(response.status_code, 422)

    def test_an_unknown_house_system_is_refused(self) -> None:
        response = self.client.post(
            "/v1/charts/natal", json={**NATAL, "house_system": "vehlow"}
        )
        self.assertEqual(response.status_code, 422)


@unittest.skipUnless(_swiss_available(), "Professional routes need Swiss Ephemeris data")
class ProfessionalRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_a_sidereal_chart_can_be_requested_over_http(self) -> None:
        response = self.client.post(
            "/v1/charts/natal",
            json={**NATAL, "zodiac": "sidereal", "ayanamsa": "lahiri"},
        )
        self.assertEqual(response.status_code, 200)
        meta = response.json()["meta"]
        self.assertEqual(meta["zodiac"], "sidereal")
        self.assertEqual(meta["ayanamsa"], "lahiri")
        self.assertIn("ayanamsaDegrees", meta)

    def test_every_house_system_works_over_http(self) -> None:
        for system in SUPPORTED_HOUSE_SYSTEMS:
            with self.subTest(system=system):
                response = self.client.post(
                    "/v1/charts/natal", json={**NATAL, "house_system": system}
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["meta"]["houseSystem"], system)

    def test_the_transform_routes_return_their_transforms(self) -> None:
        draconic = self.client.post("/v1/charts/draconic", json={"natal": NATAL}).json()
        self.assertEqual(draconic["transform"], "draconic")
        self.assertEqual(draconic["bodies"]["true_node"]["longitude"], 0.0)

        harmonic = self.client.post(
            "/v1/charts/harmonic", json={"natal": NATAL, "harmonic": 5}
        ).json()
        self.assertEqual(harmonic["transform"], "harmonic-5")

    def test_harmonic_without_its_number_is_refused(self) -> None:
        response = self.client.post("/v1/charts/harmonic", json={"natal": NATAL})
        self.assertEqual(response.status_code, 400)

    def test_relocation_keeps_the_positions_and_moves_the_angles(self) -> None:
        natal = self.client.post("/v1/charts/natal", json=NATAL).json()
        moved = self.client.post(
            "/v1/charts/relocated",
            json={"natal": NATAL, "latitude": 51.5074, "longitude": -0.1278},
        ).json()

        self.assertEqual(
            moved["bodies"]["sun"]["longitude"], natal["bodies"]["sun"]["longitude"]
        )
        self.assertNotEqual(
            moved["angles"]["ascendant"]["longitude"],
            natal["angles"]["ascendant"]["longitude"],
        )

    def test_the_direction_routes_report_their_instants(self) -> None:
        for path in ("/v1/forecast/progressions", "/v1/forecast/solar-arc"):
            with self.subTest(path=path):
                payload = self.client.post(
                    path,
                    json={"natal": NATAL, "target_instant": "2026-08-08T00:00:00Z"},
                ).json()
                self.assertIn("elapsedYears", payload["meta"])
                self.assertIn("progressedInstant", payload["meta"])

    def test_a_malformed_instant_is_a_structured_error(self) -> None:
        response = self.client.post(
            "/v1/forecast/solar-arc",
            json={"natal": NATAL, "target_instant": "not-a-date"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "INVALID_CALCULATION_PROFILE")

    def test_patterns_ship_the_profile_that_found_them(self) -> None:
        payload = self.client.post("/v1/analysis/patterns", json={"natal": NATAL}).json()
        self.assertIn("legOrbs", payload["profile"])
        self.assertEqual(payload["patternCount"], len(payload["patterns"]))

    def test_astrocartography_returns_four_lines_per_body(self) -> None:
        payload = self.client.post(
            "/v1/maps/astrocartography",
            json={"natal": NATAL, "bodies": ["sun", "moon"], "latitude_step": 10.0},
        ).json()
        self.assertEqual(payload["lineCount"], 8)

    def test_an_inverted_latitude_range_is_refused(self) -> None:
        response = self.client.post(
            "/v1/maps/astrocartography",
            json={"natal": NATAL, "latitude_min": 40.0, "latitude_max": -40.0},
        )
        self.assertEqual(response.status_code, 400)

    def test_the_ephemeris_route_tabulates(self) -> None:
        payload = self.client.post(
            "/v1/ephemeris",
            json={
                "bodies": ["sun", "ceres"],
                "start": "2026-01-01T00:00:00Z",
                "end": "2026-01-03T00:00:00Z",
                "step_seconds": 86400,
            },
        ).json()
        self.assertEqual(payload["rowCount"], 3)
        self.assertIn("ceres", payload["rows"][0]["bodies"])

    def test_an_oversized_ephemeris_is_refused_not_attempted(self) -> None:
        response = self.client.post(
            "/v1/ephemeris",
            json={
                "bodies": ["sun"],
                "start": "2026-01-01T00:00:00Z",
                "end": "2027-01-01T00:00:00Z",
                "step_seconds": 3600,
                "max_rows": 10,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_capabilities_reports_what_is_actually_available(self) -> None:
        payload = self.client.get("/v1/capabilities").json()
        self.assertEqual(len(payload["houseSystems"]), 11)
        self.assertEqual(len(payload["ayanamsas"]), 5)
        self.assertTrue(all(item["available"] for item in payload["optionalBodies"]))

    def test_library_and_http_agree_on_a_transform(self) -> None:
        from gbc_astro import AstrologyEngine

        engine = AstrologyEngine()
        library = engine.draconic(
            engine.natal("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
        ).to_dict()
        http = self.client.post("/v1/charts/draconic", json={"natal": NATAL}).json()
        self.assertEqual(http, library)
