"""Calculation-profile override resolver. No ephemeris required."""

from __future__ import annotations

import unittest

from gbc_astro.errors import InvalidCalculationProfileError, UnsupportedHouseSystemError
from gbc_astro.houses.systems import PRODUCT_HOUSE_SYSTEMS
from gbc_astro.profiles.defaults import VEDIC_SIDEREAL_V1, WESTERN_MODERN_V1
from gbc_astro.profiles.resolve import resolve_calculation_profile


class ResolveCalculationProfileTests(unittest.TestCase):
    def test_omitted_overrides_return_the_legacy_base(self) -> None:
        self.assertIs(resolve_calculation_profile(), WESTERN_MODERN_V1)
        self.assertIs(resolve_calculation_profile(WESTERN_MODERN_V1), WESTERN_MODERN_V1)

    def test_explicit_placidus_equals_omitted(self) -> None:
        self.assertIs(
            resolve_calculation_profile(house_system="placidus"),
            WESTERN_MODERN_V1,
        )
        self.assertIs(
            resolve_calculation_profile(house_system="Placidus"),
            WESTERN_MODERN_V1,
        )

    def test_whole_sign_and_equal_are_product_overrides(self) -> None:
        self.assertEqual(PRODUCT_HOUSE_SYSTEMS, ("placidus", "whole_sign", "equal"))
        whole = resolve_calculation_profile(house_system="whole_sign")
        equal = resolve_calculation_profile(house_system="equal")
        self.assertEqual(whole.house_system, "whole_sign")
        self.assertEqual(equal.house_system, "equal")
        self.assertEqual(whole.zodiac, "tropical")
        self.assertEqual(whole.node_type, "true")
        self.assertIs(whole.aspect_profile, WESTERN_MODERN_V1.aspect_profile)

    def test_professional_systems_remain_available(self) -> None:
        koch = resolve_calculation_profile(house_system="koch")
        self.assertEqual(koch.house_system, "koch")

    def test_invalid_house_system_is_refused(self) -> None:
        with self.assertRaises(UnsupportedHouseSystemError) as raised:
            resolve_calculation_profile(house_system="vehlow")
        self.assertEqual(raised.exception.details["houseSystem"], "vehlow")
        self.assertEqual(
            raised.exception.details["productHouseSystems"],
            list(PRODUCT_HOUSE_SYSTEMS),
        )

    def test_empty_additional_points_equals_omitted(self) -> None:
        self.assertIs(resolve_calculation_profile(additional_points=[]), WESTERN_MODERN_V1)
        self.assertIs(resolve_calculation_profile(additional_points=()), WESTERN_MODERN_V1)

    def test_mean_lilith_is_opt_in_and_not_an_aspect_body(self) -> None:
        profile = resolve_calculation_profile(additional_points=["mean_lilith"])
        self.assertEqual(profile.additional_points, ("mean_lilith",))
        self.assertNotIn("mean_lilith", profile.aspect_bodies)
        self.assertIn("chiron", profile.aspect_bodies)
        self.assertIsNot(profile, WESTERN_MODERN_V1)

    def test_additional_points_are_canonicalized_in_product_order(self) -> None:
        profile = resolve_calculation_profile(
            additional_points=["vertex", "osculating_lilith", "mean_lilith"]
        )
        self.assertEqual(
            profile.additional_points,
            ("mean_lilith", "true_lilith", "vertex"),
        )

    def test_unknown_and_duplicate_additional_points_are_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError) as raised:
            resolve_calculation_profile(additional_points=["lilith"])
        self.assertEqual(raised.exception.code, "INVALID_CALCULATION_PROFILE")
        self.assertEqual(raised.exception.details["field"], "additional_points")
        with self.assertRaises(InvalidCalculationProfileError):
            resolve_calculation_profile(additional_points=["mean_lilith", "mean_lilith"])
        with self.assertRaises(InvalidCalculationProfileError):
            resolve_calculation_profile(
                additional_points=["true_lilith", "osculating_lilith"]
            )
        with self.assertRaises(InvalidCalculationProfileError):
            resolve_calculation_profile(additional_points="mean_lilith")

    def test_explicit_true_node_equals_omitted(self) -> None:
        self.assertIs(resolve_calculation_profile(node_type="true"), WESTERN_MODERN_V1)
        self.assertIs(resolve_calculation_profile(node_type="True"), WESTERN_MODERN_V1)

    def test_mean_node_uses_canonical_helper(self) -> None:
        mean = resolve_calculation_profile(node_type="mean")
        self.assertEqual(mean.node_type, "mean")
        self.assertIn("mean_node", mean.aspect_bodies)
        self.assertNotIn("true_node", mean.aspect_bodies)
        self.assertEqual(mean.house_system, "placidus")

    def test_standard_aliases_are_the_legacy_major_profile(self) -> None:
        omitted = resolve_calculation_profile()
        standard = resolve_calculation_profile(aspect_preset="standard")
        alias = resolve_calculation_profile(aspect_preset="modern-major-v1")
        none = resolve_calculation_profile(aspect_preset=None)
        self.assertIs(omitted, WESTERN_MODERN_V1)
        self.assertIs(standard, WESTERN_MODERN_V1)
        self.assertIs(alias, WESTERN_MODERN_V1)
        self.assertIs(none, WESTERN_MODERN_V1)
        self.assertIs(omitted.aspect_profile, WESTERN_MODERN_V1.aspect_profile)

    def test_extended_is_a_versioned_superset(self) -> None:
        from gbc_astro.profiles.aspects import MODERN_EXTENDED_V1, STANDARD_ASPECT_PROFILE

        extended = resolve_calculation_profile(aspect_preset="extended")
        self.assertIs(extended.aspect_profile, MODERN_EXTENDED_V1)
        self.assertEqual(extended.aspect_preset, "extended")
        self.assertEqual(extended.aspect_profile.version, "1.0.0")
        self.assertEqual(
            set(rule.aspect_type for rule in STANDARD_ASPECT_PROFILE.rules).issubset(
                rule.aspect_type for rule in extended.aspect_profile.rules
            ),
            True,
        )

    def test_custom_rules_are_normalized_and_order_independent(self) -> None:
        first = resolve_calculation_profile(
            aspect_preset="custom",
            custom_aspect_rules=[
                {"type": "opposition", "exactAngle": 180, "orb": 7},
                {"type": "conjunction", "exact_angle": 0, "orb": 6},
            ],
        )
        second = resolve_calculation_profile(
            aspect_preset="custom",
            custom_aspect_rules=[
                {"type": "conjunction", "exact_angle": 0, "orb": 6},
                {"type": "opposition", "exactAngle": 180, "orb": 7},
            ],
        )
        self.assertEqual(first.aspect_preset, "custom")
        self.assertEqual(first.aspect_profile.id, second.aspect_profile.id)
        self.assertEqual(first.aspect_profile.rules, second.aspect_profile.rules)
        self.assertEqual(first.aspect_profile.rules[0].aspect_type, "conjunction")

    def test_custom_without_rules_is_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError) as raised:
            resolve_calculation_profile(aspect_preset="custom")
        self.assertEqual(raised.exception.details["field"], "custom_aspect_rules")

    def test_rules_with_standard_are_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError) as raised:
            resolve_calculation_profile(
                aspect_preset="standard",
                custom_aspect_rules=[{"type": "conjunction", "exact_angle": 0, "orb": 6}],
            )
        self.assertEqual(raised.exception.details["field"], "custom_aspect_rules")

    def test_sidereal_override_keeps_house_system(self) -> None:
        profile = resolve_calculation_profile(
            house_system="equal",
            zodiac="sidereal",
            ayanamsa="lahiri",
        )
        self.assertEqual(profile.zodiac, "sidereal")
        self.assertEqual(profile.ayanamsa, "lahiri")
        self.assertEqual(profile.house_system, "equal")

    def test_sidereal_without_ayanamsa_is_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError):
            resolve_calculation_profile(zodiac="sidereal")

    def test_public_resolver_accepts_every_engine_ayanamsa(self) -> None:
        from gbc_astro.profiles.ayanamsa import AYANAMSA_PROFILES

        for ayanamsa_id in AYANAMSA_PROFILES:
            with self.subTest(ayanamsa=ayanamsa_id):
                profile = resolve_calculation_profile(
                    zodiac="sidereal", ayanamsa=ayanamsa_id
                )
                self.assertEqual(profile.zodiac, "sidereal")
                self.assertEqual(profile.ayanamsa, ayanamsa_id)

    def test_tropical_with_ayanamsa_is_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError) as raised:
            resolve_calculation_profile(zodiac="tropical", ayanamsa="lahiri")
        self.assertEqual(raised.exception.details["field"], "ayanamsa")

    def test_unknown_zodiac_is_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError) as raised:
            resolve_calculation_profile(zodiac="draconic")
        self.assertEqual(raised.exception.details["field"], "zodiac")

    def test_vedic_base_is_unchanged_when_overrides_match(self) -> None:
        self.assertIs(
            resolve_calculation_profile(
                VEDIC_SIDEREAL_V1,
                house_system="whole_sign",
                zodiac="sidereal",
                ayanamsa="lahiri",
            ),
            VEDIC_SIDEREAL_V1,
        )


if __name__ == "__main__":
    unittest.main()
