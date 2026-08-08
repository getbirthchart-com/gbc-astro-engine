"""Readiness endpoint tests.

`/health` says the process is up. `/ready` says it can actually serve a chart.
Keeping them apart matters at deploy time: a container without its ephemeris
data starts perfectly and then fails every chart request, and only a probe that
performs a real calculation catches that before traffic arrives.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from gbc_astro.api.app import create_app


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


class LivenessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_health_stays_up_without_touching_the_ephemeris(self) -> None:
        """Liveness must not depend on data, or a restart loop hides the real fault."""
        with mock.patch.dict(os.environ, {"GBC_SWISS_EPHE_PATH": "/nonexistent"}):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_both_probes_are_published(self) -> None:
        paths = self.client.get("/openapi.json").json()["paths"]
        self.assertIn("/health", paths)
        self.assertIn("/ready", paths)


class ReadinessFailureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_missing_ephemeris_data_reports_not_ready_with_503(self) -> None:
        with mock.patch.dict(os.environ, {"GBC_SWISS_EPHE_PATH": "/nonexistent"}):
            response = self.client.get("/ready")

        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["status"], "not_ready")
        self.assertTrue(payload["detail"])
        self.assertEqual(payload["engine"], "gbc-astro")

    def test_a_missing_provider_dependency_is_reported_not_raised(self) -> None:
        """A 503 with a reason beats a 500 with a stack trace."""
        with mock.patch(
            "gbc_astro.providers.swiss.SwissEphemerisProvider.health_check",
            side_effect=RuntimeError("pyswisseph is not installed"),
        ):
            response = self.client.get("/ready")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "not_ready")
        self.assertIn("pyswisseph", response.json()["detail"])

    def test_partial_data_is_degraded_but_still_serving(self) -> None:
        """Chiron without seas_18 should not take the whole service down."""
        with mock.patch(
            "gbc_astro.providers.swiss.SwissEphemerisProvider.health_check",
            return_value={
                "status": "degraded",
                "provider": "swiss",
                "providerVersion": "2.10.03",
                "ephemerisPath": "/opt/gbc/ephemeris/swiss",
                "availableCapabilities": ["sun"],
                "unavailableCapabilities": ["chiron"],
                "manifest": {"missingRequiredData": []},
            },
        ):
            response = self.client.get("/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "degraded")
        self.assertEqual(response.json()["unavailableCapabilities"], ["chiron"])


@unittest.skipUnless(_swiss_available(), "Readiness success needs Swiss Ephemeris data")
class ReadinessSuccessTests(unittest.TestCase):
    def test_a_provisioned_instance_reports_ready(self) -> None:
        response = TestClient(create_app()).get("/ready")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["provider"], "swiss")
        self.assertEqual(payload["unavailableCapabilities"], [])
        self.assertEqual(payload["missingRequiredData"], [])
