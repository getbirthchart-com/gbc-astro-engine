"""Internal shared-secret gate.

When GBC_ASTRO_API_SECRET is set, calculation routes require a Bearer token.
Health probes stay public. Unset secret keeps local tests working.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from gbc_astro.api.app import create_app
from gbc_astro.api.auth import secrets_match

NATAL = {
    "local_date": "1992-11-03",
    "local_time": "14:35",
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542,
}

SECRET = "test-internal-secret-value"


class SecretMatchingTests(unittest.TestCase):
    def test_equal_secrets_match(self) -> None:
        self.assertTrue(secrets_match(SECRET, SECRET))

    def test_wrong_length_does_not_match(self) -> None:
        self.assertFalse(secrets_match("short", SECRET))


class InternalSecretMiddlewareTests(unittest.TestCase):
    def test_health_and_ready_stay_public_when_secret_is_set(self) -> None:
        with mock.patch.dict(os.environ, {"GBC_ASTRO_API_SECRET": SECRET}):
            client = TestClient(create_app(), raise_server_exceptions=False)
            self.assertEqual(client.get("/health").status_code, 200)

    def test_natal_without_bearer_is_401_when_secret_is_set(self) -> None:
        with mock.patch.dict(os.environ, {"GBC_ASTRO_API_SECRET": SECRET}):
            client = TestClient(create_app(), raise_server_exceptions=False)
            response = client.post("/v1/charts/natal", json=NATAL)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

    def test_natal_with_bearer_is_not_401(self) -> None:
        with mock.patch.dict(os.environ, {"GBC_ASTRO_API_SECRET": SECRET}):
            client = TestClient(create_app(), raise_server_exceptions=False)
            response = client.post(
                "/v1/charts/natal",
                json=NATAL,
                headers={"Authorization": f"Bearer {SECRET}"},
            )
        self.assertNotEqual(response.status_code, 401)

    def test_unset_secret_does_not_401(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in {
            "GBC_ASTRO_API_SECRET",
            "ASTROLOGY_API_SECRET",
            "GBC_ASTRO_REQUIRE_SECRET",
        }}
        with mock.patch.dict(os.environ, env, clear=True):
            client = TestClient(create_app(), raise_server_exceptions=False)
            response = client.post("/v1/charts/natal", json=NATAL)
        self.assertNotEqual(response.status_code, 401)

    def test_require_secret_without_secret_is_401(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in {
            "GBC_ASTRO_API_SECRET",
            "ASTROLOGY_API_SECRET",
        }}
        env["GBC_ASTRO_REQUIRE_SECRET"] = "1"
        with mock.patch.dict(os.environ, env, clear=True):
            client = TestClient(create_app(), raise_server_exceptions=False)
            response = client.post("/v1/charts/natal", json=NATAL)
            health = client.get("/health")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")
        self.assertEqual(health.status_code, 200)
