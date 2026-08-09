"""The relationship timing layer.

The failure this whole layer is exposed to is conflation. A transit to A, a
transit to B, a transit to the composite and a progressed contact are four
different claims about time, and a result that pools any of them cannot be read.
Most of what follows asserts that they stay apart.

The second concern is the one this codebase keeps meeting: activation must join
two existing facts, not mint a third. If it minted, the same geometry would be
counted twice under two names.
"""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone

from gbc_astro import AstrologyEngine
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.profiles.defaults import VEDIC_SIDEREAL_V1
from gbc_astro.profiles.relationship_timing import (
    COMPOSITE_FROM_PROGRESSED_CHARTS,
    PROGRESSED_DIRECTIONS,
    RELATIONSHIP_TIMING_V1,
)
from gbc_astro.providers.swiss import SwissEphemerisProvider

CHART_A = ("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)
CHART_B = ("1988-02-14T09:20:00", "Europe/Paris", 48.8566, 2.3522)
TARGET = datetime(2026, 8, 9, 12, tzinfo=timezone.utc)


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    return bool(path and os.path.exists(os.path.join(path, "sepl_18.se1")))


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class RelationshipTransitTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.chart_a = self.engine.natal(*CHART_A)
        self.chart_b = self.engine.natal(*CHART_B)
        self.result = self.engine.relationship_transits(
            self.chart_a, self.chart_b, TARGET
        )
        self.synastry = self.engine.synastry(self.chart_a, self.chart_b)

    def test_the_two_transit_charts_stay_separate(self) -> None:
        """Which person a transit lands on is what makes it a relationship one."""
        self.assertIsNotNone(self.result.transits_a)
        self.assertIsNotNone(self.result.transits_b)
        self.assertNotEqual(
            self.result.transits_a.to_dict(), self.result.transits_b.to_dict()
        )

    def test_every_activation_cites_both_halves_and_both_resolve(self) -> None:
        transits = {
            aspect.id
            for chart in (self.result.transits_a, self.result.transits_b)
            for aspect in chart.transit_to_natal_aspects
        }
        contacts = {aspect.id for aspect in self.synastry.cross_aspects}
        self.assertTrue(self.result.activations)
        for activation in self.result.activations:
            with self.subTest(activation=activation.id):
                self.assertIn(activation.transit_evidence_id, transits)
                self.assertIn(activation.synastry_evidence_id, contacts)

    def test_one_transit_activating_several_contacts_gets_several_ids(self) -> None:
        """Naming only the transit would collapse them and lose which is which."""
        ids = [activation.id for activation in self.result.activations]
        self.assertEqual(len(ids), len(set(ids)))
        by_transit: dict[str, int] = {}
        for activation in self.result.activations:
            by_transit[activation.transit_evidence_id] = (
                by_transit.get(activation.transit_evidence_id, 0) + 1
            )
        self.assertTrue(any(count > 1 for count in by_transit.values()))

    def test_the_shared_body_is_actually_shared(self) -> None:
        """The join is a fact about geometry, not a label."""
        contacts = {a.id: a for a in self.synastry.cross_aspects}
        for activation in self.result.activations:
            contact = contacts[activation.synastry_evidence_id]
            owned = contact.body_a if activation.chart == "A" else contact.body_b
            with self.subTest(activation=activation.id):
                self.assertEqual(owned, activation.body)

    def test_top_activations_are_the_tightest_and_capped(self) -> None:
        top = self.result.top_activations
        self.assertLessEqual(len(top), RELATIONSHIP_TIMING_V1.top_activations)
        orbs = [activation.transit_orb for activation in top]
        self.assertEqual(orbs, sorted(orbs))

    def test_the_result_says_activation_is_a_join(self) -> None:
        self.assertIn(
            "ACTIVATION_IS_A_JOIN_NOT_AN_INFERENCE",
            {warning.code for warning in self.result.warnings},
        )

    def test_it_is_deterministic(self) -> None:
        again = self.engine.relationship_transits(self.chart_a, self.chart_b, TARGET)
        self.assertEqual(again.to_dict(), self.result.to_dict())


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class CompositeTransitTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.provider = SwissEphemerisProvider(ephemeris_path=path)
        self.houses = SwissHouseCalculator(ephemeris_path=path)
        self.engine = AstrologyEngine(
            provider=self.provider, house_calculator=self.houses
        )
        self.chart_a = self.engine.natal(*CHART_A)
        self.chart_b = self.engine.natal(*CHART_B)
        self.result = self.engine.composite_transits(
            self.chart_a, self.chart_b, TARGET
        )

    def test_contacts_target_the_composite_not_either_natal_chart(self) -> None:
        composite = self.engine.composite(self.chart_a, self.chart_b)
        targets = set(composite.bodies) | set(composite.angles)
        self.assertTrue(self.result.contacts)
        for contact in self.result.contacts:
            with self.subTest(contact=contact.id):
                self.assertIn(contact.composite_body, targets)
                self.assertTrue(contact.id.startswith("composite_transit."))

    def test_composite_angles_are_included_because_this_engine_derives_them(
        self,
    ) -> None:
        self.assertTrue(self.result.meta["anglesIncluded"])

    def test_ids_are_unique(self) -> None:
        ids = [contact.id for contact in self.result.contacts]
        self.assertEqual(len(ids), len(set(ids)))

    def test_a_sidereal_engine_transits_in_its_own_zodiac(self) -> None:
        """Providers answer tropically; anything reaching one directly rotates."""
        sidereal = AstrologyEngine(
            provider=self.provider,
            house_calculator=self.houses,
            profile=VEDIC_SIDEREAL_V1,
        )
        result = sidereal.composite_transits(
            sidereal.natal(*CHART_A), sidereal.natal(*CHART_B), TARGET
        )
        self.assertTrue(result.contacts)
        self.assertNotEqual(
            {c.id for c in result.contacts}, {c.id for c in self.result.contacts}
        )


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class ProgressedSynastryTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.chart_a = self.engine.natal(*CHART_A)
        self.chart_b = self.engine.natal(*CHART_B)
        self.result = self.engine.progressed_synastry(
            self.chart_a, self.chart_b, TARGET
        )

    def test_all_three_directions_are_present_and_labelled(self) -> None:
        grouped = self.result.to_dict()["byDirection"]
        self.assertEqual(set(grouped), set(PROGRESSED_DIRECTIONS))
        for direction, contacts in grouped.items():
            with self.subTest(direction=direction):
                self.assertTrue(contacts)
                for contact in contacts:
                    self.assertEqual(contact["direction"], direction)

    def test_the_three_directions_are_genuinely_different(self) -> None:
        """If two matched, one of them would be computed from the wrong chart."""
        grouped = self.result.to_dict()["byDirection"]
        signatures = {
            direction: {(c["a"], c["b"], c["type"]) for c in contacts}
            for direction, contacts in grouped.items()
        }
        self.assertEqual(len(set(map(frozenset, signatures.values()))), 3)

    def test_every_contact_carries_its_direction_in_its_id(self) -> None:
        for contact in self.result.contacts:
            with self.subTest(contact=contact.id):
                self.assertIn(contact.direction, contact.id)

    def test_ids_are_unique_across_all_three_directions(self) -> None:
        ids = [contact.id for contact in self.result.contacts]
        self.assertEqual(len(ids), len(set(ids)))

    def test_the_result_warns_against_pooling_them(self) -> None:
        self.assertIn(
            "PROGRESSED_DIRECTIONS_ARE_DISTINCT",
            {warning.code for warning in self.result.warnings},
        )

    def test_an_unknown_birth_time_is_refused(self) -> None:
        """Progressions need a known birth time; the pair inherits that."""
        unknown = self.engine.natal(
            "1988-02-14", "Europe/Paris", 48.8566, 2.3522, unknown_time=True
        )
        with self.assertRaises(InvalidCalculationProfileError):
            self.engine.progressed_synastry(self.chart_a, unknown, TARGET)


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class ProgressedCompositeTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.chart_a = self.engine.natal(*CHART_A)
        self.chart_b = self.engine.natal(*CHART_B)

    def test_the_method_is_declared_and_is_progress_then_compose(self) -> None:
        """A composite has no instant of its own to progress from."""
        self.assertEqual(
            RELATIONSHIP_TIMING_V1.progressed_composite_method,
            COMPOSITE_FROM_PROGRESSED_CHARTS,
        )

    def test_it_differs_from_the_natal_composite(self) -> None:
        natal = self.engine.composite(self.chart_a, self.chart_b)
        progressed = self.engine.progressed_composite(
            self.chart_a, self.chart_b, TARGET
        )
        self.assertNotAlmostEqual(
            natal.bodies["sun"].longitude,
            progressed.bodies["sun"].longitude,
            places=3,
        )

    def test_it_is_a_full_composite_with_angles_and_houses(self) -> None:
        progressed = self.engine.progressed_composite(
            self.chart_a, self.chart_b, TARGET
        )
        self.assertTrue(progressed.bodies)
        self.assertTrue(progressed.angles)
        self.assertTrue(progressed.houses)

    def test_at_the_birth_moment_it_matches_the_natal_composite(self) -> None:
        """Age zero progresses to the birth instant, so the two must agree."""
        birth = datetime.fromisoformat(
            self.chart_a.subject.utc_datetime.replace("Z", "+00:00")
        )
        natal = self.engine.composite(self.chart_a, self.chart_b)
        progressed = self.engine.progressed_composite(
            self.chart_a, self.chart_b, birth
        )
        # Chart B is progressed from its own birth, not A's, so only A's side
        # is exactly at age zero. The Sun still has to be close.
        self.assertLess(
            abs(natal.bodies["sun"].longitude - progressed.bodies["sun"].longitude),
            3.0,
        )

    def test_it_is_deterministic(self) -> None:
        first = self.engine.progressed_composite(self.chart_a, self.chart_b, TARGET)
        second = self.engine.progressed_composite(self.chart_a, self.chart_b, TARGET)
        self.assertEqual(first.to_dict(), second.to_dict())


@unittest.skipUnless(_swiss_available(), "Needs Swiss Ephemeris data")
class SiderealCompositeFrameTests(unittest.TestCase):
    """A composite chart must sit wholly in one zodiac.

    The composite angles are derived from the midpoint Midheaven by way of its
    right ascension, and right ascension is measured from the true equinox --
    so that conversion is only valid on a tropical longitude. On a sidereal
    chart the two Midheavens arrive already rotated, and feeding their midpoint
    to the conversion produced an ARMC wrong by the ayanamsa. The Ascendant that
    came out was 13.6 degrees from where the rest of the chart sat, while the
    bodies and the Midheaven were correct -- a chart half in each frame.

    No test caught it, because none compared a sidereal composite's angles
    against its own bodies. This one does.
    """

    def setUp(self) -> None:
        import dataclasses

        from gbc_astro.profiles.defaults import WESTERN_MODERN_V1

        path = os.environ["GBC_SWISS_EPHE_PATH"]
        provider = SwissEphemerisProvider(ephemeris_path=path)
        houses = SwissHouseCalculator(ephemeris_path=path)
        # Only the zodiac differs from the tropical default: same house system,
        # same rulership. Anything that moves is a frame effect and nothing else.
        self.tropical = AstrologyEngine(provider=provider, house_calculator=houses)
        self.sidereal = AstrologyEngine(
            provider=provider,
            house_calculator=houses,
            profile=dataclasses.replace(
                WESTERN_MODERN_V1,
                id="zodiac-isolation",
                zodiac="sidereal",
                ayanamsa="lahiri",
            ),
        )

    def _offsets(self, tropical, sidereal) -> tuple[set[float], set[float]]:
        bodies = {
            round((tropical.bodies[k].longitude - sidereal.bodies[k].longitude) % 360, 6)
            for k in tropical.bodies
        }
        angles = {
            round((tropical.angles[k].longitude - sidereal.angles[k].longitude) % 360, 6)
            for k in tropical.angles
        }
        return bodies, angles

    def test_composite_angles_rotate_with_its_bodies(self) -> None:
        tropical = self.tropical.composite(
            self.tropical.natal(*CHART_A), self.tropical.natal(*CHART_B)
        )
        sidereal = self.sidereal.composite(
            self.sidereal.natal(*CHART_A), self.sidereal.natal(*CHART_B)
        )
        bodies, angles = self._offsets(tropical, sidereal)

        self.assertEqual(len(bodies), 1, "bodies must share one rotation")
        self.assertEqual(len(angles), 1, "angles must share one rotation")
        self.assertEqual(
            bodies,
            angles,
            "the composite Ascendant was 13.6 degrees adrift from its own bodies",
        )

    def test_composite_cusps_rotate_with_its_bodies(self) -> None:
        tropical = self.tropical.composite(
            self.tropical.natal(*CHART_A), self.tropical.natal(*CHART_B)
        )
        sidereal = self.sidereal.composite(
            self.sidereal.natal(*CHART_A), self.sidereal.natal(*CHART_B)
        )
        bodies, _ = self._offsets(tropical, sidereal)
        cusps = {
            round((a.cusp_longitude - b.cusp_longitude) % 360, 6)
            for a, b in zip(tropical.houses, sidereal.houses, strict=True)
        }
        self.assertEqual(cusps, bodies)

    def test_the_progressed_composite_inherits_the_fix(self) -> None:
        tropical = self.tropical.progressed_composite(
            self.tropical.natal(*CHART_A), self.tropical.natal(*CHART_B), TARGET
        )
        sidereal = self.sidereal.progressed_composite(
            self.sidereal.natal(*CHART_A), self.sidereal.natal(*CHART_B), TARGET
        )
        bodies, angles = self._offsets(tropical, sidereal)
        self.assertEqual(bodies, angles)

    def test_a_tropical_composite_is_untouched_by_the_rotation_path(self) -> None:
        """Zero offset must be a no-op, not a rebuild that perturbs anything."""
        first = self.tropical.composite(
            self.tropical.natal(*CHART_A), self.tropical.natal(*CHART_B)
        )
        second = self.tropical.composite(
            self.tropical.natal(*CHART_A), self.tropical.natal(*CHART_B)
        )
        self.assertEqual(first.to_dict(), second.to_dict())
