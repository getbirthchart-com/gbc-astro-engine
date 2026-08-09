"""Evidence identity, and the one point that was counted twice.

Two things are pinned here.

**Deterministic IDs.** Everything downstream of synastry addresses facts by id:
score contributions cite them, evidence bundles collect them, a report outline
orders them, and the relationship-timing layer marks them as currently
activated. An id that is not stable across runs, or that changes when an orb
profile is revised, silently breaks every stored reference to it.

**One lunar node.** A chart publishes both the true and the mean node because a
caller may want either, but they are one point computed two ways, about a degree
apart. Letting both form aspects doubled every node contact and put a permanent
"true_node conjunct mean_node" into every chart the engine had ever produced.
"""

from __future__ import annotations

import dataclasses
import os
import unittest

from gbc_astro import AstrologyEngine
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.defaults import RELATIONSHIP_WESTERN_V1, WESTERN_MODERN_V1
from gbc_astro.profiles.model import AspectProfile, AspectRule
from gbc_astro.providers.swiss import SwissEphemerisProvider

CHART_A = ("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
CHART_B = ("1988-02-14T09:20:00", "Europe/Paris", 48.8566, 2.3522)

NODES = {"true_node", "mean_node"}


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    return bool(path and os.path.exists(os.path.join(path, "sepl_18.se1")))


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class OneLunarNodeTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.chart_a = self.engine.natal(*CHART_A)
        self.chart_b = self.engine.natal(*CHART_B)

    def test_both_nodes_are_still_reported_as_bodies(self) -> None:
        """The fix removes them from aspecting, not from the chart."""
        for node in NODES:
            with self.subTest(node=node):
                self.assertIn(node, self.chart_a.bodies)

    def test_no_natal_aspect_joins_the_two_nodes(self) -> None:
        """It was in every chart, always true, and said nothing."""
        for aspect in self.chart_a.aspects:
            with self.subTest(aspect=aspect.aspect_type):
                self.assertNotEqual({aspect.body_a, aspect.body_b}, NODES)

    def test_only_one_node_aspects_at_all(self) -> None:
        for chart in (self.chart_a, self.chart_b):
            nodes_seen = {
                body
                for aspect in chart.aspects
                for body in (aspect.body_a, aspect.body_b)
                if body in NODES
            }
            with self.subTest(chart=chart.subject.utc_datetime):
                self.assertLessEqual(len(nodes_seen), 1)

    def test_a_node_contact_is_never_reported_twice_in_synastry(self) -> None:
        """Nine of eleven node contacts used to be the same contact twice."""
        synastry = self.engine.synastry(self.chart_a, self.chart_b)
        collapsed = [
            (
                aspect.body_a.replace("mean_node", "true_node"),
                aspect.body_b.replace("mean_node", "true_node"),
                aspect.aspect_type,
            )
            for aspect in synastry.cross_aspects
        ]
        self.assertEqual(len(collapsed), len(set(collapsed)))

    def test_a_node_falls_into_one_house_not_two(self) -> None:
        synastry = self.engine.synastry(self.chart_a, self.chart_b)
        node_overlays = [
            overlay
            for overlay in synastry.a_bodies_in_b_houses
            if overlay.body in NODES
        ]
        self.assertEqual(len(node_overlays), 1)

    def test_a_profile_admitting_both_nodes_is_refused(self) -> None:
        """Enforced structurally, because the defaults are not the only profiles."""
        profile = dataclasses.replace(
            WESTERN_MODERN_V1,
            aspect_bodies=WESTERN_MODERN_V1.aspect_bodies + ("mean_node",),
        )
        with self.assertRaises(InvalidCalculationProfileError) as raised:
            AstrologyEngine(profile=profile)
        self.assertIn("one lunar node", str(raised.exception))


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class EvidenceIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.chart_a = self.engine.natal(*CHART_A)
        self.chart_b = self.engine.natal(*CHART_B)
        self.synastry = self.engine.synastry(self.chart_a, self.chart_b)

    def _all_ids(self, synastry: object) -> list[str]:
        result = synastry  # type: ignore[assignment]
        return (
            [aspect.id for aspect in result.cross_aspects]  # type: ignore[attr-defined]
            + [angle.id for angle in result.angle_interactions]  # type: ignore[attr-defined]
            + [o.id for o in result.a_bodies_in_b_houses]  # type: ignore[attr-defined]
            + [o.id for o in result.b_bodies_in_a_houses]  # type: ignore[attr-defined]
        )

    def test_every_fact_has_a_unique_id(self) -> None:
        ids = self._all_ids(self.synastry)
        self.assertTrue(ids)
        self.assertEqual(len(ids), len(set(ids)))

    def test_ids_are_stable_across_runs(self) -> None:
        again = self.engine.synastry(self.chart_a, self.chart_b)
        self.assertEqual(self._all_ids(self.synastry), self._all_ids(again))

    def test_direction_is_part_of_the_identity(self) -> None:
        """A's Sun on B's Moon is not B's Sun on A's Moon.

        Two different facts about two different people. An id that collapsed
        them would make a stored reference ambiguous about whose planet it is.
        """
        swapped = self.engine.synastry(self.chart_b, self.chart_a)
        self.assertNotEqual(
            set(self._all_ids(self.synastry)), set(self._all_ids(swapped))
        )

    def test_an_overlay_id_names_both_charts(self) -> None:
        overlay = self.synastry.a_bodies_in_b_houses[0]
        self.assertTrue(overlay.id.startswith("synastry.overlay.a."))
        self.assertIn(".in.b.house_", overlay.id)

    def test_an_id_does_not_change_when_only_the_orb_profile_does(self) -> None:
        """The point of keeping orbs out of the id.

        A profile revision changes which contacts exist. It must not rename the
        ones that survive, or every stored score citing them breaks.
        """
        wider = dataclasses.replace(
            RELATIONSHIP_WESTERN_V1,
            version="9.9.9",
            synastry_aspect_profile=AspectProfile(
                id="wider-for-test",
                version="9.9.9",
                rules=(
                    AspectRule("conjunction", 0.0, 9.0),
                    AspectRule("sextile", 60.0, 6.0),
                    AspectRule("square", 90.0, 8.0),
                    AspectRule("trine", 120.0, 8.0),
                    AspectRule("opposition", 180.0, 9.0),
                ),
            ),
        )
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        loose_engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
            relationship_profile=wider,
        )
        loose = loose_engine.synastry(self.chart_a, self.chart_b)

        tight_ids = {aspect.id for aspect in self.synastry.cross_aspects}
        loose_ids = {aspect.id for aspect in loose.cross_aspects}
        self.assertGreater(len(loose_ids), len(tight_ids))
        self.assertTrue(tight_ids.issubset(loose_ids))

    def test_ids_carry_no_display_prose(self) -> None:
        for identifier in self._all_ids(self.synastry):
            with self.subTest(id=identifier):
                self.assertEqual(identifier, identifier.lower())
                self.assertNotIn(" ", identifier)


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class SynastryAspectProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )

    def test_cross_aspects_and_composite_use_different_profiles(self) -> None:
        """A composite chart is a chart, and is read with natal orbs."""
        profile = self.engine.relationship_profile
        self.assertEqual(profile.synastry_aspect_profile.id, "synastry-major-v1")
        self.assertEqual(profile.aspect_profile.id, "modern-major-v1")

    def test_the_result_publishes_which_profile_produced_the_contacts(self) -> None:
        chart_a = self.engine.natal(*CHART_A)
        chart_b = self.engine.natal(*CHART_B)
        meta = self.engine.synastry(chart_a, chart_b).meta.to_dict()
        self.assertEqual(meta["aspectProfile"], "synastry-major-v1")
