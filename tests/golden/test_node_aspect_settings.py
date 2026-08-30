"""Public True/Mean Node selector and Standard/Extended/Custom natal aspects."""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from gbc_astro import AstrologyEngine, calculate_chart
from gbc_astro.api.app import create_app
from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.cli import _build_parser
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.aspects import STANDARD_ASPECT_PROFILE
from gbc_astro.profiles.defaults import MODERN_MAJOR_V1, WESTERN_MODERN_V1
from gbc_astro.profiles.nodes import profile_with_node_type
from gbc_astro.profiles.resolve import resolve_calculation_profile
from gbc_astro.profiles.synastry import SYNASTRY_ASPECT_PROFILE_V1
from gbc_astro.profiles.transit import TRANSIT_ASPECT_PROFILE_V1
from gbc_astro.providers.swiss import SwissEphemerisProvider
from gbc_astro.validation.reproducibility import (
    calculation_hash,
    calculation_identity_payload,
)
from tests.helpers import FixtureHouseCalculator, FixtureProvider

HANOI = {
    "local_datetime": "1992-11-03T14:35:00",
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542,
}
HTTP_HANOI = {
    "local_date": "1992-11-03",
    "local_time": "14:35:00",
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542,
}
FACADE = {
    "date": "1992-11-03",
    "time": "14:35:00",
    "latitude": 21.0285,
    "longitude": 105.8542,
    "timezone": "Asia/Ho_Chi_Minh",
}


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


def _swiss_engine(profile=WESTERN_MODERN_V1) -> AstrologyEngine:
    path = os.environ["GBC_SWISS_EPHE_PATH"]
    return AstrologyEngine(
        provider=SwissEphemerisProvider(ephemeris_path=path),
        house_calculator=SwissHouseCalculator(ephemeris_path=path),
        profile=profile,
    )


def _fixture_engine(profile=WESTERN_MODERN_V1) -> AstrologyEngine:
    return AstrologyEngine(
        provider=FixtureProvider(),
        house_calculator=FixtureHouseCalculator(),
        profile=profile,
    )


def _node_aspect_ids(chart) -> set[tuple[str, str, str]]:
    return {
        (aspect.body_a, aspect.body_b, aspect.aspect_type)
        for aspect in chart.aspects
        if aspect.body_a in {"true_node", "mean_node"}
        or aspect.body_b in {"true_node", "mean_node"}
    }


class PublicNodeSelectorTests(unittest.TestCase):
    def test_omitted_node_equals_explicit_true(self) -> None:
        engine = _fixture_engine()
        omitted = calculate_chart(**FACADE, engine=engine)
        explicit = calculate_chart(**FACADE, engine=engine, node_type="true")
        self.assertEqual(omitted.to_json(), explicit.to_json())
        self.assertEqual(calculation_hash(omitted), calculation_hash(explicit))
        self.assertEqual(omitted.meta.node_type, "true")
        self.assertEqual(omitted.meta.aspect_preset, "standard")

    def test_resolver_true_is_the_same_object_as_legacy_default(self) -> None:
        self.assertIs(resolve_calculation_profile(node_type="true"), WESTERN_MODERN_V1)
        self.assertIs(
            profile_with_node_type(WESTERN_MODERN_V1, "true"), WESTERN_MODERN_V1
        )


@unittest.skipUnless(_swiss_available(), "Node/aspect settings need Swiss Ephemeris data")
class MeanNodePublicPathTests(unittest.TestCase):
    def test_mean_switches_aspects_south_node_draconic_metadata_and_hash(self) -> None:
        true_engine = _swiss_engine()
        mean_engine = _swiss_engine(resolve_calculation_profile(node_type="mean"))
        true_chart = true_engine.natal(**HANOI)
        mean_chart = mean_engine.natal(**HANOI)

        self.assertEqual(true_chart.meta.node_type, "true")
        self.assertEqual(mean_chart.meta.node_type, "mean")
        self.assertIn("true_node", true_chart.bodies)
        self.assertIn("mean_node", mean_chart.bodies)

        true_nodes = _node_aspect_ids(true_chart)
        mean_nodes = _node_aspect_ids(mean_chart)
        self.assertTrue(true_nodes)
        self.assertTrue(mean_nodes)
        self.assertTrue(all("true_node" in pair[:2] for pair in true_nodes))
        self.assertFalse(any("mean_node" in pair[:2] for pair in true_nodes))
        self.assertTrue(all("mean_node" in pair[:2] for pair in mean_nodes))
        self.assertFalse(any("true_node" in pair[:2] for pair in mean_nodes))

        selected_north = mean_chart.bodies["mean_node"].longitude
        south = mean_chart.points["south_node"].longitude
        self.assertAlmostEqual(
            normalize_longitude(south - selected_north), 180.0, places=10
        )
        self.assertEqual(mean_chart.points["south_node"].method, "mean_node_opposed")

        draconic = mean_engine.draconic(mean_chart)
        self.assertEqual(draconic.meta["nodeType"], "mean")
        self.assertEqual(draconic.meta["nodeBody"], "mean_node")
        self.assertAlmostEqual(draconic.bodies["mean_node"].longitude, 0.0)
        self.assertNotAlmostEqual(draconic.bodies["true_node"].longitude, 0.0)

        self.assertNotEqual(calculation_hash(true_chart), calculation_hash(mean_chart))
        self.assertEqual(
            calculation_identity_payload(mean_chart)["settings"]["nodeType"], "mean"
        )

    def test_public_mean_matches_canonical_helper_not_raw_replace(self) -> None:
        via_resolver = _swiss_engine(
            resolve_calculation_profile(node_type="mean")
        ).natal(**HANOI)
        via_helper = _swiss_engine(
            profile_with_node_type(WESTERN_MODERN_V1, "mean")
        ).natal(**HANOI)
        self.assertEqual(via_resolver.to_json(), via_helper.to_json())
        self.assertEqual(calculation_hash(via_resolver), calculation_hash(via_helper))


@unittest.skipUnless(_swiss_available(), "Node/aspect settings need Swiss Ephemeris data")
class StandardExtendedCustomNatalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _swiss_engine()

    def test_omitted_none_standard_and_modern_major_v1_match_and_keep_fourteen(self) -> None:
        omitted = self.engine.natal(**HANOI)
        via_none = _swiss_engine(
            resolve_calculation_profile(aspect_preset=None)
        ).natal(**HANOI)
        standard = _swiss_engine(
            resolve_calculation_profile(aspect_preset="standard")
        ).natal(**HANOI)
        alias = _swiss_engine(
            resolve_calculation_profile(aspect_preset="modern-major-v1")
        ).natal(**HANOI)
        facade = calculate_chart(**FACADE, engine=self.engine, aspect_preset="standard")
        self.assertEqual(len(omitted.aspects), 14)
        self.assertEqual(omitted.to_json(), via_none.to_json())
        self.assertEqual(omitted.to_json(), standard.to_json())
        self.assertEqual(omitted.to_json(), alias.to_json())
        self.assertEqual(omitted.to_json(), facade.to_json())
        self.assertEqual(calculation_hash(omitted), calculation_hash(standard))
        self.assertEqual(omitted.meta.aspect_preset, "standard")
        self.assertEqual(omitted.meta.aspect_profile, "modern-major-v1")
        self.assertIs(STANDARD_ASPECT_PROFILE, MODERN_MAJOR_V1)
        self.assertFalse(
            any(
                aspect.body_a in {"ascendant", "mc"}
                or aspect.body_b in {"ascendant", "mc"}
                for aspect in omitted.aspects
            )
        )

    def test_extended_adds_minor_aspects_without_dropping_standard(self) -> None:
        standard = self.engine.natal(**HANOI)
        extended = _swiss_engine(
            resolve_calculation_profile(aspect_preset="extended")
        ).natal(**HANOI)
        standard_ids = {
            (a.body_a, a.body_b, a.aspect_type) for a in standard.aspects
        }
        extended_ids = {
            (a.body_a, a.body_b, a.aspect_type) for a in extended.aspects
        }
        self.assertTrue(standard_ids.issubset(extended_ids))
        self.assertGreater(len(extended.aspects), len(standard.aspects))
        self.assertTrue(
            any(
                aspect.aspect_type
                in {"semisextile", "semisquare", "sesquiquadrate", "quincunx"}
                for aspect in extended.aspects
            )
        )
        self.assertEqual(extended.meta.aspect_preset, "extended")
        self.assertEqual(extended.meta.aspect_profile, "modern-extended-v1")
        self.assertEqual(extended.meta.aspect_profile_version, "1.0.0")
        self.assertNotEqual(calculation_hash(standard), calculation_hash(extended))

    def test_custom_rules_and_hash_are_order_independent(self) -> None:
        rules_a = [
            {"type": "opposition", "exactAngle": 180, "orb": 7},
            {"type": "conjunction", "exact_angle": 0, "orb": 6},
        ]
        rules_b = [
            {"type": "conjunction", "exact_angle": 0, "orb": 6},
            {"type": "opposition", "exact_angle": 180, "orb": 7},
        ]
        first = _swiss_engine(
            resolve_calculation_profile(aspect_preset="custom", custom_aspect_rules=rules_a)
        ).natal(**HANOI)
        second = _swiss_engine(
            resolve_calculation_profile(aspect_preset="custom", custom_aspect_rules=rules_b)
        ).natal(**HANOI)
        different = _swiss_engine(
            resolve_calculation_profile(
                aspect_preset="custom",
                custom_aspect_rules=[{"type": "conjunction", "exact_angle": 0, "orb": 5}],
            )
        ).natal(**HANOI)
        self.assertEqual(first.meta.custom_aspect_rules, second.meta.custom_aspect_rules)
        self.assertEqual(calculation_hash(first), calculation_hash(second))
        self.assertEqual(
            calculation_identity_payload(first)["settings"]["customAspectRules"],
            calculation_identity_payload(second)["settings"]["customAspectRules"],
        )
        self.assertNotEqual(calculation_hash(first), calculation_hash(different))
        self.assertEqual(first.meta.aspect_preset, "custom")
        self.assertTrue(str(first.meta.aspect_profile).startswith("custom-v1:"))
        digest = str(first.meta.aspect_profile).split(":", 1)[1]
        self.assertEqual(len(digest), 64)
        self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_synastry_and_transit_profiles_stay_on_their_own_tables(self) -> None:
        natal = _swiss_engine(
            resolve_calculation_profile(aspect_preset="extended")
        ).natal(**HANOI)
        other = self.engine.natal(
            local_datetime="1990-06-21T08:20:00",
            timezone="Europe/Berlin",
            latitude=52.52,
            longitude=13.405,
        )
        synastry = self.engine.synastry(natal, other)
        self.assertEqual(synastry.meta.aspect_profile, SYNASTRY_ASPECT_PROFILE_V1.id)
        transit = self.engine.transits(
            natal, datetime(2026, 8, 8, 12, tzinfo=timezone.utc)
        )
        self.assertEqual(transit.meta["transitAspectProfile"], TRANSIT_ASPECT_PROFILE_V1.id)


class InvalidCombinationTests(unittest.TestCase):
    def test_invalid_combinations_are_structured_errors(self) -> None:
        cases = (
            {"aspect_preset": "custom"},
            {
                "aspect_preset": "standard",
                "custom_aspect_rules": [{"type": "conjunction", "exact_angle": 0, "orb": 6}],
            },
            {"aspect_preset": "custom", "custom_aspect_rules": []},
            {
                "aspect_preset": "custom",
                "custom_aspect_rules": [{"type": "not-an-aspect", "exact_angle": 0, "orb": 1}],
            },
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(InvalidCalculationProfileError) as raised:
                    resolve_calculation_profile(**kwargs)
                self.assertEqual(raised.exception.code, "INVALID_CALCULATION_PROFILE")
                self.assertIn("field", raised.exception.details)


@unittest.skipUnless(_swiss_available(), "Node/aspect settings need Swiss Ephemeris data")
class HttpPythonCliParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _swiss_engine()
        self.client = TestClient(create_app())

    def test_http_python_agree_for_mean_and_extended(self) -> None:
        python = calculate_chart(
            **FACADE, engine=self.engine, node_type="mean", aspect_preset="extended"
        ).to_dict()
        response = self.client.post(
            "/v1/charts/natal",
            json={**HTTP_HANOI, "node_type": "mean", "aspect_preset": "extended"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), python)
        self.assertEqual(response.json()["meta"]["nodeType"], "mean")
        self.assertEqual(response.json()["meta"]["aspectPreset"], "extended")

    def test_http_custom_and_invalid_combinations(self) -> None:
        ok = self.client.post(
            "/v1/charts/natal",
            json={
                **HTTP_HANOI,
                "aspect_preset": "custom",
                "custom_aspect_rules": [
                    {"type": "conjunction", "exact_angle": 0, "orb": 6},
                    {"type": "opposition", "exact_angle": 180, "orb": 7},
                ],
            },
        )
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["meta"]["aspectPreset"], "custom")
        self.assertEqual(
            ok.json()["meta"]["customAspectRules"][0]["type"], "conjunction"
        )

        missing = self.client.post(
            "/v1/charts/natal",
            json={**HTTP_HANOI, "aspect_preset": "custom"},
        )
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(missing.json()["error"]["code"], "INVALID_CALCULATION_PROFILE")
        self.assertEqual(missing.json()["error"]["field"], "custom_aspect_rules")

    def test_cli_exposes_the_same_settings(self) -> None:
        parser = _build_parser()
        natal = parser.parse_args(
            [
                "natal",
                "--date",
                "1992-11-03",
                "--time",
                "14:35:00",
                "--timezone",
                "Asia/Ho_Chi_Minh",
                "--lat",
                "21.0285",
                "--lng",
                "105.8542",
                "--node-type",
                "mean",
                "--aspect-preset",
                "extended",
            ]
        )
        self.assertEqual(natal.node_type, "mean")
        self.assertEqual(natal.aspect_preset, "extended")


class PresentationDoesNotAffectHashTests(unittest.TestCase):
    def test_schema_version_does_not_enter_v2_identity(self) -> None:
        from dataclasses import replace

        chart = _fixture_engine().natal(
            local_datetime="1992-11-03T14:35:00",
            timezone="Asia/Ho_Chi_Minh",
            latitude=21.0285,
            longitude=105.8542,
        )
        relabeled = replace(chart, schema_version="9.9.9")
        self.assertNotEqual(chart.to_dict()["schemaVersion"], relabeled.to_dict()["schemaVersion"])
        self.assertEqual(calculation_hash(chart), calculation_hash(relabeled))


if __name__ == "__main__":
    unittest.main()
