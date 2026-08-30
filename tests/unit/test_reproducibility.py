from __future__ import annotations

import json
import os
import unittest
from dataclasses import replace

from gbc_astro import AstrologyEngine
from gbc_astro.profiles.defaults import VEDIC_SIDEREAL_V1, WESTERN_MODERN_V1
from gbc_astro.profiles.resolve import resolve_calculation_profile
from gbc_astro.validation.reproducibility import (
    CALCULATION_HASH_VERSION,
    calculation_hash,
    calculation_identity_payload,
    encode_calculation_hash,
    identify_calculation_hash,
)
from tests.helpers import FixtureHouseCalculator, FixtureProvider

FIXTURE_KWARGS = {
    "local_datetime": "1992-11-03T14:35:00",
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542,
}


def _fixture_engine(profile=WESTERN_MODERN_V1) -> AstrologyEngine:
    return AstrologyEngine(
        provider=FixtureProvider(),
        house_calculator=FixtureHouseCalculator(),
        profile=profile,
    )


def _swiss_ephe_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    return bool(path and os.path.exists(os.path.join(path, "sepl_18.se1")))


class ReproducibilityTests(unittest.TestCase):
    def test_same_input_produces_same_hash(self) -> None:
        engine = _fixture_engine()
        kwargs = {**FIXTURE_KWARGS, "house_system": "equal"}
        first = engine.natal(**kwargs)
        second = engine.natal(**kwargs)
        self.assertEqual(calculation_hash(first), calculation_hash(second))
        self.assertEqual(first.to_json(), second.to_json())

    def test_hash_version_is_v2(self) -> None:
        chart = _fixture_engine().natal(**FIXTURE_KWARGS, house_system="equal")
        digest = calculation_hash(chart)
        self.assertEqual(CALCULATION_HASH_VERSION, "v2")
        self.assertTrue(digest.startswith("v2:"))
        self.assertEqual(identify_calculation_hash(digest).version, "v2")
        payload = calculation_identity_payload(chart)
        self.assertEqual(payload["calculationHashVersion"], "v2")
        self.assertEqual(payload["settings"]["nodeType"], "true")

    def test_repeated_identical_calculation_is_stable(self) -> None:
        engine = _fixture_engine()
        hashes = [
            calculation_hash(engine.natal(**FIXTURE_KWARGS, house_system="placidus"))
            for _ in range(3)
        ]
        self.assertEqual(len(set(hashes)), 1)

    def test_explicit_default_and_omitted_default_share_v2_hash(self) -> None:
        engine = _fixture_engine()
        omitted = engine.natal(**FIXTURE_KWARGS)
        explicit = engine.natal(**FIXTURE_KWARGS, house_system="placidus", unknown_time=False)
        self.assertEqual(omitted.meta.house_system, "placidus")
        self.assertEqual(calculation_hash(omitted), calculation_hash(explicit))

    def test_true_and_mean_node_produce_different_v2_identity(self) -> None:
        true_chart = _fixture_engine().natal(**FIXTURE_KWARGS)
        mean_chart = _fixture_engine(
            resolve_calculation_profile(node_type="mean")
        ).natal(**FIXTURE_KWARGS)
        self.assertNotEqual(calculation_hash(true_chart), calculation_hash(mean_chart))
        self.assertEqual(calculation_identity_payload(true_chart)["settings"]["nodeType"], "true")
        self.assertEqual(calculation_identity_payload(mean_chart)["settings"]["nodeType"], "mean")

    def test_standard_and_extended_produce_different_v2_identity(self) -> None:
        standard = _fixture_engine().natal(**FIXTURE_KWARGS)
        extended = _fixture_engine(
            resolve_calculation_profile(aspect_preset="extended")
        ).natal(**FIXTURE_KWARGS)
        self.assertEqual(
            calculation_identity_payload(standard)["settings"]["aspectPreset"], "standard"
        )
        self.assertEqual(
            calculation_identity_payload(extended)["settings"]["aspectPreset"], "extended"
        )
        self.assertNotEqual(calculation_hash(standard), calculation_hash(extended))

    def test_equivalent_custom_rules_share_v2_hash(self) -> None:
        first = _fixture_engine(
            resolve_calculation_profile(
                aspect_preset="custom",
                custom_aspect_rules=[
                    {"type": "opposition", "exactAngle": 180, "orb": 7},
                    {"type": "conjunction", "exact_angle": 0, "orb": 6},
                ],
            )
        ).natal(**FIXTURE_KWARGS)
        second = _fixture_engine(
            resolve_calculation_profile(
                aspect_preset="custom",
                custom_aspect_rules=[
                    {"type": "conjunction", "exact_angle": 0, "orb": 6},
                    {"type": "opposition", "exact_angle": 180, "orb": 7},
                ],
            )
        ).natal(**FIXTURE_KWARGS)
        self.assertEqual(calculation_hash(first), calculation_hash(second))
        self.assertEqual(
            calculation_identity_payload(first)["settings"]["customAspectRules"],
            [
                {"type": "conjunction", "exactAngle": 0.0, "orb": 6.0},
                {"type": "opposition", "exactAngle": 180.0, "orb": 7.0},
            ],
        )

    def test_explicit_standard_and_omitted_share_v2_hash(self) -> None:
        omitted = _fixture_engine().natal(**FIXTURE_KWARGS)
        explicit = _fixture_engine(
            resolve_calculation_profile(node_type="true", aspect_preset="standard")
        ).natal(**FIXTURE_KWARGS)
        self.assertEqual(calculation_hash(omitted), calculation_hash(explicit))
        self.assertEqual(
            calculation_identity_payload(omitted)["settings"]["aspectPreset"], "standard"
        )

    def test_additional_points_enter_v2_identity(self) -> None:
        omitted = _fixture_engine().natal(**FIXTURE_KWARGS)
        empty = _fixture_engine(
            resolve_calculation_profile(additional_points=[])
        ).natal(**FIXTURE_KWARGS)
        selected = _fixture_engine(
            resolve_calculation_profile(additional_points=["mean_lilith"])
        ).natal(**FIXTURE_KWARGS)
        self.assertEqual(calculation_hash(omitted), calculation_hash(empty))
        self.assertEqual(
            calculation_identity_payload(omitted)["settings"]["additionalPoints"], []
        )
        self.assertEqual(
            calculation_identity_payload(selected)["settings"]["additionalPoints"],
            ["mean_lilith"],
        )
        self.assertNotEqual(calculation_hash(omitted), calculation_hash(selected))

    def test_warning_text_and_sign_labels_do_not_change_v2_hash(self) -> None:
        chart = _fixture_engine().natal(
            local_datetime="1992-11-03",
            timezone="Asia/Ho_Chi_Minh",
            latitude=21.0285,
            longitude=105.8542,
            unknown_time=True,
        )
        self.assertTrue(chart.warnings)
        noisy_warning = replace(
            chart,
            warnings=(replace(chart.warnings[0], message="rewritten presentation copy"),),
        )
        sun = chart.bodies["sun"]
        relabeled = replace(
            chart,
            bodies={**chart.bodies, "sun": replace(sun, sign="not-a-sign", degree_in_sign=0.0)},
        )
        self.assertEqual(calculation_hash(chart), calculation_hash(noisy_warning))
        self.assertEqual(calculation_hash(chart), calculation_hash(relabeled))
        self.assertNotEqual(
            chart.to_dict()["warnings"][0]["message"],
            noisy_warning.to_dict()["warnings"][0]["message"],
        )

    def test_dictionary_ordering_does_not_change_v2_hash(self) -> None:
        chart = _fixture_engine().natal(**FIXTURE_KWARGS, house_system="equal")
        payload = calculation_identity_payload(chart)
        reversed_payload = {key: payload[key] for key in reversed(list(payload))}
        self.assertEqual(
            encode_calculation_hash(payload),
            encode_calculation_hash(reversed_payload),
        )
        self.assertEqual(encode_calculation_hash(payload), calculation_hash(chart))
        pretty = json.dumps(payload, indent=4, sort_keys=False)
        compact = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        self.assertNotEqual(pretty, compact)
        self.assertEqual(
            encode_calculation_hash(json.loads(pretty)),
            encode_calculation_hash(json.loads(compact)),
        )

    def test_astronomical_result_change_changes_v2_hash(self) -> None:
        engine = _fixture_engine()
        chart = engine.natal(**FIXTURE_KWARGS, house_system="equal")
        moved = replace(
            chart,
            bodies={
                **chart.bodies,
                "sun": replace(chart.bodies["sun"], longitude=chart.bodies["sun"].longitude + 0.01),
            },
        )
        later = engine.natal(
            local_datetime="1992-11-04T14:35:00",
            timezone="Asia/Ho_Chi_Minh",
            latitude=21.0285,
            longitude=105.8542,
            house_system="equal",
        )
        equal = engine.natal(**FIXTURE_KWARGS, house_system="equal")
        placidus = engine.natal(**FIXTURE_KWARGS, house_system="placidus")
        self.assertNotEqual(calculation_hash(chart), calculation_hash(moved))
        self.assertNotEqual(calculation_hash(chart), calculation_hash(later))
        self.assertNotEqual(calculation_hash(equal), calculation_hash(placidus))

    @unittest.skipUnless(_swiss_ephe_available(), "sidereal ayanamsa needs Swiss Ephemeris")
    def test_sidereal_profile_changes_v2_identity(self) -> None:
        tropical = _fixture_engine().natal(**FIXTURE_KWARGS)
        sidereal = _fixture_engine(VEDIC_SIDEREAL_V1).natal(**FIXTURE_KWARGS)
        self.assertNotEqual(calculation_hash(tropical), calculation_hash(sidereal))
        self.assertEqual(calculation_identity_payload(tropical)["settings"]["zodiac"], "tropical")
        self.assertEqual(calculation_identity_payload(sidereal)["settings"]["zodiac"], "sidereal")

    def test_legacy_v1_artifacts_are_identified_and_not_compared_to_v2(self) -> None:
        chart = _fixture_engine().natal(**FIXTURE_KWARGS, house_system="equal")
        v2 = calculation_hash(chart)
        # Historical v1: unprefixed SHA-256 of the full natal document.
        legacy_v1 = "aa75bc0898cce2b4ac44a564dc4c2a54fee3627cb57d425e3772b246b810b20c"
        identified_v1 = identify_calculation_hash(legacy_v1)
        identified_v2 = identify_calculation_hash(v2)
        self.assertEqual(identified_v1.version, "v1")
        self.assertEqual(identified_v1.digest, legacy_v1)
        self.assertEqual(identified_v1.encoded, legacy_v1)
        self.assertEqual(identified_v2.version, "v2")
        self.assertNotEqual(v2, legacy_v1)
        with self.assertRaises(ValueError):
            identify_calculation_hash("not-a-hash")
        with self.assertRaises(ValueError):
            identify_calculation_hash("v2:not-hex")


if __name__ == "__main__":
    unittest.main()
