"""Synastry and composite integration tests."""

from __future__ import annotations

import json
import os
import unittest

from gbc_astro import AstrologyEngine
from gbc_astro.astronomy.circular import shortest_angular_distance
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.defaults import RELATIONSHIP_WESTERN_V1
from gbc_astro.providers.swiss import SwissEphemerisProvider


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


@unittest.skipUnless(_swiss_available(), "Relationship charts need Swiss Ephemeris data")
class RelationshipTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.chart_a = self.engine.natal(
            "1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542
        )
        self.chart_b = self.engine.natal("1990-06-21T08:20:00", "Europe/Berlin", 52.52, 13.405)

    # --- synastry -------------------------------------------------------

    def test_cross_aspects_are_the_full_product_not_combinations(self) -> None:
        """A.sun to B.sun is a real contact, and A.sun-B.moon differs from A.moon-B.sun."""
        synastry = self.engine.synastry(self.chart_a, self.chart_b)
        pairs = {(aspect.body_a, aspect.body_b) for aspect in synastry.cross_aspects}

        reversed_pairs = {(b, a) for a, b in pairs}
        self.assertNotEqual(pairs, reversed_pairs & pairs, "orientation must be meaningful")
        for aspect in synastry.cross_aspects:
            self.assertIn(aspect.body_a, self.chart_a.bodies)
            self.assertIn(aspect.body_b, self.chart_b.bodies)

    def test_cross_aspect_orbs_agree_with_the_profile(self) -> None:
        synastry = self.engine.synastry(self.chart_a, self.chart_b)
        rules = {rule.aspect_type: rule for rule in RELATIONSHIP_WESTERN_V1.aspect_profile.rules}

        for aspect in synastry.cross_aspects:
            rule = rules[aspect.aspect_type]
            separation = shortest_angular_distance(
                self.chart_a.bodies[aspect.body_a].longitude,
                self.chart_b.bodies[aspect.body_b].longitude,
            )
            self.assertAlmostEqual(aspect.actual_angle, separation, places=9)
            self.assertAlmostEqual(aspect.orb, abs(separation - rule.exact_angle), places=9)
            self.assertLessEqual(aspect.orb, rule.orb)

    def test_cross_aspect_phase_is_always_indeterminate(self) -> None:
        """Two natal charts share no timeline, so applying/separating cannot apply."""
        synastry = self.engine.synastry(self.chart_a, self.chart_b)
        self.assertTrue(synastry.cross_aspects)
        for aspect in synastry.cross_aspects:
            self.assertEqual(aspect.phase, "indeterminate")
        self.assertIn(
            "SYNASTRY_PHASE_INDETERMINATE", {w.code for w in synastry.warnings}
        )

    def test_house_overlays_run_both_directions_against_the_right_chart(self) -> None:
        synastry = self.engine.synastry(self.chart_a, self.chart_b)

        self.assertEqual(len(synastry.a_bodies_in_b_houses), len(self.chart_a.bodies))
        self.assertEqual(len(synastry.b_bodies_in_a_houses), len(self.chart_b.bodies))
        for overlay in synastry.a_bodies_in_b_houses:
            self.assertEqual(overlay.body_chart, "A")
            self.assertEqual(overlay.house_chart, "B")
            self.assertIn(overlay.house, range(1, 13))
            self.assertAlmostEqual(
                overlay.body_longitude, self.chart_a.bodies[overlay.body].longitude
            )
        for overlay in synastry.b_bodies_in_a_houses:
            self.assertEqual(overlay.body_chart, "B")
            self.assertEqual(overlay.house_chart, "A")

    def test_angle_interactions_cover_both_directions(self) -> None:
        synastry = self.engine.synastry(self.chart_a, self.chart_b)
        directions = {
            (interaction.body_chart, interaction.angle_chart)
            for interaction in synastry.angle_interactions
        }
        self.assertIn(("A", "B"), directions)
        self.assertIn(("B", "A"), directions)
        for interaction in synastry.angle_interactions:
            self.assertNotEqual(interaction.body_chart, interaction.angle_chart)
            self.assertIn(interaction.angle, ("ascendant", "mc", "descendant", "ic"))

    def test_unknown_birth_time_omits_overlays_instead_of_inventing_them(self) -> None:
        unknown = self.engine.natal(
            "1990-06-21", "Europe/Berlin", 52.52, 13.405, unknown_time=True
        )
        synastry = self.engine.synastry(self.chart_a, unknown)

        self.assertEqual(synastry.a_bodies_in_b_houses, ())
        self.assertTrue(synastry.b_bodies_in_a_houses, "A still has houses")
        self.assertTrue(synastry.cross_aspects, "cross aspects need no houses")

        codes = {warning.code for warning in synastry.warnings}
        self.assertIn("SYNASTRY_HOUSE_OVERLAY_UNAVAILABLE", codes)
        self.assertIn("SYNASTRY_ANGLE_INTERACTIONS_PARTIAL", codes)

    def test_synastry_with_self_puts_every_body_at_zero_orb_conjunction(self) -> None:
        synastry = self.engine.synastry(self.chart_a, self.chart_a)
        same_body = {
            aspect.body_a: aspect
            for aspect in synastry.cross_aspects
            if aspect.body_a == aspect.body_b
        }
        self.assertEqual(len(same_body), len(self.chart_a.bodies))
        for aspect in same_body.values():
            self.assertEqual(aspect.aspect_type, "conjunction")
            self.assertAlmostEqual(aspect.orb, 0.0, places=9)

    def test_mismatched_schema_versions_are_refused(self) -> None:
        from dataclasses import replace

        other = replace(self.chart_b, schema_version="9.9.9")
        with self.assertRaises(InvalidCalculationProfileError):
            self.engine.synastry(self.chart_a, other)

    # --- composite ------------------------------------------------------

    def test_composite_positions_are_midpoints_of_the_pair(self) -> None:
        composite = self.engine.composite(self.chart_a, self.chart_b)
        for body_id, body in composite.bodies.items():
            first = self.chart_a.bodies[body_id].longitude
            second = self.chart_b.bodies[body_id].longitude
            self.assertAlmostEqual(
                shortest_angular_distance(body.longitude, first),
                shortest_angular_distance(body.longitude, second),
                places=8,
            )

    def test_composite_carries_no_speed_distance_or_retrograde(self) -> None:
        """A composite chart is not an instant, so those fields have no meaning."""
        composite = self.engine.composite(self.chart_a, self.chart_b)
        for body in composite.bodies.values():
            self.assertIsNone(body.speed_longitude)
            self.assertIsNone(body.distance)
            self.assertIsNone(body.retrograde)
            self.assertIsNone(body.house)

    def test_composite_declares_its_methodology_and_omits_houses(self) -> None:
        composite = self.engine.composite(self.chart_a, self.chart_b)
        self.assertEqual(composite.meta.composite_position_method, "shortest_arc_midpoint")
        self.assertIsNone(composite.meta.composite_house_method)
        self.assertIn("COMPOSITE_HOUSES_UNAVAILABLE", {w.code for w in composite.warnings})

    def test_composite_with_self_reproduces_the_original_longitudes(self) -> None:
        composite = self.engine.composite(self.chart_a, self.chart_a)
        for body_id, body in composite.bodies.items():
            self.assertAlmostEqual(
                shortest_angular_distance(body.longitude, self.chart_a.bodies[body_id].longitude),
                0.0,
                places=9,
            )

    def test_composite_is_order_independent_for_non_opposed_bodies(self) -> None:
        forward = self.engine.composite(self.chart_a, self.chart_b)
        backward = self.engine.composite(self.chart_b, self.chart_a)
        ambiguous = {m.body_id for m in forward.midpoints if m.ambiguous}

        for body_id, body in forward.bodies.items():
            if body_id in ambiguous:
                continue
            self.assertAlmostEqual(
                shortest_angular_distance(body.longitude, backward.bodies[body_id].longitude),
                0.0,
                places=8,
                msg=body_id,
            )

    def test_composite_records_every_midpoint_with_its_inputs(self) -> None:
        composite = self.engine.composite(self.chart_a, self.chart_b)
        self.assertEqual(len(composite.midpoints), len(composite.bodies))
        for midpoint in composite.midpoints:
            self.assertAlmostEqual(
                midpoint.longitude_a, self.chart_a.bodies[midpoint.body_id].longitude
            )
            self.assertAlmostEqual(
                midpoint.longitude_b, self.chart_b.bodies[midpoint.body_id].longitude
            )
            self.assertLessEqual(midpoint.separation, 180.0)

    def test_composite_unknown_time_omits_angles(self) -> None:
        unknown = self.engine.natal(
            "1990-06-21", "Europe/Berlin", 52.52, 13.405, unknown_time=True
        )
        composite = self.engine.composite(self.chart_a, unknown)

        self.assertEqual(composite.angles, {})
        self.assertIsNone(composite.meta.composite_angle_method)
        self.assertIn("COMPOSITE_ANGLES_UNAVAILABLE", {w.code for w in composite.warnings})

    # --- canonical JSON -------------------------------------------------

    def test_synastry_json_matches_the_documented_contract(self) -> None:
        payload = json.loads(self.engine.synastry(self.chart_a, self.chart_b).to_json())
        self.assertEqual(
            set(payload),
            {
                "schemaVersion",
                "meta",
                "chartA",
                "chartB",
                "crossAspects",
                "aBodiesInBHouses",
                "bBodiesInAHouses",
                "angleInteractions",
                "warnings",
            },
        )
        self.assertEqual(payload["schemaVersion"], "1.0.0")
        self.assertEqual(payload["meta"]["relationshipProfile"], "relationship-western-v1")

    def test_relationship_json_is_deterministic(self) -> None:
        for build in (self.engine.synastry, self.engine.composite):
            with self.subTest(build=build.__name__):
                self.assertEqual(
                    build(self.chart_a, self.chart_b).to_json(),
                    build(self.chart_a, self.chart_b).to_json(),
                )
