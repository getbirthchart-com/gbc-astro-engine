"""Relationship-level True/Mean Node convention (REL-01)."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from gbc_astro import AstrologyEngine
from gbc_astro.api.app import create_app
from gbc_astro.cli import _build_parser
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.defaults import RELATIONSHIP_WESTERN_V1, WESTERN_MODERN_V1
from gbc_astro.profiles.nodes import profile_with_node_type
from gbc_astro.providers.swiss import SwissEphemerisProvider
from gbc_astro.validation.reproducibility import synastry_hash, synastry_identity_payload

CHART_A = {
    "local_datetime": "1992-11-03T14:35:00",
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542,
}
CHART_B = {
    "local_datetime": "1988-02-14T09:20:00",
    "timezone": "Europe/Paris",
    "latitude": 48.8566,
    "longitude": 2.3522,
}
HTTP_A = {
    "local_date": "1992-11-03",
    "local_time": "14:35:00",
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542,
}
HTTP_B = {
    "local_date": "1988-02-14",
    "local_time": "09:20:00",
    "timezone": "Europe/Paris",
    "latitude": 48.8566,
    "longitude": 2.3522,
}
NODES = {"true_node", "mean_node"}


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


def _swiss_engine(profile=WESTERN_MODERN_V1, relationship_profile=RELATIONSHIP_WESTERN_V1):
    path = os.environ["GBC_SWISS_EPHE_PATH"]
    return AstrologyEngine(
        provider=SwissEphemerisProvider(ephemeris_path=path),
        house_calculator=SwissHouseCalculator(ephemeris_path=path),
        profile=profile,
        relationship_profile=relationship_profile,
    )


def _node_pairs(chart) -> set[tuple[str, str]]:
    return {
        (aspect.body_a, aspect.body_b)
        for aspect in chart.cross_aspects
        if aspect.body_a in NODES or aspect.body_b in NODES
    }


def _planet_pairs(chart) -> set[tuple[str, str, str]]:
    return {
        (aspect.body_a, aspect.body_b, aspect.aspect_type)
        for aspect in chart.cross_aspects
        if aspect.body_a not in NODES and aspect.body_b not in NODES
    }


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class SynastryNodeConventionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _swiss_engine()
        self.chart_a = self.engine.natal(**CHART_A)
        self.chart_b = self.engine.natal(**CHART_B)

    def test_omitted_equals_explicit_true_and_is_legacy(self) -> None:
        omitted = self.engine.synastry(self.chart_a, self.chart_b)
        explicit = self.engine.synastry(self.chart_a, self.chart_b, node_type="true")
        self.assertEqual(omitted.meta.node_type, "true")
        self.assertEqual(explicit.meta.node_type, "true")
        self.assertEqual(omitted.to_json(), explicit.to_json())
        self.assertEqual(synastry_hash(omitted), synastry_hash(explicit))
        self.assertTrue(_node_pairs(omitted))
        node_bodies = {
            node for pair in _node_pairs(omitted) for node in pair if node in NODES
        }
        self.assertTrue(not node_bodies or node_bodies == {"true_node"})

    def test_mean_uses_mean_node_for_both_charts(self) -> None:
        mean = self.engine.synastry(self.chart_a, self.chart_b, node_type="mean")
        self.assertEqual(mean.meta.node_type, "mean")
        node_bodies = {node for pair in _node_pairs(mean) for node in pair if node in NODES}
        self.assertEqual(node_bodies, {"mean_node"})
        self.assertNotIn("true_node", node_bodies)
        self.assertFalse(
            any(
                aspect.body_a == "south_node" or aspect.body_b == "south_node"
                for aspect in mean.cross_aspects
            )
        )

    def test_true_and_mean_node_contacts_differ(self) -> None:
        true_chart = self.engine.synastry(self.chart_a, self.chart_b, node_type="true")
        mean_chart = self.engine.synastry(self.chart_a, self.chart_b, node_type="mean")
        self.assertNotEqual(_node_pairs(true_chart), _node_pairs(mean_chart))
        self.assertNotEqual(synastry_hash(true_chart), synastry_hash(mean_chart))
        self.assertEqual(
            synastry_identity_payload(true_chart)["settings"]["nodeType"], "true"
        )
        self.assertEqual(
            synastry_identity_payload(mean_chart)["settings"]["nodeType"], "mean"
        )

    def test_true_and_mean_do_not_mix_in_one_calculation(self) -> None:
        for node_type in ("true", "mean"):
            chart = self.engine.synastry(self.chart_a, self.chart_b, node_type=node_type)
            seen = {node for pair in _node_pairs(chart) for node in pair if node in NODES}
            self.assertLessEqual(len(seen), 1)
            overlays = {
                overlay.body
                for overlay in (*chart.a_bodies_in_b_houses, *chart.b_bodies_in_a_houses)
                if overlay.body in NODES
            }
            self.assertLessEqual(len(overlays), 1)
            if overlays:
                expected = "true_node" if node_type == "true" else "mean_node"
                self.assertEqual(overlays, {expected})

    def test_planet_to_planet_aspects_are_unchanged(self) -> None:
        true_chart = self.engine.synastry(self.chart_a, self.chart_b, node_type="true")
        mean_chart = self.engine.synastry(self.chart_a, self.chart_b, node_type="mean")
        self.assertEqual(_planet_pairs(true_chart), _planet_pairs(mean_chart))

    def test_mismatched_natal_conventions_require_explicit_setting(self) -> None:
        mean_engine = _swiss_engine(profile_with_node_type(WESTERN_MODERN_V1, "mean"))
        mean_a = mean_engine.natal(**CHART_A)
        true_b = self.engine.natal(**CHART_B)
        self.assertEqual(mean_a.meta.node_type, "mean")
        self.assertEqual(true_b.meta.node_type, "true")
        with self.assertRaises(InvalidCalculationProfileError) as raised:
            self.engine.synastry(mean_a, true_b)
        self.assertEqual(raised.exception.details["field"], "node_type")
        explicit = self.engine.synastry(mean_a, true_b, node_type="true")
        self.assertEqual(explicit.meta.node_type, "true")
        mean_explicit = self.engine.synastry(mean_a, true_b, node_type="mean")
        self.assertEqual(mean_explicit.meta.node_type, "mean")

    def test_both_natal_mean_omitted_relationship_stays_true(self) -> None:
        mean_engine = _swiss_engine(profile_with_node_type(WESTERN_MODERN_V1, "mean"))
        mean_a = mean_engine.natal(**CHART_A)
        mean_b = mean_engine.natal(**CHART_B)
        omitted = self.engine.synastry(mean_a, mean_b)
        self.assertEqual(omitted.meta.node_type, "true")
        node_bodies = {node for pair in _node_pairs(omitted) for node in pair if node in NODES}
        self.assertTrue(not node_bodies or node_bodies == {"true_node"})

    def test_invalid_node_type_is_structured(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError) as raised:
            self.engine.synastry(self.chart_a, self.chart_b, node_type="osculating")
        self.assertEqual(raised.exception.details["field"], "node_type")

    def test_sidereal_relationship_stays_deterministic(self) -> None:
        sidereal = self.engine.with_settings(zodiac="sidereal", ayanamsa="lahiri")
        a = sidereal.natal(**CHART_A)
        b = sidereal.natal(**CHART_B)
        first = sidereal.synastry(a, b, node_type="mean")
        second = sidereal.synastry(a, b, node_type="mean")
        self.assertEqual(first.meta.zodiac, "sidereal")
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(synastry_hash(first), synastry_hash(second))

    def test_natal_mean_does_not_mutate_relationship_default(self) -> None:
        mean_natal = _swiss_engine(profile_with_node_type(WESTERN_MODERN_V1, "mean"))
        self.assertEqual(mean_natal.relationship_profile.node_type, "true")
        self.assertIs(mean_natal.relationship_profile, RELATIONSHIP_WESTERN_V1)
        mean_natal.synastry(self.chart_a, self.chart_b, node_type="mean")
        self.assertEqual(RELATIONSHIP_WESTERN_V1.node_type, "true")
        self.assertIn("true_node", RELATIONSHIP_WESTERN_V1.synastry_bodies)

    def test_relationship_mean_does_not_mutate_natal_default(self) -> None:
        self.engine.synastry(self.chart_a, self.chart_b, node_type="mean")
        self.assertEqual(self.engine.profile.node_type, "true")
        self.assertEqual(WESTERN_MODERN_V1.node_type, "true")
        natal = self.engine.natal(**CHART_A)
        self.assertEqual(natal.meta.node_type, "true")


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class SynastryNodePublicParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _swiss_engine()
        self.client = TestClient(create_app())
        self.chart_a = self.engine.natal(**CHART_A)
        self.chart_b = self.engine.natal(**CHART_B)

    def test_http_python_agree_for_mean_synastry(self) -> None:
        python = self.engine.synastry(self.chart_a, self.chart_b, node_type="mean").to_dict()
        response = self.client.post(
            "/v1/charts/synastry",
            json={"chart_a": HTTP_A, "chart_b": HTTP_B, "node_type": "mean"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["meta"]["nodeType"], "mean")
        self.assertEqual(response.json()["crossAspects"], python["crossAspects"])
        self.assertEqual(response.json()["schemaVersion"], "1.5.0")

    def test_http_omitted_is_true(self) -> None:
        response = self.client.post(
            "/v1/charts/synastry", json={"chart_a": HTTP_A, "chart_b": HTTP_B}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["meta"]["nodeType"], "true")

    def test_http_invalid_node_type_is_422(self) -> None:
        response = self.client.post(
            "/v1/charts/synastry",
            json={"chart_a": HTTP_A, "chart_b": HTTP_B, "node_type": "osculating"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "REQUEST_VALIDATION_ERROR")

    def test_cli_exposes_relationship_node_type(self) -> None:
        parsed = _build_parser().parse_args(
            [
                "synastry",
                "--a-date",
                "1992-11-03",
                "--a-time",
                "14:35:00",
                "--a-timezone",
                "Asia/Ho_Chi_Minh",
                "--a-lat",
                "21.0285",
                "--a-lng",
                "105.8542",
                "--b-date",
                "1988-02-14",
                "--b-time",
                "09:20:00",
                "--b-timezone",
                "Europe/Paris",
                "--b-lat",
                "48.8566",
                "--b-lng",
                "2.3522",
                "--relationship-node-type",
                "mean",
            ]
        )
        self.assertEqual(parsed.relationship_node_type, "mean")
        self.assertIsNone(parsed.node_type)


if __name__ == "__main__":
    unittest.main()
