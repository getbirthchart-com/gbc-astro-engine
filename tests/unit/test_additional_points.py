"""Additional natal point identifiers. No ephemeris required."""

from __future__ import annotations

import unittest

from gbc_astro.constants import ASPECT_BODIES, BODY_IDS
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.profiles.additional import (
    PRODUCT_ADDITIONAL_POINTS,
    additional_body_ids,
    normalize_additional_points,
)
from gbc_astro.profiles.defaults import WESTERN_MODERN_V1
from gbc_astro.providers.asteroids import OPTIONAL_BODIES


class AdditionalPointIdentifierTests(unittest.TestCase):
    def test_lilith_ids_map_to_swiss_apogee_constants(self) -> None:
        self.assertEqual(OPTIONAL_BODIES["mean_lilith"], "MEAN_APOG")
        self.assertEqual(OPTIONAL_BODIES["true_lilith"], "OSCU_APOG")
        self.assertNotEqual(OPTIONAL_BODIES["mean_lilith"], OPTIONAL_BODIES["true_lilith"])

    def test_default_bodies_keep_chiron_and_exclude_lilith(self) -> None:
        self.assertIn("chiron", BODY_IDS)
        self.assertIn("chiron", ASPECT_BODIES)
        self.assertNotIn("mean_lilith", BODY_IDS)
        self.assertNotIn("true_lilith", BODY_IDS)
        self.assertNotIn("mean_lilith", ASPECT_BODIES)
        self.assertNotIn("true_lilith", WESTERN_MODERN_V1.aspect_bodies)
        self.assertEqual(WESTERN_MODERN_V1.additional_points, ())

    def test_empty_and_omitted_normalize_to_the_legacy_tuple(self) -> None:
        self.assertEqual(normalize_additional_points(None), ())
        self.assertEqual(normalize_additional_points([]), ())
        self.assertEqual(additional_body_ids(()), ())

    def test_product_order_and_osculating_alias(self) -> None:
        self.assertEqual(
            PRODUCT_ADDITIONAL_POINTS,
            ("mean_lilith", "true_lilith", "part_of_fortune", "vertex"),
        )
        self.assertEqual(
            normalize_additional_points(
                ["vertex", "part_of_fortune", "osculating_lilith", "mean_lilith"]
            ),
            ("mean_lilith", "true_lilith", "part_of_fortune", "vertex"),
        )
        self.assertEqual(
            additional_body_ids(("mean_lilith", "true_lilith", "vertex")),
            ("mean_lilith", "true_lilith"),
        )

    def test_unknown_duplicate_and_non_list_inputs_are_refused(self) -> None:
        cases: tuple[object, ...] = (
            ["lilith"],
            ["chiron"],
            ["ceres"],
            ["mean_lilith", "mean_lilith"],
            ["true_lilith", "osculating_lilith"],
            "mean_lilith",
            {"mean_lilith"},
        )
        for raw in cases:
            with self.subTest(raw=raw):
                with self.assertRaises(InvalidCalculationProfileError) as raised:
                    normalize_additional_points(raw)
                self.assertEqual(raised.exception.code, "INVALID_CALCULATION_PROFILE")
                self.assertEqual(raised.exception.details["field"], "additional_points")


if __name__ == "__main__":
    unittest.main()
