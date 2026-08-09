"""Evidence contexts and the report outline.

Neither produces prose and neither calls a model. Both select and order facts
that already exist, so the tests are about three properties:

**Every identifier resolves.** A context or an outline citing something that is
not in the result is worse than one citing nothing, because a consumer has no
way to tell.

**Bounded, and honest that it is bounded.** An unbounded context is how a prompt
ends up carrying four hundred contacts and a model ends up asserting whichever
of them it noticed. The cap is part of the contract, and `availableCount` says
what was left behind.

**An empty section is still a section.** A pair with no birth times has no house
overlays; dropping the section would read as a topic that did not apply rather
than one the geometry could not answer.
"""

from __future__ import annotations

import os
import unittest

from gbc_astro import AstrologyEngine
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.report import COUPLE_REPORT_V1, TOPIC_IDS
from gbc_astro.providers.swiss import SwissEphemerisProvider

CHART_A = ("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
CHART_B = ("1988-02-14T09:20:00", "Europe/Paris", 48.8566, 2.3522)
UNKNOWN_A = ("1992-11-03", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
UNKNOWN_B = ("1988-02-14", "Europe/Paris", 48.8566, 2.3522)


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    return bool(path and os.path.exists(os.path.join(path, "sepl_18.se1")))


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class EvidenceContextTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.chart_a = self.engine.natal(*CHART_A)
        self.chart_b = self.engine.natal(*CHART_B)
        self.synastry = self.engine.synastry(self.chart_a, self.chart_b)

    def _known_ids(self) -> set[str]:
        return (
            {a.id for a in self.synastry.cross_aspects}
            | {a.id for a in self.synastry.angle_interactions}
            | {o.id for o in self.synastry.a_bodies_in_b_houses}
            | {o.id for o in self.synastry.b_bodies_in_a_houses}
            | {p.id for p in self.synastry.patterns}
            | {p.id for p in self.synastry.point_contacts}
        )

    def test_every_topic_produces_a_context_that_resolves(self) -> None:
        known = self._known_ids()
        for topic in TOPIC_IDS:
            context = self.engine.evidence_context(self.chart_a, self.chart_b, topic)
            with self.subTest(topic=topic):
                self.assertEqual(context.topic, topic)
                for evidence_id in context.evidence_ids:
                    self.assertIn(evidence_id, known)

    def test_a_context_never_exceeds_the_declared_cap(self) -> None:
        for topic in TOPIC_IDS:
            context = self.engine.evidence_context(self.chart_a, self.chart_b, topic)
            with self.subTest(topic=topic):
                self.assertLessEqual(
                    len(context.evidence_ids), COUPLE_REPORT_V1.maximum_evidence
                )

    def test_truncation_is_reported_rather_than_hidden(self) -> None:
        """The top of a list must not be mistakable for the whole of one."""
        context = self.engine.evidence_context(self.chart_a, self.chart_b, "overall")
        self.assertTrue(context.truncated)
        self.assertGreater(context.available_count, len(context.evidence_ids))

        narrow = self.engine.evidence_context(
            self.chart_a, self.chart_b, "communication"
        )
        self.assertFalse(narrow.truncated)
        self.assertEqual(narrow.available_count, len(narrow.evidence_ids))

    def test_a_dimension_topic_selects_only_what_speaks_to_it(self) -> None:
        """A communication context citing every scored contact would be citing
        the whole chart and calling it communication."""
        score = self.engine.compatibility(self.chart_a, self.chart_b)
        relevant = {
            c.evidence_id for c in score.contributions if "communication" in c.dimension_values
        }
        context = self.engine.evidence_context(
            self.chart_a, self.chart_b, "communication"
        )
        self.assertTrue(context.evidence_ids)
        self.assertLessEqual(set(context.evidence_ids), relevant)

    def test_the_context_carries_every_profile_that_shaped_it(self) -> None:
        context = self.engine.evidence_context(self.chart_a, self.chart_b, "overall")
        for key in (
            "engineVersion",
            "scoringProfileVersion",
            "dimensionProfileVersion",
            "relationshipTypeVersion",
            "reportProfileVersion",
            "synastrySchemaVersion",
        ):
            with self.subTest(key=key):
                self.assertIn(key, context.provenance)

    def test_the_context_follows_the_relationship_type(self) -> None:
        work = self.engine.evidence_context(
            self.chart_a, self.chart_b, "attraction", "work"
        )
        romantic = self.engine.evidence_context(
            self.chart_a, self.chart_b, "attraction", "romantic"
        )
        self.assertEqual(work.provenance["relationshipType"], "work-v1")
        self.assertEqual(romantic.provenance["relationshipType"], "romantic-v1")

    def test_selection_is_deterministic(self) -> None:
        first = self.engine.evidence_context(self.chart_a, self.chart_b, "overall")
        second = self.engine.evidence_context(self.chart_a, self.chart_b, "overall")
        self.assertEqual(first.evidence_ids, second.evidence_ids)

    def test_an_unknown_topic_is_refused(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError):
            self.engine.evidence_context(self.chart_a, self.chart_b, "vibes")


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class ReportOutlineTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.chart_a = self.engine.natal(*CHART_A)
        self.chart_b = self.engine.natal(*CHART_B)
        self.outline = self.engine.report_outline(self.chart_a, self.chart_b)

    def test_sections_come_back_in_priority_order(self) -> None:
        priorities = [section.priority for section in self.outline.sections]
        self.assertEqual(priorities, sorted(priorities))
        self.assertEqual(len(self.outline.sections), len(COUPLE_REPORT_V1.sections))

    def test_no_section_carries_prose(self) -> None:
        """The core supplies identifiers; the words belong to the renderer."""
        for section in self.outline.sections:
            with self.subTest(section=section.section_id):
                self.assertEqual(section.section_id, section.section_id.lower())
                self.assertNotIn(" ", section.section_id)

    def test_every_section_is_capped_and_says_so(self) -> None:
        for section in self.outline.sections:
            with self.subTest(section=section.section_id):
                self.assertLessEqual(
                    len(section.evidence_ids), COUPLE_REPORT_V1.maximum_evidence
                )
                self.assertGreaterEqual(
                    section.available_count, len(section.evidence_ids)
                )
                self.assertEqual(
                    section.truncated,
                    section.available_count > len(section.evidence_ids),
                )

    def test_a_dimension_section_cites_only_its_own_dimension(self) -> None:
        score = self.engine.compatibility(self.chart_a, self.chart_b)
        section = next(
            s for s in self.outline.sections if s.section_id == "communication"
        )
        relevant = {
            c.evidence_id
            for c in score.contributions
            if "communication" in c.dimension_values
        }
        self.assertTrue(section.evidence_ids)
        self.assertLessEqual(set(section.evidence_ids), relevant)

    def test_every_section_is_available_for_a_full_pair(self) -> None:
        for section in self.outline.sections:
            with self.subTest(section=section.section_id):
                self.assertTrue(section.available)
                self.assertIsNone(section.unavailable_reason)

    def test_an_empty_section_is_kept_and_explained(self) -> None:
        """Dropping it would read as a topic that did not apply."""
        outline = self.engine.report_outline(
            self.engine.natal(*UNKNOWN_A, unknown_time=True),
            self.engine.natal(*UNKNOWN_B, unknown_time=True),
        )
        self.assertEqual(len(outline.sections), len(COUPLE_REPORT_V1.sections))
        unavailable = [s for s in outline.sections if not s.available]
        self.assertTrue(unavailable)
        for section in unavailable:
            with self.subTest(section=section.section_id):
                self.assertTrue(section.unavailable_reason)
                self.assertEqual(section.evidence_ids, ())

    def test_a_reason_is_not_repeated_within_one_section(self) -> None:
        """Both overlay directions share a reason; saying it twice reads as two
        separate problems."""
        outline = self.engine.report_outline(
            self.engine.natal(*UNKNOWN_A, unknown_time=True),
            self.engine.natal(*UNKNOWN_B, unknown_time=True),
        )
        section = next(s for s in outline.sections if s.section_id == "house_overlays")
        assert section.unavailable_reason is not None
        parts = section.unavailable_reason.split("; ")
        self.assertEqual(len(parts), len(set(parts)))

    def test_the_outline_is_deterministic(self) -> None:
        again = self.engine.report_outline(self.chart_a, self.chart_b)
        self.assertEqual(again.to_dict(), self.outline.to_dict())
