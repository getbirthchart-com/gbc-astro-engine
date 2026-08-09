"""Dimension scores, and the evidence rule that holds them up.

The roadmap's rule is that no derived score may exist without decomposable
contributing signals, and that every signal must cite canonical evidence. That
is only worth anything if the citations resolve, so the first test here checks
that every evidence id a score references is a fact the synastry result actually
contains.

The other thing pinned here is the difference between silent and neutral. A
dimension with no contacts is not a zero, and an unknown birth time makes a pair
silent about everything the angles would have said. `contactCount` is what keeps
those apart, and nothing may quietly turn an absence into evidence.
"""

from __future__ import annotations

import math
import os
import unittest

from gbc_astro import AstrologyEngine
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.dimensions import (
    DIMENSION_IDS,
    SYNASTRY_DIMENSION_PROFILE_V1,
)
from gbc_astro.providers.swiss import SwissEphemerisProvider

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
class EvidenceRuleTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.chart_a = self.engine.natal(*CHART_A)
        self.chart_b = self.engine.natal(*CHART_B)
        self.synastry = self.engine.synastry(self.chart_a, self.chart_b)
        self.score = self.engine.compatibility(self.chart_a, self.chart_b)

    def _known_facts(self) -> set[str]:
        return (
            {aspect.id for aspect in self.synastry.cross_aspects}
            | {angle.id for angle in self.synastry.angle_interactions}
            | {o.id for o in self.synastry.a_bodies_in_b_houses}
            | {o.id for o in self.synastry.b_bodies_in_a_houses}
        )

    def test_every_contribution_cites_a_fact_that_exists(self) -> None:
        """A citation that does not resolve is worse than no citation."""
        facts = self._known_facts()
        self.assertTrue(self.score.contributions)
        for contribution in self.score.contributions:
            with self.subTest(evidence=contribution.evidence_id):
                self.assertIn(contribution.evidence_id, facts)

    def test_every_dimension_evidence_id_exists(self) -> None:
        facts = self._known_facts()
        for dimension in self.score.dimensions:
            for evidence_id in dimension.evidence_ids:
                with self.subTest(dimension=dimension.dimension, id=evidence_id):
                    self.assertIn(evidence_id, facts)

    def test_no_contribution_is_cited_twice_in_one_dimension(self) -> None:
        for dimension in self.score.dimensions:
            with self.subTest(dimension=dimension.dimension):
                self.assertEqual(
                    len(dimension.evidence_ids), len(set(dimension.evidence_ids))
                )

    def test_the_totals_are_exactly_the_sum_of_the_contributions(self) -> None:
        """The score must be reconstructable, not merely accompanied by detail."""
        supportive = sum(c.value for c in self.score.contributions if c.value > 0.0)
        challenging = sum(c.value for c in self.score.contributions if c.value < 0.0)
        self.assertAlmostEqual(self.score.supportive, supportive, places=9)
        self.assertAlmostEqual(self.score.challenging, challenging, places=9)
        self.assertAlmostEqual(self.score.activity, supportive - challenging, places=9)

    def test_each_dimension_is_the_sum_of_its_own_contributions(self) -> None:
        for dimension in self.score.dimensions:
            values = [
                c.dimension_values[dimension.dimension]
                for c in self.score.contributions
                if dimension.dimension in c.dimension_values
            ]
            with self.subTest(dimension=dimension.dimension):
                self.assertAlmostEqual(
                    dimension.supportive, sum(v for v in values if v > 0.0), places=9
                )
                self.assertAlmostEqual(
                    dimension.challenging, sum(v for v in values if v < 0.0), places=9
                )
                self.assertEqual(dimension.contact_count, len(values))


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class DimensionShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.chart_a = self.engine.natal(*CHART_A)
        self.chart_b = self.engine.natal(*CHART_B)
        self.score = self.engine.compatibility(self.chart_a, self.chart_b)

    def test_every_dimension_is_returned_even_with_no_contacts(self) -> None:
        """Omitting an empty dimension would hide the difference from a zero."""
        self.assertEqual(
            tuple(d.dimension for d in self.score.dimensions), DIMENSION_IDS
        )

    def test_no_score_is_nan_or_infinite(self) -> None:
        numbers = [self.score.supportive, self.score.challenging, self.score.activity]
        for dimension in self.score.dimensions:
            numbers += [dimension.supportive, dimension.challenging, dimension.activity]
        for value in numbers:
            with self.subTest(value=value):
                self.assertTrue(math.isfinite(value))

    def test_supportive_and_challenging_are_never_netted(self) -> None:
        """A pair with strong attraction and strong friction is not a pair with
        neither, and a single net figure cannot tell them apart."""
        for dimension in self.score.dimensions:
            with self.subTest(dimension=dimension.dimension):
                self.assertGreaterEqual(dimension.supportive, 0.0)
                self.assertLessEqual(dimension.challenging, 0.0)

    def test_the_aspect_decides_the_sign_not_the_dimension(self) -> None:
        """A Mercury square is still about communication.

        The profile maps bodies to dimensions; it never moves a contact to a
        different dimension because the aspect was hard.
        """
        squares = [
            c
            for c in self.score.contributions
            if c.aspect_type == "square" and "mercury" in (c.subject_a + c.subject_b)
        ]
        self.assertTrue(squares)
        for contribution in squares:
            with self.subTest(evidence=contribution.evidence_id):
                self.assertIn("communication", contribution.dimension_values)

    def test_hard_aspects_add_friction_to_conflict(self) -> None:
        for contribution in self.score.contributions:
            if contribution.aspect_type not in ("square", "opposition"):
                continue
            with self.subTest(evidence=contribution.evidence_id):
                self.assertLess(contribution.dimension_values.get("conflict", 0.0), 0.0)

    def test_an_unmapped_body_introduces_no_dimension_of_its_own(self) -> None:
        """The node and Chiron are unmapped, which is not the same as silencing.

        A contact still scores in whatever dimensions its other end speaks to --
        Mars trine the node is about drive, just less squarely than Mars trine
        Venus. What an unmapped body must never do is bring a dimension with it.
        """
        profile = SYNASTRY_DIMENSION_PROFILE_V1
        unmapped = {"true_node", "chiron"}
        checked = 0
        for contribution in self.score.contributions:
            ends = {
                contribution.subject_a.split(".", 1)[1],
                contribution.subject_b.split(".", 1)[1],
            }
            if not ends & unmapped:
                continue
            checked += 1
            partner_dimensions = set()
            for end in ends - unmapped:
                partner_dimensions |= set(profile.weights_for(end))
            if contribution.aspect_type in profile.conflict_aspects:
                partner_dimensions.add("conflict")
            with self.subTest(evidence=contribution.evidence_id):
                self.assertLessEqual(
                    set(contribution.dimension_values), partner_dimensions
                )
        self.assertGreater(checked, 0)

    def test_a_contact_between_two_unmapped_bodies_scores_no_dimension(self) -> None:
        """Except conflict, which the aspect contributes rather than the bodies."""
        for contribution in self.score.contributions:
            ends = {
                contribution.subject_a.split(".", 1)[1],
                contribution.subject_b.split(".", 1)[1],
            }
            if not ends <= {"true_node", "chiron"}:
                continue
            with self.subTest(evidence=contribution.evidence_id):
                self.assertLessEqual(set(contribution.dimension_values), {"conflict"})

    def test_the_profile_that_produced_the_split_is_published(self) -> None:
        payload = self.score.to_dict()
        self.assertEqual(
            payload["meta"]["dimensionProfile"], SYNASTRY_DIMENSION_PROFILE_V1.id
        )
        self.assertEqual(
            payload["meta"]["dimensionProfileVersion"],
            SYNASTRY_DIMENSION_PROFILE_V1.version,
        )
        self.assertIn("bodyDimensions", payload["dimensionProfile"])

    def test_scoring_is_deterministic(self) -> None:
        again = self.engine.compatibility(self.chart_a, self.chart_b)
        self.assertEqual(again.to_dict(), self.score.to_dict())


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class MissingDataTests(unittest.TestCase):
    """Silent is not neutral, and an unknown birth time is silent."""

    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.chart_a = self.engine.natal(*CHART_A)
        self.known = self.engine.compatibility(
            self.chart_a, self.engine.natal(*CHART_B)
        )
        self.sparse = self.engine.compatibility(
            self.chart_a, self.engine.natal(*UNKNOWN_B, unknown_time=True)
        )

    def test_an_unknown_birth_time_lowers_coverage_not_the_dimension_list(
        self,
    ) -> None:
        self.assertEqual(
            tuple(d.dimension for d in self.sparse.dimensions), DIMENSION_IDS
        )
        known_contacts = sum(d.contact_count for d in self.known.dimensions)
        sparse_contacts = sum(d.contact_count for d in self.sparse.dimensions)
        self.assertLess(sparse_contacts, known_contacts)

    def test_no_angle_contact_is_invented_for_the_unknown_chart(self) -> None:
        for contribution in self.sparse.contributions:
            with self.subTest(evidence=contribution.evidence_id):
                self.assertNotIn(".b.ascendant", contribution.evidence_id)
                self.assertNotIn(".b.mc", contribution.evidence_id)

    def test_missing_evidence_is_absent_rather_than_scored_as_zero(self) -> None:
        """No zero-valued contribution is injected to stand in for what is gone."""
        for contribution in self.sparse.contributions:
            with self.subTest(evidence=contribution.evidence_id):
                self.assertNotEqual(contribution.value, 0.0)


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class RelationshipTypeTests(unittest.TestCase):
    """The type changes what counts, never what is true."""

    TYPES = ("general", "romantic", "friendship", "family", "work")

    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.chart_a = self.engine.natal(*CHART_A)
        self.chart_b = self.engine.natal(*CHART_B)
        self.scores = {
            name: self.engine.compatibility(self.chart_a, self.chart_b, name)
            for name in self.TYPES
        }

    def test_the_geometry_is_identical_under_every_type(self) -> None:
        """The absolute rule: relationship type reweights, it does not recalculate."""
        for name, score in self.scores.items():
            with self.subTest(relationship_type=name):
                self.assertEqual(
                    [c.evidence_id for c in score.contributions],
                    [c.evidence_id for c in self.scores["general"].contributions],
                )
                self.assertEqual(
                    [c.orb for c in score.contributions],
                    [c.orb for c in self.scores["general"].contributions],
                )
                self.assertAlmostEqual(
                    score.activity, self.scores["general"].activity, places=9
                )

    def test_each_type_produces_a_different_dimension_reading(self) -> None:
        readings = {
            name: tuple(round(d.activity, 6) for d in score.dimensions)
            for name, score in self.scores.items()
        }
        self.assertEqual(len(set(readings.values())), len(self.TYPES))

    def test_the_declared_intent_of_each_profile_holds(self) -> None:
        """Not just "different" -- different in the documented direction."""
        activity = {
            name: {d.dimension: d.activity for d in score.dimensions}
            for name, score in self.scores.items()
        }
        general = activity["general"]
        self.assertGreater(activity["romantic"]["attraction"], general["attraction"])
        self.assertGreater(activity["work"]["communication"], general["communication"])
        self.assertGreater(activity["work"]["stability"], general["stability"])
        self.assertGreater(activity["family"]["emotional"], general["emotional"])
        self.assertGreater(activity["friendship"]["growth"], general["growth"])
        # Attraction is demoted furthest for the two least romantic readings.
        self.assertLess(activity["work"]["attraction"], activity["friendship"]["attraction"])
        self.assertLess(activity["family"]["attraction"], activity["friendship"]["attraction"])

    def test_a_demoted_dimension_is_reduced_not_deleted(self) -> None:
        """Zeroing attraction would delete evidence rather than reweight it."""
        for name in ("friendship", "family", "work"):
            attraction = next(
                d for d in self.scores[name].dimensions if d.dimension == "attraction"
            )
            with self.subTest(relationship_type=name):
                self.assertGreater(attraction.contact_count, 0)
                self.assertNotEqual(attraction.activity, 0.0)

    def test_the_decomposition_still_holds_under_every_type(self) -> None:
        """Reweighting inside the contribution is what preserves this."""
        for name, score in self.scores.items():
            for dimension in score.dimensions:
                values = [
                    c.dimension_values[dimension.dimension]
                    for c in score.contributions
                    if dimension.dimension in c.dimension_values
                ]
                with self.subTest(relationship_type=name, dimension=dimension.dimension):
                    self.assertAlmostEqual(
                        dimension.supportive,
                        sum(v for v in values if v > 0.0),
                        places=9,
                    )

    def test_the_weight_actually_applied_is_published(self) -> None:
        for dimension in self.scores["work"].dimensions:
            if dimension.dimension != "attraction":
                continue
            self.assertAlmostEqual(dimension.profile_weight, 0.15, places=9)

    def test_omitting_the_type_is_neutral_rather_than_romantic(self) -> None:
        """Assuming romantic would answer a question the caller never asked."""
        unspecified = self.engine.compatibility(self.chart_a, self.chart_b)
        self.assertEqual(unspecified.relationship_type, "general-v1")
        self.assertEqual(
            unspecified.to_dict(), self.scores["general"].to_dict()
        )
        self.assertNotEqual(
            unspecified.to_dict()["dimensions"],
            self.scores["romantic"].to_dict()["dimensions"],
        )
        for dimension in unspecified.dimensions:
            with self.subTest(dimension=dimension.dimension):
                self.assertEqual(dimension.profile_weight, 1.0)

    def test_an_unknown_type_is_refused_rather_than_defaulted(self) -> None:
        from gbc_astro.errors import InvalidCalculationProfileError

        with self.assertRaises(InvalidCalculationProfileError):
            self.engine.compatibility(self.chart_a, self.chart_b, "situationship")
