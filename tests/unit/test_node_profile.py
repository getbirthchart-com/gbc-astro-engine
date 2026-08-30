"""Profile-level lunar node validation. No ephemeris required."""

from __future__ import annotations

import unittest
from dataclasses import replace

from gbc_astro import AstrologyEngine
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.profiles.defaults import RELATIONSHIP_WESTERN_V1, WESTERN_MODERN_V1
from gbc_astro.profiles.nodes import (
    NODE_BODY_BY_TYPE,
    aspect_bodies_for_node_type,
    profile_with_node_type,
    relationship_profile_with_node_type,
    selected_node_body_id,
    validate_node_settings,
)
from tests.helpers import FixtureHouseCalculator, FixtureProvider


class NodeResolutionTests(unittest.TestCase):
    def test_true_and_mean_map_to_distinct_bodies(self) -> None:
        self.assertEqual(selected_node_body_id("true"), "true_node")
        self.assertEqual(selected_node_body_id("mean"), "mean_node")
        self.assertEqual(set(NODE_BODY_BY_TYPE), {"true", "mean"})

    def test_aspect_bodies_for_mean_replace_true_node_only(self) -> None:
        rewritten = aspect_bodies_for_node_type(WESTERN_MODERN_V1.aspect_bodies, "mean")
        self.assertIn("mean_node", rewritten)
        self.assertNotIn("true_node", rewritten)
        self.assertEqual(
            [body for body in rewritten if body != "mean_node"],
            [body for body in WESTERN_MODERN_V1.aspect_bodies if body != "true_node"],
        )


class NodeProfileValidationTests(unittest.TestCase):
    def test_default_western_profile_is_valid(self) -> None:
        AstrologyEngine(
            provider=FixtureProvider(),
            house_calculator=FixtureHouseCalculator(),
            profile=WESTERN_MODERN_V1,
        )

    def test_unsupported_node_type_fails_before_calculation(self) -> None:
        # Raw replace is the negative path: callers switching node convention
        # must use profile_with_node_type so aspect bodies stay aligned.
        broken = replace(WESTERN_MODERN_V1, id="bad-node", node_type="osculating")
        with self.assertRaises(InvalidCalculationProfileError) as raised:
            AstrologyEngine(
                provider=FixtureProvider(),
                house_calculator=FixtureHouseCalculator(),
                profile=broken,
            )
        self.assertEqual(raised.exception.code, "INVALID_CALCULATION_PROFILE")
        self.assertIn("nodeType", raised.exception.details)

    def test_both_nodes_in_aspect_bodies_are_refused(self) -> None:
        broken = replace(
            WESTERN_MODERN_V1,
            aspect_bodies=WESTERN_MODERN_V1.aspect_bodies + ("mean_node",),
        )
        with self.assertRaises(InvalidCalculationProfileError) as raised:
            AstrologyEngine(profile=broken)
        self.assertIn("one lunar node", str(raised.exception))

    def test_mean_type_with_true_node_aspects_is_refused_not_repaired(self) -> None:
        mismatched = replace(WESTERN_MODERN_V1, id="mismatched", node_type="mean")
        with self.assertRaises(InvalidCalculationProfileError) as raised:
            AstrologyEngine(
                provider=FixtureProvider(),
                house_calculator=FixtureHouseCalculator(),
                profile=mismatched,
            )
        self.assertIn("does not match node_type", str(raised.exception))
        self.assertEqual(raised.exception.details["selectedNode"], "mean_node")
        self.assertEqual(raised.exception.details["aspectNodes"], ["true_node"])

    def test_true_type_with_mean_node_aspects_is_refused(self) -> None:
        mismatched = replace(
            WESTERN_MODERN_V1,
            id="mismatched-true",
            aspect_bodies=aspect_bodies_for_node_type(
                WESTERN_MODERN_V1.aspect_bodies, "mean"
            ),
        )
        with self.assertRaises(InvalidCalculationProfileError):
            validate_node_settings(mismatched.node_type, mismatched.aspect_bodies)

    def test_aligned_mean_profile_is_accepted(self) -> None:
        profile = profile_with_node_type(
            WESTERN_MODERN_V1, "mean", profile_id="mean-node"
        )
        engine = AstrologyEngine(
            provider=FixtureProvider(),
            house_calculator=FixtureHouseCalculator(),
            profile=profile,
        )
        self.assertEqual(engine.profile.node_type, "mean")
        self.assertIn("mean_node", engine.profile.aspect_bodies)
        self.assertNotIn("true_node", engine.profile.aspect_bodies)


class RelationshipNodeProfileTests(unittest.TestCase):
    def test_default_relationship_profile_is_true_node(self) -> None:
        self.assertEqual(RELATIONSHIP_WESTERN_V1.node_type, "true")
        self.assertIn("true_node", RELATIONSHIP_WESTERN_V1.synastry_bodies)
        self.assertNotIn("mean_node", RELATIONSHIP_WESTERN_V1.synastry_bodies)
        self.assertNotIn("south_node", RELATIONSHIP_WESTERN_V1.synastry_bodies)

    def test_relationship_mean_helper_does_not_mutate_default(self) -> None:
        mean = relationship_profile_with_node_type(RELATIONSHIP_WESTERN_V1, "mean")
        self.assertEqual(mean.node_type, "mean")
        self.assertIn("mean_node", mean.synastry_bodies)
        self.assertNotIn("true_node", mean.synastry_bodies)
        self.assertEqual(RELATIONSHIP_WESTERN_V1.node_type, "true")
        self.assertIn("true_node", RELATIONSHIP_WESTERN_V1.synastry_bodies)
        self.assertNotIn("mean_node", RELATIONSHIP_WESTERN_V1.synastry_bodies)

    def test_raw_replace_is_not_the_public_switch(self) -> None:
        from dataclasses import replace as dc_replace

        broken = dc_replace(RELATIONSHIP_WESTERN_V1, node_type="mean")
        with self.assertRaises(InvalidCalculationProfileError):
            AstrologyEngine(
                provider=FixtureProvider(),
                house_calculator=FixtureHouseCalculator(),
                relationship_profile=broken,
            )

    def test_natal_mean_does_not_mutate_relationship_default(self) -> None:
        natal_mean = profile_with_node_type(WESTERN_MODERN_V1, "mean")
        engine = AstrologyEngine(
            provider=FixtureProvider(),
            house_calculator=FixtureHouseCalculator(),
            profile=natal_mean,
        )
        self.assertEqual(engine.profile.node_type, "mean")
        self.assertEqual(engine.relationship_profile.node_type, "true")
        self.assertIs(engine.relationship_profile, RELATIONSHIP_WESTERN_V1)


if __name__ == "__main__":
    unittest.main()
