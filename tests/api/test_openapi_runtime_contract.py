"""Advertised OpenAPI enums must match runtime acceptance. No hidden 400s."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from gbc_astro.api.app import create_app
from gbc_astro.api.models import Ayanamsa, HouseSystem
from gbc_astro.houses.systems import SUPPORTED_HOUSE_SYSTEMS
from gbc_astro.profiles.ayanamsa import (
    AYANAMSA_PROFILES,
    RECOMMENDED_PRODUCT_AYANAMSHA,
)

NATAL = {
    "local_date": "1992-11-03",
    "local_time": "14:35:00",
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


def _openapi_enum(schema: dict[str, object], name: str) -> list[str]:
    components = schema["components"]
    assert isinstance(components, dict)
    schemas = components["schemas"]
    assert isinstance(schemas, dict)
    model = schemas[name]
    assert isinstance(model, dict)
    values = model["enum"]
    assert isinstance(values, list)
    return [str(item) for item in values]


class AdvertisedEnumContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())
        self.schema = self.client.get("/openapi.json").json()

    def test_ayanamsa_openapi_enum_matches_runtime_profiles(self) -> None:
        advertised = set(_openapi_enum(self.schema, "Ayanamsa"))
        self.assertEqual(advertised, {member.value for member in Ayanamsa})
        self.assertEqual(advertised, set(AYANAMSA_PROFILES))
        self.assertIn(RECOMMENDED_PRODUCT_AYANAMSHA, advertised)

    def test_house_system_openapi_enum_matches_engine(self) -> None:
        advertised = set(_openapi_enum(self.schema, "HouseSystem"))
        self.assertEqual(advertised, {member.value for member in HouseSystem})
        self.assertEqual(advertised, set(SUPPORTED_HOUSE_SYSTEMS))


@unittest.skipUnless(_swiss_available(), "Advertised ayanamsa runtime needs Swiss Ephemeris")
class AdvertisedAyanamsaRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())
        self.advertised = _openapi_enum(self.client.get("/openapi.json").json(), "Ayanamsa")

    def test_every_advertised_ayanamsa_is_accepted_at_runtime(self) -> None:
        self.assertEqual(len(self.advertised), 5)
        for ayanamsa in self.advertised:
            with self.subTest(ayanamsa=ayanamsa):
                response = self.client.post(
                    "/v1/charts/natal",
                    json={**NATAL, "zodiac": "sidereal", "ayanamsa": ayanamsa},
                )
                self.assertEqual(response.status_code, 200, response.text)
                meta = response.json()["meta"]
                self.assertEqual(meta["zodiac"], "sidereal")
                self.assertEqual(meta["ayanamsa"], ayanamsa)
                self.assertEqual(meta["ayanamsha"], ayanamsa)
                self.assertIsInstance(meta["ayanamsaVersion"], str)
                self.assertIsInstance(meta["ayanamsaDegrees"], float)
                self.assertNotIn("productExposureApproved", meta)

    def test_unsupported_ayanamsa_is_not_in_openapi_and_is_rejected(self) -> None:
        self.assertNotIn("not_an_ayanamsa", self.advertised)
        response = self.client.post(
            "/v1/charts/natal",
            json={**NATAL, "zodiac": "sidereal", "ayanamsa": "not_an_ayanamsa"},
        )
        self.assertEqual(response.status_code, 422)

    def test_capabilities_recommend_lahiri_without_hiding_engine_ayanamsas(self) -> None:
        payload = self.client.get("/v1/capabilities").json()
        readiness = payload["siderealReadiness"]
        self.assertEqual(readiness["recommendedProductAyanamsha"], "lahiri")
        self.assertIs(readiness["productExposureApproved"], False)
        self.assertTrue(readiness["coreReady"])
        self.assertEqual(set(readiness["engineAyanamsas"]), set(self.advertised))
        self.assertEqual(len(payload["ayanamsas"]), len(self.advertised))


if __name__ == "__main__":
    unittest.main()
