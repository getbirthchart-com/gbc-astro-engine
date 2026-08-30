"""Natal aspect preset and custom-rule validation. No ephemeris required."""

from __future__ import annotations

import math
import unittest

from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.profiles.aspects import (
    CANONICAL_ASPECT_ANGLES,
    MAX_NATAL_ASPECT_ORB,
    MODERN_EXTENDED_V1,
    STANDARD_ASPECT_PROFILE,
    apply_aspect_settings,
    custom_aspect_profile_id,
    normalize_aspect_preset,
    normalize_custom_aspect_rules,
    serialize_aspect_rules,
)
from gbc_astro.profiles.defaults import MODERN_MAJOR_V1, WESTERN_MODERN_V1
from gbc_astro.profiles.pattern import PATTERN_PROFILE_V1
from gbc_astro.profiles.synastry import SYNASTRY_ASPECT_PROFILE_V1
from gbc_astro.profiles.transit import TRANSIT_ASPECT_PROFILE_V1


class StandardAliasTests(unittest.TestCase):
    def test_standard_is_the_existing_major_profile_object(self) -> None:
        self.assertIs(STANDARD_ASPECT_PROFILE, MODERN_MAJOR_V1)
        self.assertEqual(STANDARD_ASPECT_PROFILE.id, "modern-major-v1")
        self.assertEqual(
            [
                (rule.aspect_type, rule.exact_angle, rule.orb)
                for rule in STANDARD_ASPECT_PROFILE.rules
            ],
            [
                ("conjunction", 0.0, 8.0),
                ("sextile", 60.0, 5.0),
                ("square", 90.0, 7.0),
                ("trine", 120.0, 7.0),
                ("opposition", 180.0, 8.0),
            ],
        )

    def test_modern_major_v1_alias_normalizes_to_standard(self) -> None:
        self.assertEqual(normalize_aspect_preset("standard"), "standard")
        self.assertEqual(normalize_aspect_preset("modern-major-v1"), "standard")
        self.assertEqual(normalize_aspect_preset("EXTENDED"), "extended")

    def test_extended_is_standard_plus_versioned_minors(self) -> None:
        self.assertEqual(MODERN_EXTENDED_V1.id, "modern-extended-v1")
        self.assertEqual(MODERN_EXTENDED_V1.version, "1.0.0")
        self.assertEqual(MODERN_EXTENDED_V1.rules[:5], MODERN_MAJOR_V1.rules)
        extra = {
            (rule.aspect_type, rule.exact_angle, rule.orb)
            for rule in MODERN_EXTENDED_V1.rules[5:]
        }
        self.assertEqual(
            extra,
            {
                ("semisextile", 30.0, 2.0),
                ("semisquare", 45.0, 2.0),
                ("sesquiquadrate", 135.0, 2.0),
                ("quincunx", 150.0, 3.0),
            },
        )


class CustomRuleValidationTests(unittest.TestCase):
    def test_empty_rules_are_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError) as raised:
            normalize_custom_aspect_rules([])
        self.assertEqual(raised.exception.details["field"], "custom_aspect_rules")

    def test_duplicate_type_and_angle_are_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError) as raised:
            normalize_custom_aspect_rules(
                [
                    {"type": "conjunction", "exact_angle": 0, "orb": 6},
                    {"type": "conjunction", "exact_angle": 0, "orb": 4},
                ]
            )
        self.assertEqual(raised.exception.details["type"], "conjunction")

    def test_unknown_type_is_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError) as raised:
            normalize_custom_aspect_rules(
                [{"type": "quintile", "exact_angle": 72, "orb": 2}]
            )
        self.assertEqual(raised.exception.details["aspectType"], "quintile")
        self.assertEqual(
            raised.exception.details["supported"], sorted(CANONICAL_ASPECT_ANGLES)
        )

    def test_negative_orb_is_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError):
            normalize_custom_aspect_rules(
                [{"type": "conjunction", "exact_angle": 0, "orb": -1}]
            )

    def test_orb_above_safe_maximum_is_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError) as raised:
            normalize_custom_aspect_rules(
                [
                    {
                        "type": "conjunction",
                        "exact_angle": 0,
                        "orb": MAX_NATAL_ASPECT_ORB + 0.1,
                    }
                ]
            )
        self.assertEqual(raised.exception.details["maxOrb"], MAX_NATAL_ASPECT_ORB)

    def test_exact_angle_out_of_range_is_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError):
            normalize_custom_aspect_rules(
                [{"type": "conjunction", "exact_angle": 181, "orb": 1}]
            )

    def test_nan_and_infinity_are_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError):
            normalize_custom_aspect_rules(
                [{"type": "conjunction", "exact_angle": math.nan, "orb": 6}]
            )
        with self.assertRaises(InvalidCalculationProfileError):
            normalize_custom_aspect_rules(
                [{"type": "conjunction", "exact_angle": 0, "orb": math.inf}]
            )

    def test_mismatched_canonical_angle_is_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError) as raised:
            normalize_custom_aspect_rules(
                [{"type": "conjunction", "exact_angle": 90, "orb": 6}]
            )
        self.assertEqual(raised.exception.details["canonicalExactAngle"], 0.0)

    def test_equivalent_rule_order_shares_identity(self) -> None:
        first = normalize_custom_aspect_rules(
            [
                {"type": "opposition", "exactAngle": 180, "orb": 7},
                {"type": "conjunction", "exact_angle": 0, "orb": 6},
            ]
        )
        second = normalize_custom_aspect_rules(
            [
                {"orb": 6, "type": "conjunction", "exact_angle": 0},
                {"type": "opposition", "exact_angle": 180, "orb": 7},
            ]
        )
        self.assertEqual(first, second)
        self.assertEqual(custom_aspect_profile_id(first), custom_aspect_profile_id(second))
        profile_id = custom_aspect_profile_id(first)
        self.assertTrue(profile_id.startswith("custom-v1:"))
        digest = profile_id.split(":", 1)[1]
        self.assertEqual(len(digest), 64)
        self.assertTrue(digest.islower())
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertEqual(serialize_aspect_rules(first), serialize_aspect_rules(second))
        self.assertEqual(
            custom_aspect_profile_id(first),
            custom_aspect_profile_id(first),
        )

    def test_standard_and_extended_ids_are_unchanged(self) -> None:
        self.assertEqual(MODERN_MAJOR_V1.id, "modern-major-v1")
        self.assertEqual(MODERN_EXTENDED_V1.id, "modern-extended-v1")

    def test_different_orbs_have_different_identity(self) -> None:
        tight = normalize_custom_aspect_rules(
            [{"type": "conjunction", "exact_angle": 0, "orb": 6}]
        )
        wide = normalize_custom_aspect_rules(
            [{"type": "conjunction", "exact_angle": 0, "orb": 7}]
        )
        self.assertNotEqual(custom_aspect_profile_id(tight), custom_aspect_profile_id(wide))

    def test_rules_with_non_custom_preset_are_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError):
            apply_aspect_settings(
                WESTERN_MODERN_V1,
                "standard",
                [{"type": "conjunction", "exact_angle": 0, "orb": 6}],
            )


class OtherProfilesUnchangedTests(unittest.TestCase):
    def test_synastry_and_transit_default_profiles_are_untouched(self) -> None:
        self.assertEqual(SYNASTRY_ASPECT_PROFILE_V1.id, "synastry-major-v1")
        self.assertEqual(
            [rule.orb for rule in SYNASTRY_ASPECT_PROFILE_V1.rules],
            [7.0, 3.0, 6.0, 6.0, 7.0],
        )
        self.assertEqual(TRANSIT_ASPECT_PROFILE_V1.id, "transit-major-v1")
        self.assertEqual(
            [rule.orb for rule in TRANSIT_ASPECT_PROFILE_V1.rules],
            [3.0, 3.0, 3.0, 3.0, 2.0],
        )
        self.assertIn("quincunx", PATTERN_PROFILE_V1.leg_orbs)
        self.assertEqual(PATTERN_PROFILE_V1.leg_orbs["quincunx"], 3.0)
        self.assertNotIn("quincunx", {rule.aspect_type for rule in MODERN_MAJOR_V1.rules})


if __name__ == "__main__":
    unittest.main()
