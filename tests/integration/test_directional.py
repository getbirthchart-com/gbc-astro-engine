"""Ruler interactions and directional themes, both of which are views.

The one thing that would make either of these a defect is if they became a
second copy of geometry the result already has. "A's seventh-house ruler
conjunct B's Venus" is not a new contact -- if Mercury rules A's seventh, it is
the cross aspect already in the result and already scored. Emitting it again
with its own evidence id would put the same geometry into the scoring twice.

So the tests here are mostly about what these must *not* do: mint evidence,
change a score, or claim a direction the geometry does not have.
"""

from __future__ import annotations

import os
import unittest

from gbc_astro import AstrologyEngine
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.dimensions import DIMENSION_IDS
from gbc_astro.providers.swiss import SwissEphemerisProvider
from gbc_astro.relationship.directional import A_TO_B, B_TO_A

CHART_A = ("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
CHART_B = ("1988-02-14T09:20:00", "Europe/Paris", 48.8566, 2.3522)
UNKNOWN_B = ("1988-02-14", "Europe/Paris", 48.8566, 2.3522)


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    return bool(path and os.path.exists(os.path.join(path, "sepl_18.se1")))


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class ViewsCiteRatherThanMintTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.chart_a = self.engine.natal(*CHART_A)
        self.chart_b = self.engine.natal(*CHART_B)
        self.synastry = self.engine.synastry(self.chart_a, self.chart_b)

    def _facts(self) -> set[str]:
        return (
            {a.id for a in self.synastry.cross_aspects}
            | {a.id for a in self.synastry.angle_interactions}
            | {o.id for o in self.synastry.a_bodies_in_b_houses}
            | {o.id for o in self.synastry.b_bodies_in_a_houses}
        )

    def test_every_ruler_interaction_cites_a_fact_that_exists(self) -> None:
        facts = self._facts()
        self.assertTrue(self.synastry.ruler_interactions)
        for interaction in self.synastry.ruler_interactions:
            with self.subTest(ruler=interaction.id):
                self.assertIn(interaction.evidence_id, facts)

    def test_a_ruler_interaction_never_invents_geometry(self) -> None:
        """Its cited fact must carry the same aspect and orb it reports."""
        aspects = {a.id: a for a in self.synastry.cross_aspects}
        for interaction in self.synastry.ruler_interactions:
            if interaction.kind != "aspect":
                continue
            source = aspects[interaction.evidence_id]
            with self.subTest(ruler=interaction.id):
                self.assertEqual(interaction.aspect_type, source.aspect_type)
                self.assertAlmostEqual(interaction.orb or 0.0, source.orb, places=9)

    def test_every_directional_theme_cites_facts_that_exist(self) -> None:
        facts = self._facts()
        for theme in self.synastry.directional_themes:
            for evidence_id in theme.evidence_ids:
                with self.subTest(theme=theme.theme, id=evidence_id):
                    self.assertIn(evidence_id, facts)

    def test_ruler_interactions_add_nothing_to_the_score(self) -> None:
        """The whole reason they cite instead of minting."""
        score = self.engine.compatibility(self.chart_a, self.chart_b)
        cited = {i.evidence_id for i in self.synastry.ruler_interactions}
        scored = [c for c in score.contributions if c.evidence_id in cited]
        # Each cited fact is scored at most once, however many rulerships
        # happen to point at it.
        self.assertEqual(len({c.evidence_id for c in scored}), len(scored))

    def test_one_fact_may_be_reframed_by_several_rulerships(self) -> None:
        """A body ruling two houses reframes the same contact twice, by design."""
        seen: dict[str, int] = {}
        for interaction in self.synastry.ruler_interactions:
            seen[interaction.evidence_id] = seen.get(interaction.evidence_id, 0) + 1
        self.assertTrue(any(count > 1 for count in seen.values()))


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class DirectionTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.chart_a = self.engine.natal(*CHART_A)
        self.chart_b = self.engine.natal(*CHART_B)
        self.synastry = self.engine.synastry(self.chart_a, self.chart_b)

    def test_no_cross_aspect_is_grouped_as_directional(self) -> None:
        """An aspect is mutual. Grouping it by direction would assert one.

        This is the same refusal the engine already makes when it reports
        cross-aspect phase as indeterminate instead of borrowing natal speeds.
        """
        for theme in self.synastry.directional_themes:
            for evidence_id in theme.evidence_ids:
                with self.subTest(id=evidence_id):
                    self.assertNotIn(".cross.", evidence_id)

    def test_both_directions_carry_every_theme(self) -> None:
        pairs = {
            (theme.direction, theme.theme) for theme in self.synastry.directional_themes
        }
        self.assertEqual(
            pairs,
            {
                (direction, dimension)
                for direction in (A_TO_B, B_TO_A)
                for dimension in DIMENSION_IDS
            },
        )

    def test_the_two_directions_are_different_statements(self) -> None:
        forward = {
            t.theme: t.evidence_ids
            for t in self.synastry.directional_themes
            if t.direction == A_TO_B
        }
        backward = {
            t.theme: t.evidence_ids
            for t in self.synastry.directional_themes
            if t.direction == B_TO_A
        }
        self.assertNotEqual(forward, backward)
        for evidence in forward.values():
            for evidence_id in evidence:
                with self.subTest(id=evidence_id):
                    self.assertIn(".a.", evidence_id)

    def test_swapping_the_charts_swaps_the_directions(self) -> None:
        swapped = self.engine.synastry(self.chart_b, self.chart_a)
        original = {
            t.theme: t.contact_count
            for t in self.synastry.directional_themes
            if t.direction == A_TO_B
        }
        reversed_ = {
            t.theme: t.contact_count
            for t in swapped.directional_themes
            if t.direction == B_TO_A
        }
        self.assertEqual(original, reversed_)


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class UnknownTimeTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.chart_a = self.engine.natal(*CHART_A)
        self.unknown = self.engine.natal(*UNKNOWN_B, unknown_time=True)
        self.synastry = self.engine.synastry(self.chart_a, self.unknown)

    def test_a_chart_with_no_houses_has_no_house_rulers_to_send(self) -> None:
        """Nothing is substituted for the rulerships it does not have."""
        self.assertFalse(
            [i for i in self.synastry.ruler_interactions if i.direction == B_TO_A]
        )

    def test_the_known_chart_still_sends_its_rulers(self) -> None:
        """Asymmetry is the correct behaviour, not a degraded one."""
        self.assertTrue(
            [i for i in self.synastry.ruler_interactions if i.direction == A_TO_B]
        )

    def test_themes_survive_with_lower_coverage(self) -> None:
        self.assertEqual(len(self.synastry.directional_themes), len(DIMENSION_IDS) * 2)
