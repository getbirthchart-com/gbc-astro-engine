"""Named configurations between two charts.

Two properties matter more than the individual detections.

**Citations resolve, and only one family may cite nothing.** A stellium is
defined by sign sharing rather than by an aspect, so four bodies can occupy one
sign with no conjunction between the two charts inside the orb. Every other
family is built from contacts and must cite them.

**Nothing here is scored.** Each contact behind a pattern is already scored once
as itself, and scoring the pattern as well would count the same geometry a
second time for having been noticed -- the shape this codebase has removed three
times already.
"""

from __future__ import annotations

import os
import random
import statistics
import unittest

from gbc_astro import AstrologyEngine
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.relationship_patterns import RELATIONSHIP_PATTERNS_V1
from gbc_astro.providers.swiss import SwissEphemerisProvider

CHART_A = ("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
CHART_B = ("1988-02-14T09:20:00", "Europe/Paris", 48.8566, 2.3522)


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    return bool(path and os.path.exists(os.path.join(path, "sepl_18.se1")))


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class RelationshipPatternTests(unittest.TestCase):
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
        return {a.id for a in self.synastry.cross_aspects} | {
            a.id for a in self.synastry.angle_interactions
        }

    def test_every_citation_resolves(self) -> None:
        facts = self._facts()
        self.assertTrue(self.synastry.patterns)
        for pattern in self.synastry.patterns:
            for evidence_id in pattern.evidence_ids:
                with self.subTest(pattern=pattern.id, id=evidence_id):
                    self.assertIn(evidence_id, facts)

    def test_only_a_stellium_may_cite_nothing(self) -> None:
        """Sign sharing is not an aspect, so there may be no contact to cite."""
        for pattern in self.synastry.patterns:
            if pattern.evidence_ids:
                continue
            with self.subTest(pattern=pattern.id):
                self.assertEqual(pattern.pattern_type, "cross_stellium")

    def test_no_pattern_is_scored(self) -> None:
        score = self.engine.compatibility(self.chart_a, self.chart_b)
        for contribution in score.contributions:
            with self.subTest(evidence=contribution.evidence_id):
                self.assertNotIn(".pattern.", contribution.evidence_id)
        for pattern in self.synastry.patterns:
            self.assertFalse(pattern.scored)

    def test_no_configuration_lies_entirely_within_one_chart(self) -> None:
        """That would be a natal pattern, already reported on that chart."""
        for pattern in self.synastry.patterns:
            if not pattern.pattern_type.startswith("cross_"):
                continue
            owners = {member.split(".", 1)[0] for member in pattern.members}
            with self.subTest(pattern=pattern.id):
                self.assertEqual(owners, {"A", "B"})

    def test_cross_yods_are_excluded_and_the_profile_says_so(self) -> None:
        """Their defining legs are quincunxes, which synastry does not recognise."""
        self.assertIn("yod", RELATIONSHIP_PATTERNS_V1.excluded_cross_configurations)
        for pattern in self.synastry.patterns:
            self.assertNotEqual(pattern.pattern_type, "cross_yod")

    def test_ids_are_unique_and_stable(self) -> None:
        ids = [pattern.id for pattern in self.synastry.patterns]
        self.assertEqual(len(ids), len(set(ids)))
        again = self.engine.synastry(self.chart_a, self.chart_b)
        self.assertEqual([p.id for p in again.patterns], ids)

    def test_mutual_activation_names_a_reciprocal_pair_once(self) -> None:
        """A.venus on B.mars *and* B.venus on A.mars is one structure, not two."""
        for pattern in self.synastry.patterns:
            if pattern.pattern_type != "mutual_activation":
                continue
            first, second = pattern.members
            with self.subTest(pattern=pattern.id):
                self.assertLess(first, second)
                self.assertGreaterEqual(len(pattern.evidence_ids), 2)

    def test_the_luminaries_are_never_reported_as_emphasised(self) -> None:
        """They reach any workable threshold in nearly every pair."""
        for pattern in self.synastry.patterns:
            if pattern.pattern_type == "body_emphasis":
                with self.subTest(pattern=pattern.id):
                    self.assertNotIn(pattern.members[0], ("sun", "moon"))

    def test_emphasis_requires_the_declared_number_of_contacts(self) -> None:
        for pattern in self.synastry.patterns:
            if pattern.pattern_type != "body_emphasis":
                continue
            with self.subTest(pattern=pattern.id):
                self.assertGreaterEqual(
                    len(pattern.evidence_ids),
                    RELATIONSHIP_PATTERNS_V1.emphasis_minimum_contacts,
                )

    def test_the_output_stays_readable_across_random_pairs(self) -> None:
        """A list of thirty notable patterns is not a list of notable patterns.

        The thresholds were measured to bring this down from 29.4 per pair.
        """
        random.seed(13)
        charts = []
        for _ in range(20):
            stamp = f"{random.randint(1950, 2005):04d}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}T{random.randint(0, 23):02d}:{random.randint(0, 59):02d}:00"
            charts.append(
                self.engine.natal(
                    stamp, "UTC", random.uniform(-45, 55), random.uniform(-170, 170)
                )
            )
        counts = [
            len(self.engine.synastry(charts[i], charts[i + 10]).patterns)
            for i in range(10)
        ]
        self.assertLess(statistics.mean(counts), 20.0)
