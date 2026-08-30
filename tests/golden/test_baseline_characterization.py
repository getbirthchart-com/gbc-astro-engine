"""Lock the public default natal contract before calculation-settings work.

These tests characterize current behavior. They must not rewrite the Hanoi
golden fixture. An omitted setting continues to select:

Tropical · Placidus · True Node · modern-major-v1 · Chiron enabled
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from gbc_astro import AstrologyEngine, calculate_chart
from gbc_astro.api.app import create_app
from gbc_astro.constants import ASPECT_BODIES
from gbc_astro.errors import HouseCalculationUnavailableError
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.defaults import MODERN_MAJOR_V1, WESTERN_MODERN_V1
from gbc_astro.profiles.model import CalculationProfile
from gbc_astro.profiles.nodes import profile_with_node_type
from gbc_astro.providers.swiss import SwissEphemerisProvider
from gbc_astro.validation.reproducibility import (
    CALCULATION_HASH_VERSION,
    calculation_hash,
    identify_calculation_hash,
)
from tests.helpers import FixtureHouseCalculator, FixtureProvider

HANOI = {
    "local_datetime": "1992-11-03T14:35:00",
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542,
    "house_system": "placidus",
}
GOLDEN = Path(__file__).parents[1] / "fixtures" / "public_golden_cases.json"


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


def _swiss_engine(profile: CalculationProfile = WESTERN_MODERN_V1) -> AstrologyEngine:
    path = os.environ["GBC_SWISS_EPHE_PATH"]
    return AstrologyEngine(
        provider=SwissEphemerisProvider(ephemeris_path=path),
        house_calculator=SwissHouseCalculator(ephemeris_path=path),
        profile=profile,
    )


class DefaultProfileCharacterizationTests(unittest.TestCase):
    def test_western_modern_v1_is_the_legacy_default(self) -> None:
        self.assertEqual(WESTERN_MODERN_V1.zodiac, "tropical")
        self.assertEqual(WESTERN_MODERN_V1.house_system, "placidus")
        self.assertEqual(WESTERN_MODERN_V1.node_type, "true")
        self.assertEqual(WESTERN_MODERN_V1.aspect_profile.id, "modern-major-v1")
        self.assertIs(WESTERN_MODERN_V1.aspect_profile, MODERN_MAJOR_V1)
        self.assertEqual(WESTERN_MODERN_V1.aspect_bodies, ASPECT_BODIES)
        self.assertIn("true_node", WESTERN_MODERN_V1.aspect_bodies)
        self.assertNotIn("mean_node", WESTERN_MODERN_V1.aspect_bodies)
        self.assertIn("chiron", WESTERN_MODERN_V1.aspect_bodies)


@unittest.skipUnless(_swiss_available(), "Swiss Ephemeris data not configured")
class HanoiGoldenCharacterizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _swiss_engine()
        self.expected = json.loads(GOLDEN.read_text(encoding="utf-8"))[0]["expected"]

    def test_hanoi_1992_retains_published_values_and_fourteen_aspects(self) -> None:
        chart = self.engine.natal(**HANOI)
        self.assertAlmostEqual(chart.bodies["sun"].longitude, self.expected["sun_longitude"])
        self.assertAlmostEqual(chart.bodies["moon"].longitude, self.expected["moon_longitude"])
        self.assertAlmostEqual(
            chart.bodies["chiron"].longitude, self.expected["chiron_longitude"]
        )
        self.assertAlmostEqual(
            chart.angles["ascendant"].longitude, self.expected["ascendant_longitude"]
        )
        self.assertAlmostEqual(chart.angles["mc"].longitude, self.expected["mc_longitude"])
        self.assertAlmostEqual(
            chart.houses[1].cusp_longitude, self.expected["first_house_cusp_longitude"]
        )
        self.assertEqual(chart.derived.big_three, self.expected["big_three"])
        self.assertEqual(len(chart.aspects), self.expected["aspect_count"])
        self.assertEqual(chart.meta.zodiac, "tropical")
        self.assertEqual(chart.meta.house_system, "placidus")
        self.assertEqual(chart.meta.node_type, "true")
        self.assertEqual(chart.meta.aspect_profile, "modern-major-v1")
        self.assertEqual(chart.to_dict()["meta"]["nodeType"], "true")
        self.assertEqual(chart.to_dict()["schemaVersion"], "1.9.0")
        self.assertEqual(chart.to_dict()["meta"]["requestedHouseSystem"], "placidus")
        self.assertEqual(chart.to_dict()["meta"]["aspectPreset"], "standard")
        self.assertEqual(chart.to_dict()["meta"]["aspectProfileVersion"], "1.0.0")
        self.assertEqual(chart.to_dict()["meta"]["additionalPoints"], [])
        self.assertIn("chiron", chart.bodies)
        self.assertNotIn("mean_lilith", chart.bodies)
        self.assertNotIn("true_lilith", chart.bodies)
        node_aspects = [
            aspect
            for aspect in chart.aspects
            if aspect.body_a in {"true_node", "mean_node"}
            or aspect.body_b in {"true_node", "mean_node"}
        ]
        self.assertTrue(node_aspects)
        self.assertTrue(all("true_node" in (a.body_a, a.body_b) for a in node_aspects))
        self.assertFalse(any("mean_node" in (a.body_a, a.body_b) for a in node_aspects))

    def test_calculate_chart_matches_engine_natal_with_default_arguments(self) -> None:
        native = self.engine.natal(**HANOI)
        facade = calculate_chart(
            "1992-11-03",
            "14:35:00",
            latitude=21.0285,
            longitude=105.8542,
            timezone="Asia/Ho_Chi_Minh",
            engine=self.engine,
        )
        self.assertEqual(facade.to_json(), native.to_json())


@unittest.skipUnless(_swiss_available(), "Swiss Ephemeris data not configured")
class HttpLegacyRequestTests(unittest.TestCase):
    def test_http_natal_without_overrides_matches_engine_default(self) -> None:
        engine = _swiss_engine()
        direct = engine.natal(
            local_datetime="1992-11-03T14:35:00",
            timezone="Asia/Ho_Chi_Minh",
            latitude=21.0285,
            longitude=105.8542,
        ).to_dict()
        with TestClient(create_app()) as client:
            response = client.post(
                "/v1/charts/natal",
                json={
                    "local_date": "1992-11-03",
                    "local_time": "14:35:00",
                    "timezone": "Asia/Ho_Chi_Minh",
                    "latitude": 21.0285,
                    "longitude": 105.8542,
                },
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload, direct)
        self.assertEqual(payload["schemaVersion"], "1.9.0")
        self.assertEqual(payload["meta"]["zodiac"], "tropical")
        self.assertEqual(payload["meta"]["houseSystem"], "placidus")
        self.assertEqual(payload["meta"]["requestedHouseSystem"], "placidus")
        self.assertEqual(payload["meta"]["nodeType"], "true")
        self.assertEqual(payload["meta"]["aspectProfile"], "modern-major-v1")
        self.assertEqual(payload["meta"]["aspectPreset"], "standard")
        self.assertEqual(payload["meta"]["aspectProfileVersion"], "1.0.0")
        self.assertEqual(payload["meta"]["additionalPoints"], [])


class UnknownTimeContractTests(unittest.TestCase):
    def test_unknown_time_is_local_midnight_and_omits_time_sensitive_facts(self) -> None:
        engine = AstrologyEngine(
            provider=FixtureProvider(),
            house_calculator=FixtureHouseCalculator(),
        )
        chart = engine.natal(
            local_datetime="1992-11-03",
            timezone="Asia/Ho_Chi_Minh",
            latitude=21.0285,
            longitude=105.8542,
            unknown_time=True,
        )
        self.assertFalse(chart.subject.birth_time_known)
        self.assertEqual(chart.subject.local_datetime, "1992-11-03T00:00:00")
        self.assertEqual(chart.angles, {})
        self.assertEqual(chart.houses, ())
        self.assertIsNone(chart.meta.house_system)
        self.assertEqual(chart.meta.requested_house_system, "placidus")
        self.assertIsNone(chart.derived.big_three["rising"])
        self.assertIsNone(chart.derived.chart_ruler)
        self.assertNotIn("vertex", chart.points)
        self.assertNotIn("part_of_fortune", chart.points)
        self.assertIn("south_node", chart.points)
        self.assertTrue(all(body.house is None for body in chart.bodies.values()))
        self.assertEqual(chart.warnings[0].code, "UNKNOWN_BIRTH_TIME")
        self.assertNotIn("noon", chart.warnings[0].message.lower())
        self.assertNotIn("birth time is", chart.warnings[0].message.lower())


@unittest.skipUnless(_swiss_available(), "Swiss Ephemeris data not configured")
class HighLatitudePlacidusTests(unittest.TestCase):
    def test_placidus_raises_and_does_not_fallback(self) -> None:
        engine = _swiss_engine()
        with self.assertRaises(HouseCalculationUnavailableError) as raised:
            engine.natal(
                local_datetime="1992-06-21T12:00:00",
                timezone="UTC",
                latitude=70.0,
                longitude=0.0,
                house_system="placidus",
            )
        self.assertEqual(raised.exception.code, "HOUSE_CALCULATION_UNAVAILABLE")
        self.assertIn("No other system was substituted", str(raised.exception))
        self.assertFalse(raised.exception.details.get("definedAtAllLatitudes"))


@unittest.skipUnless(_swiss_available(), "Swiss Ephemeris data not configured")
class SiderealStateIsolationTests(unittest.TestCase):
    def test_tropical_after_sidereal_is_unchanged(self) -> None:
        tropical = _swiss_engine()
        from gbc_astro.profiles.defaults import VEDIC_SIDEREAL_V1

        sidereal = _swiss_engine(VEDIC_SIDEREAL_V1)
        first = tropical.natal(**HANOI)
        _ = sidereal.natal(**HANOI)
        second = tropical.natal(**HANOI)
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.meta.zodiac, "tropical")
        self.assertIsNone(first.meta.ayanamsa)


@unittest.skipUnless(_swiss_available(), "Swiss Ephemeris data not configured")
class NodeAspectConsistencyTests(unittest.TestCase):
    def test_mean_node_profile_aspects_mean_node_not_true_node(self) -> None:
        true_chart = _swiss_engine().natal(**HANOI)
        mean_engine = _swiss_engine(
            profile_with_node_type(WESTERN_MODERN_V1, "mean", profile_id="mean-node")
        )
        mean_chart = mean_engine.natal(**HANOI)

        self.assertEqual(true_chart.meta.node_type, "true")
        self.assertEqual(mean_chart.meta.node_type, "mean")
        self.assertIn("true_node", true_chart.bodies)
        self.assertIn("mean_node", true_chart.bodies)
        self.assertIn("true_node", mean_chart.bodies)
        self.assertIn("mean_node", mean_chart.bodies)

        true_ids = {(a.body_a, a.body_b, a.aspect_type) for a in true_chart.aspects}
        mean_ids = {(a.body_a, a.body_b, a.aspect_type) for a in mean_chart.aspects}
        self.assertTrue(any("true_node" in pair[:2] for pair in true_ids))
        self.assertFalse(any("mean_node" in pair[:2] for pair in true_ids))
        self.assertTrue(any("mean_node" in pair[:2] for pair in mean_ids))
        self.assertFalse(any("true_node" in pair[:2] for pair in mean_ids))

        self.assertEqual(
            mean_chart.points["south_node"].method, "mean_node_opposed"
        )
        self.assertEqual(
            true_chart.points["south_node"].method, "true_node_opposed"
        )
        self.assertNotEqual(
            true_chart.bodies["true_node"].longitude,
            mean_chart.bodies["mean_node"].longitude,
        )
        self.assertNotEqual(true_ids, mean_ids)

    def test_mean_draconic_uses_mean_node(self) -> None:
        engine = _swiss_engine(
            profile_with_node_type(WESTERN_MODERN_V1, "mean", profile_id="mean-node")
        )
        natal = engine.natal(**HANOI)
        draconic = engine.draconic(natal)
        self.assertEqual(draconic.meta["nodeType"], "mean")
        self.assertEqual(draconic.meta["nodeBody"], "mean_node")
        self.assertAlmostEqual(draconic.bodies["mean_node"].longitude, 0.0)
        self.assertNotAlmostEqual(draconic.bodies["true_node"].longitude, 0.0)


class CalculationHashCharacterizationTests(unittest.TestCase):
    def test_default_hash_is_versioned_v2_identity(self) -> None:
        engine = AstrologyEngine(
            provider=FixtureProvider(),
            house_calculator=FixtureHouseCalculator(),
        )
        chart = engine.natal(
            local_datetime="1992-11-03T14:35:00",
            timezone="Asia/Ho_Chi_Minh",
            latitude=21.0285,
            longitude=105.8542,
            house_system="equal",
        )
        digest = calculation_hash(chart)
        identified = identify_calculation_hash(digest)
        self.assertEqual(CALCULATION_HASH_VERSION, "v2")
        self.assertTrue(digest.startswith("v2:"))
        self.assertEqual(identified.version, "v2")
        self.assertEqual(calculation_hash(chart), digest)
        payload = chart.to_dict()
        self.assertEqual(payload["schemaVersion"], "1.9.0")
        self.assertEqual(payload["meta"]["nodeType"], "true")
        self.assertEqual(chart.meta.node_type, "true")

    def test_public_meta_includes_settings_on_schema_1_9_0(self) -> None:
        engine = AstrologyEngine(
            provider=FixtureProvider(),
            house_calculator=FixtureHouseCalculator(),
        )
        chart = engine.natal(
            local_datetime="1992-11-03T14:35:00",
            timezone="Asia/Ho_Chi_Minh",
            latitude=21.0285,
            longitude=105.8542,
            house_system="equal",
        )
        payload = json.loads(chart.to_json())
        self.assertEqual(payload["schemaVersion"], "1.9.0")
        self.assertEqual(payload["meta"]["nodeType"], "true")
        self.assertEqual(payload["meta"]["aspectPreset"], "standard")
        self.assertEqual(payload["meta"]["aspectProfile"], "modern-major-v1")
        self.assertEqual(payload["meta"]["aspectProfileVersion"], "1.0.0")
        self.assertEqual(payload["meta"]["additionalPoints"], [])
        self.assertIn("nodeType", payload["meta"])


if __name__ == "__main__":
    unittest.main()
