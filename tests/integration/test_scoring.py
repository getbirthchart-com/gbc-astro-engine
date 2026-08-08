"""Relationship scoring tests.

A score has no independent reference to check it against -- the weights are an
opinion, not a measurement -- so these tests check the things that *can* be
wrong regardless of opinion: that the arithmetic matches the published
breakdown, that no geometric fact is counted twice, that the result does not
depend on argument order, and that the profile is actually consulted.
"""

from __future__ import annotations

import json
import os
import unittest
from collections import Counter
from dataclasses import replace

from gbc_astro import AstrologyEngine
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.scoring import SYNASTRY_SCORING_V1
from gbc_astro.providers.swiss import SwissEphemerisProvider
from gbc_astro.relationship.scoring import orb_factor


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


class OrbFactorTests(unittest.TestCase):
    def test_exact_contact_scores_at_full_weight(self) -> None:
        self.assertAlmostEqual(orb_factor(0.0, 8.0, 0.3), 1.0, places=9)

    def test_edge_of_orb_scores_at_the_floor(self) -> None:
        self.assertAlmostEqual(orb_factor(8.0, 8.0, 0.3), 0.3, places=9)

    def test_falls_off_monotonically(self) -> None:
        values = [orb_factor(orb, 8.0, 0.3) for orb in (0.0, 2.0, 4.0, 6.0, 8.0)]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_never_leaves_the_declared_range(self) -> None:
        for orb in (0.0, 1.0, 8.0, 20.0):
            with self.subTest(orb=orb):
                value = orb_factor(orb, 8.0, 0.3)
                self.assertGreaterEqual(value, 0.3)
                self.assertLessEqual(value, 1.0)


@unittest.skipUnless(_swiss_available(), "Scoring needs Swiss Ephemeris data")
class RelationshipScoreTests(unittest.TestCase):
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

    def test_totals_are_exactly_the_sum_of_the_published_breakdown(self) -> None:
        """The headline numbers must be reproducible from the lines shown."""
        score = self.engine.compatibility(self.chart_a, self.chart_b)
        positive = sum(item.value for item in score.contributions if item.value > 0)
        negative = sum(item.value for item in score.contributions if item.value < 0)

        self.assertAlmostEqual(score.supportive, positive, places=9)
        self.assertAlmostEqual(score.challenging, negative, places=9)
        self.assertAlmostEqual(score.activity, positive - negative, places=9)
        self.assertAlmostEqual(score.balance, positive + negative, places=9)
        self.assertEqual(score.contribution_count, len(score.contributions))

    def test_each_contribution_is_its_three_factors_multiplied(self) -> None:
        score = self.engine.compatibility(self.chart_a, self.chart_b)
        for item in score.contributions:
            with self.subTest(a=item.subject_a, b=item.subject_b):
                self.assertAlmostEqual(
                    item.value,
                    item.aspect_weight * item.pair_weight * item.orb_factor,
                    places=9,
                )

    def test_no_percentage_is_produced(self) -> None:
        """A percentage would imply an absolute scale that does not exist."""
        payload = self.engine.compatibility(self.chart_a, self.chart_b).to_dict()
        self.assertNotIn("percent", payload["totals"])
        self.assertNotIn("percentage", payload["totals"])
        self.assertEqual(
            set(payload["totals"]),
            {
                "supportive",
                "challenging",
                "activity",
                "balance",
                "activityBand",
                "balanceBand",
            },
        )

    def test_each_angle_axis_is_scored_only_once(self) -> None:
        """The Descendant mirrors the Ascendant: one geometric fact, one line."""
        score = self.engine.compatibility(self.chart_a, self.chart_b)
        axis_of = SYNASTRY_SCORING_V1.angle_axis_of

        seen = Counter(
            (item.subject_a, axis_of[item.subject_b.split(".", 1)[1]])
            for item in score.contributions
            if item.kind == "angle_interaction"
        )
        self.assertTrue(seen)
        self.assertEqual([count for count in seen.values() if count > 1], [])

    def test_a_conjunction_to_the_descendant_survives_as_a_conjunction(self) -> None:
        """Not collapsed into an opposition to the Ascendant, which would flip its sign."""
        score = self.engine.compatibility(self.chart_a, self.chart_b)
        descendant_conjunctions = [
            item
            for item in score.contributions
            if item.subject_b.endswith(".descendant") and item.aspect_type == "conjunction"
        ]
        self.assertTrue(descendant_conjunctions)
        for item in descendant_conjunctions:
            self.assertGreater(item.value, 0.0)

    def test_score_does_not_depend_on_argument_order(self) -> None:
        forward = self.engine.compatibility(self.chart_a, self.chart_b)
        backward = self.engine.compatibility(self.chart_b, self.chart_a)

        self.assertAlmostEqual(forward.activity, backward.activity, places=9)
        self.assertAlmostEqual(forward.balance, backward.balance, places=9)
        self.assertEqual(forward.contribution_count, backward.contribution_count)

    def test_scoring_is_deterministic(self) -> None:
        self.assertEqual(
            self.engine.compatibility(self.chart_a, self.chart_b).to_json(),
            self.engine.compatibility(self.chart_a, self.chart_b).to_json(),
        )

    def test_a_chart_against_itself_is_strongly_supportive(self) -> None:
        """Every body exactly conjunct its counterpart: no hard cross aspects at all."""
        score = self.engine.compatibility(self.chart_a, self.chart_a)
        same_body = [
            item
            for item in score.contributions
            if item.kind == "cross_aspect"
            and item.subject_a[2:] == item.subject_b[2:]
        ]
        self.assertTrue(same_body)
        for item in same_body:
            self.assertEqual(item.aspect_type, "conjunction")
            self.assertAlmostEqual(item.orb_factor, 1.0, places=9)
        self.assertGreater(score.balance, 0.0)

    def test_the_profile_is_actually_consulted(self) -> None:
        """Change an opinion, change the score: the weights are not decorative."""
        louder = replace(
            SYNASTRY_SCORING_V1,
            id="test-doubled",
            version="0.0.0",
            aspect_weights={
                key: value * 2.0 for key, value in SYNASTRY_SCORING_V1.aspect_weights.items()
            },
        )
        engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=os.environ["GBC_SWISS_EPHE_PATH"]),
            house_calculator=SwissHouseCalculator(
                ephemeris_path=os.environ["GBC_SWISS_EPHE_PATH"]
            ),
            scoring_profile=louder,
        )
        base = self.engine.compatibility(self.chart_a, self.chart_b)
        doubled = engine.compatibility(self.chart_a, self.chart_b)

        self.assertAlmostEqual(doubled.activity, base.activity * 2.0, places=8)
        self.assertEqual(doubled.scoring_profile, "test-doubled")

    def test_the_result_carries_the_whole_profile_and_its_caveats(self) -> None:
        """A score must always be traceable to the opinion that produced it."""
        score = self.engine.compatibility(self.chart_a, self.chart_b)
        payload = json.loads(score.to_json())

        self.assertEqual(payload["meta"]["scoringProfile"], "synastry-scoring-v1")
        self.assertEqual(payload["meta"]["scoringProfileVersion"], "1.0.0")
        self.assertIn("aspectWeights", payload["profile"])
        self.assertIn("bodyWeights", payload["profile"])
        self.assertIn("editorial opinion", payload["profile"]["rationale"])
        self.assertIn("cafeastrology.com", payload["profile"]["sourceNote"])
        self.assertTrue(any("no independent reference" in note for note in payload["notes"]))

    def test_bands_are_profile_declared_not_universal(self) -> None:
        score = self.engine.compatibility(self.chart_a, self.chart_b)
        labels = {band["label"] for band in score.profile_detail["activityBands"]}
        self.assertIn(score.activity_band, labels)
