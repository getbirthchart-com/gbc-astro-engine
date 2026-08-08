"""Regression tests for the security and robustness audit.

Each test corresponds to a finding. They exist so the finding cannot come back
quietly: a fix without a test is a fix that lasts until the next refactor.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import unittest
from collections import defaultdict

from fastapi.testclient import TestClient

from gbc_astro.api.app import create_app
from gbc_astro.charts.astrocartography import MAX_LINE_POINTS

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


class TimezoneInputTests(unittest.TestCase):
    """Finding: a path-like timezone raised ValueError and became a 500.

    Python's zoneinfo blocks the traversal itself, so nothing was ever readable.
    The defect was that a bad request looked like a server fault: it returned
    500 and logged a full stack trace, which is indistinguishable from a real
    outage in monitoring.
    """

    def setUp(self) -> None:
        self.client = TestClient(create_app(), raise_server_exceptions=False)

    def test_a_malformed_timezone_is_a_client_error(self) -> None:
        for value in (
            "../../etc/passwd",
            "/etc/passwd",
            "..",
            "Asia/Ho\x00Chi",
            "A" * 5000,
            "  ",
        ):
            with self.subTest(timezone=value):
                response = self.client.post(
                    "/v1/charts/natal", json={**NATAL, "timezone": value}
                )
                self.assertLess(response.status_code, 500, value)
                self.assertIn(
                    response.json()["error"]["code"],
                    {"UNKNOWN_TIMEZONE", "REQUEST_VALIDATION_ERROR"},
                )

    def test_errors_never_carry_a_stack_trace_or_a_filesystem_path(self) -> None:
        for payload in (
            {**NATAL, "timezone": "../../etc/passwd"},
            {**NATAL, "latitude": 1e308},
            {**NATAL, "local_date": "not-a-date"},
        ):
            with self.subTest(payload=sorted(payload)):
                body = self.client.post("/v1/charts/natal", json=payload).text
                for marker in ("Traceback", "site-packages", "/Users/", ".venv"):
                    self.assertNotIn(marker, body)


class ResourceBoundTests(unittest.TestCase):
    """Finding: astrocartography had no bound on emitted points.

    `latitude_step: 0.001` produced 6.8 million points -- 9.2 seconds of CPU and
    a 351 MB response from one unauthenticated request.
    """

    def setUp(self) -> None:
        self.client = TestClient(create_app(), raise_server_exceptions=False)

    def test_a_tiny_latitude_step_is_refused(self) -> None:
        response = self.client.post(
            "/v1/maps/astrocartography", json={"natal": NATAL, "latitude_step": 0.001}
        )
        self.assertEqual(response.status_code, 422)

    def test_an_oversized_body_list_is_refused(self) -> None:
        for path, payload in (
            ("/v1/maps/astrocartography", {"natal": NATAL, "bodies": ["sun"] * 100}),
            (
                "/v1/ephemeris",
                {
                    "bodies": ["sun"] * 10_000,
                    "start": "2026-01-01T00:00:00Z",
                    "end": "2026-01-02T00:00:00Z",
                    "step_seconds": 86400,
                },
            ),
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path, json=payload).status_code, 422)

    def test_the_point_budget_is_enforced_in_the_domain_not_only_the_schema(self) -> None:
        """A caller reaching the library directly must hit the same wall."""
        from gbc_astro.charts.astrocartography import calculate_astrocartography

        equatorial = {f"body{index}": (10.0, 5.0) for index in range(20)}
        with self.assertRaises(ValueError):
            calculate_astrocartography(
                equatorial, 0.0, latitude_range=(-66.0, 66.0), latitude_step=0.05
            )

    def test_the_budget_is_a_declared_number(self) -> None:
        self.assertGreater(MAX_LINE_POINTS, 0)


@unittest.skipUnless(_swiss_available(), "Worst-case timing needs Swiss Ephemeris data")
class WorstCaseCostTests(unittest.TestCase):
    def test_the_tightest_permitted_request_stays_bounded(self) -> None:
        client = TestClient(create_app())
        started = time.perf_counter()
        response = client.post(
            "/v1/maps/astrocartography",
            json={"natal": NATAL, "latitude_step": 0.05},
        )
        elapsed = time.perf_counter() - started

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 5.0, "worst permitted case should stay well under 5s")
        self.assertLess(len(response.content), 32_000_000)


@unittest.skipUnless(_swiss_available(), "Concurrency test needs Swiss Ephemeris data")
class AyanamsaConcurrencyTests(unittest.TestCase):
    """Finding: Swiss Ephemeris keeps the sidereal mode in global state.

    Selecting a mode and reading the ayanamsa were two calls against one shared
    variable, and FastAPI runs synchronous handlers in a threadpool. Measured
    under forced GIL switching, 1.4% of calls returned another thread's value --
    a Lahiri request answered with Raman, 1.45 degrees out. Silently wrong, not
    a crash, which is the worst kind.
    """

    def test_concurrent_readers_never_see_another_ayanamsa(self) -> None:
        from gbc_astro.profiles.ayanamsa import AYANAMSA_PROFILES
        from gbc_astro.zodiac.sidereal import AyanamsaCalculator

        calculator = AyanamsaCalculator()
        profiles = {
            name: AYANAMSA_PROFILES[name]
            for name in ("lahiri", "raman", "fagan_bradley")
        }
        julian_day = 2451545.0
        expected = {
            name: round(calculator.value(julian_day, profile), 6)
            for name, profile in profiles.items()
        }

        results: dict[str, list[float]] = defaultdict(list)

        def worker(name: str) -> None:
            profile = profiles[name]
            for _ in range(1500):
                results[name].append(round(calculator.value(julian_day, profile), 6))

        original = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)  # force the interleaving the bug needs
        try:
            threads = [threading.Thread(target=worker, args=(name,)) for name in profiles]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        finally:
            sys.setswitchinterval(original)

        for name, values in results.items():
            wrong = [value for value in values if value != expected[name]]
            self.assertEqual(wrong, [], f"{name} saw another thread's ayanamsa")

    def test_the_ayanamsas_differ_enough_for_the_test_to_be_meaningful(self) -> None:
        """If they were all equal the concurrency test could not fail."""
        from gbc_astro.validation.ayanamsa import observed_spread_degrees

        self.assertGreater(observed_spread_degrees(), 1.0)
