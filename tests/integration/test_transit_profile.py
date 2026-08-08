"""Transit orb boundaries, ranking, determinism and unknown-time behaviour.

Covers Phase 08B-1 sections 27 to 32. Aspect detection is checked against
synthetic charts with planted separations rather than whatever the sky happens
to be doing, so a failure points at the orb policy and nothing else.
"""

from __future__ import annotations

import os
import unittest
from dataclasses import replace
from datetime import datetime, timezone

from gbc_astro import AstrologyEngine
from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.models.forecast import TransitAspect
from gbc_astro.profiles.transit import (
    NATAL_ANGLE_TARGETS,
    TRANSIT_ASPECT_PROFILE_V1,
    TRANSIT_PROFILE_V1,
    TRANSIT_RANKING_V1,
    TRANSITING_BODIES,
)
from gbc_astro.providers.swiss import SwissEphemerisProvider

INSTANT = datetime(2026, 8, 8, 12, tzinfo=timezone.utc)


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    required = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
    return bool(path and all(os.path.exists(os.path.join(path, name)) for name in required))


def _aspect(
    transit_body: str = "saturn",
    natal_body: str = "sun",
    aspect_type: str = "conjunction",
    orb: float = 0.0,
    phase: str = "applying",
    kind: str = "body",
) -> TransitAspect:
    exact = {
        "conjunction": 0.0,
        "sextile": 60.0,
        "square": 90.0,
        "trine": 120.0,
        "opposition": 180.0,
    }[aspect_type]
    return TransitAspect(
        transit_body=transit_body,
        natal_body=natal_body,
        natal_target_kind=kind,
        aspect_type=aspect_type,
        exact_angle=exact,
        actual_angle=exact + orb,
        orb=orb,
        phase=phase,
    )


class AspectProfileTests(unittest.TestCase):
    """Section 5: the orb policy is versioned, explicit and tighter than natal."""

    def test_profile_is_versioned_and_named(self) -> None:
        self.assertEqual(TRANSIT_ASPECT_PROFILE_V1.id, "transit-major-v1")
        self.assertEqual(TRANSIT_ASPECT_PROFILE_V1.version, "1.0.0")

    def test_exactly_the_five_major_aspects(self) -> None:
        self.assertEqual(
            {rule.aspect_type for rule in TRANSIT_ASPECT_PROFILE_V1.rules},
            {"conjunction", "opposition", "square", "trine", "sextile"},
        )

    def test_orbs_are_tighter_than_the_natal_profile(self) -> None:
        """The whole reason a separate profile exists."""
        from gbc_astro.profiles.defaults import WESTERN_MODERN_V1

        natal = {r.aspect_type: r.orb for r in WESTERN_MODERN_V1.aspect_profile.rules}
        for rule in TRANSIT_ASPECT_PROFILE_V1.rules:
            with self.subTest(aspect=rule.aspect_type):
                self.assertLess(rule.orb, natal[rule.aspect_type])

    def test_transiting_scope_is_the_ten_planets(self) -> None:
        self.assertEqual(len(TRANSITING_BODIES), 10)
        for excluded in ("true_node", "mean_node", "chiron"):
            self.assertNotIn(excluded, TRANSITING_BODIES)

    def test_only_ascendant_and_mc_are_angle_targets(self) -> None:
        """Descendant and IC are the exact opposites; including both double counts."""
        self.assertEqual(NATAL_ANGLE_TARGETS, ("ascendant", "mc"))


@unittest.skipUnless(_swiss_available(), "Transit detection needs Swiss Ephemeris data")
class AspectDetectionBoundaryTests(unittest.TestCase):
    """Section 27: detection at, just inside, and just outside each orb limit."""

    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.natal = self.engine.natal(
            "1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542
        )
        self.transits = self.engine.transits(self.natal, INSTANT)
        self.limits = {r.aspect_type: r.orb for r in TRANSIT_ASPECT_PROFILE_V1.rules}

    def test_every_reported_aspect_is_inside_its_orb_limit(self) -> None:
        self.assertTrue(self.transits.transit_to_natal_aspects)
        for aspect in self.transits.transit_to_natal_aspects:
            self.assertLessEqual(aspect.orb, self.limits[aspect.aspect_type])

    def test_orb_matches_the_separation_and_the_exact_angle(self) -> None:
        for aspect in self.transits.transit_to_natal_aspects:
            self.assertAlmostEqual(
                aspect.orb, abs(aspect.actual_angle - aspect.exact_angle), places=9
            )

    def test_nothing_outside_the_orb_limit_is_reported(self) -> None:
        """Anything the natal profile would have caught but this one should not."""
        wide = self.engine.transits(
            self.natal,
            INSTANT,
            top_count=100,
        )
        for aspect in wide.transit_to_natal_aspects:
            self.assertLessEqual(aspect.orb, self.limits[aspect.aspect_type])

    def test_detection_survives_the_zero_degree_boundary(self) -> None:
        """A natal point just past 0 Aries against a transit just before it."""
        from gbc_astro.aspects.engine import match_aspect_rule
        from gbc_astro.astronomy.circular import shortest_angular_distance

        for first, second in ((359.5, 0.5), (0.2, 359.8), (359.0, 1.5), (0.0, 359.0)):
            with self.subTest(first=first, second=second):
                separation = shortest_angular_distance(
                    normalize_longitude(first), normalize_longitude(second)
                )
                matched = match_aspect_rule(separation, TRANSIT_ASPECT_PROFILE_V1)
                self.assertIsNotNone(matched)
                assert matched is not None
                self.assertEqual(matched[0].aspect_type, "conjunction")

    def test_the_tighter_profile_really_does_narrow_the_field(self) -> None:
        """Measured: natal orbs leave three to four dozen active, this leaves a dozen."""
        from gbc_astro.profiles.defaults import WESTERN_MODERN_V1

        wide_profile = replace(
            TRANSIT_PROFILE_V1, aspect_profile=WESTERN_MODERN_V1.aspect_profile
        )
        wide_engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=os.environ["GBC_SWISS_EPHE_PATH"]),
            house_calculator=SwissHouseCalculator(
                ephemeris_path=os.environ["GBC_SWISS_EPHE_PATH"]
            ),
            transit_profile=wide_profile,
        )
        wide = wide_engine.transits(self.natal, INSTANT)
        self.assertGreater(
            len(wide.transit_to_natal_aspects),
            2 * len(self.transits.transit_to_natal_aspects),
        )


class RankingTests(unittest.TestCase):
    """Section 28: ranking behaves as documented and never ties by chance."""

    def _rank(self, aspects: list[TransitAspect]) -> list[TransitAspect]:
        from gbc_astro.forecast.transits import _ranked

        limits = {r.aspect_type: r.orb for r in TRANSIT_ASPECT_PROFILE_V1.rules}
        return list(_ranked(aspects, limits, TRANSIT_PROFILE_V1))

    def test_smaller_orb_wins_when_everything_else_is_equal(self) -> None:
        ranked = self._rank([_aspect(orb=2.5), _aspect(orb=0.1)])
        self.assertAlmostEqual(ranked[0].orb, 0.1)
        self.assertGreater(ranked[0].score, ranked[1].score)

    def test_slower_transiting_body_outranks_a_faster_one(self) -> None:
        ranked = self._rank(
            [_aspect(transit_body="moon", orb=0.1), _aspect(transit_body="pluto", orb=0.1)]
        )
        self.assertEqual(ranked[0].transit_body, "pluto")

    def test_hard_aspect_outranks_a_soft_one(self) -> None:
        ranked = self._rank(
            [_aspect(aspect_type="sextile", orb=0.1), _aspect(aspect_type="conjunction", orb=0.1)]
        )
        self.assertEqual(ranked[0].aspect_type, "conjunction")

    def test_personal_natal_target_outranks_an_outer_one(self) -> None:
        ranked = self._rank(
            [_aspect(natal_body="neptune", orb=0.1), _aspect(natal_body="sun", orb=0.1)]
        )
        self.assertEqual(ranked[0].natal_body, "sun")

    def test_applying_outranks_separating_all_else_equal(self) -> None:
        ranked = self._rank(
            [_aspect(phase="separating", orb=1.0), _aspect(phase="applying", orb=1.0)]
        )
        self.assertEqual(ranked[0].phase, "applying")

    def test_ranks_are_a_contiguous_sequence_from_one(self) -> None:
        ranked = self._rank([_aspect(orb=float(index) / 2.0) for index in range(6)])
        self.assertEqual([item.rank for item in ranked], [1, 2, 3, 4, 5, 6])

    def test_ties_are_broken_by_name_not_by_chance(self) -> None:
        """Identical scores must still order identically on every run."""
        tied = [
            _aspect(transit_body="saturn", natal_body="venus", orb=1.0),
            _aspect(transit_body="saturn", natal_body="mars", orb=1.0),
        ]
        first = [item.id for item in self._rank(tied)]
        second = [item.id for item in self._rank(list(reversed(tied)))]
        self.assertEqual(first, second)
        self.assertEqual(first[0], "transit.saturn.conjunction.natal.mars")

    def test_profile_is_versioned_and_declares_its_tie_breaker(self) -> None:
        self.assertEqual(TRANSIT_RANKING_V1.id, "transit-ranking-v1")
        self.assertEqual(TRANSIT_RANKING_V1.version, "1.0.0")
        self.assertEqual(TRANSIT_RANKING_V1.default_top_count, 3)
        self.assertIn("score_desc", TRANSIT_RANKING_V1.tie_breaker)

    def test_scoring_uses_every_documented_factor(self) -> None:
        from gbc_astro.forecast.transits import rank_score

        base = _aspect(orb=0.0, phase="separating")
        expected = (
            TRANSIT_RANKING_V1.aspect_weights["conjunction"]
            * TRANSIT_RANKING_V1.transiting_body_weights["saturn"]
            * TRANSIT_RANKING_V1.natal_target_weights["sun"]
            * 1.0
            * TRANSIT_RANKING_V1.phase_multipliers["separating"]
        )
        self.assertAlmostEqual(rank_score(base, 3.0, TRANSIT_PROFILE_V1), expected, places=9)


@unittest.skipUnless(_swiss_available(), "Transit tests need Swiss Ephemeris data")
class TransitIdentityAndDeterminismTests(unittest.TestCase):
    """Sections 13 and 32."""

    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.natal = self.engine.natal(
            "1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542
        )

    def test_ids_are_deterministic_and_unique(self) -> None:
        transits = self.engine.transits(self.natal, INSTANT)
        identifiers = [aspect.id for aspect in transits.transit_to_natal_aspects]

        self.assertEqual(len(identifiers), len(set(identifiers)))
        for aspect in transits.transit_to_natal_aspects:
            self.assertEqual(
                aspect.id,
                f"transit.{aspect.transit_body}.{aspect.aspect_type}"
                f".natal.{aspect.natal_body}",
            )

    def test_ids_carry_no_prose_and_no_numbers(self) -> None:
        transits = self.engine.transits(self.natal, INSTANT)
        for aspect in transits.transit_to_natal_aspects:
            self.assertRegex(aspect.id, r"^transit\.[a-z_]+\.[a-z]+\.natal\.[a-z_]+$")

    def test_repeated_calls_are_byte_identical(self) -> None:
        first = self.engine.transits(self.natal, INSTANT).to_json()
        second = self.engine.transits(self.natal, INSTANT).to_json()
        self.assertEqual(first, second)

    def test_ordering_is_stable_across_runs(self) -> None:
        runs = [
            [aspect.id for aspect in self.engine.transits(self.natal, INSTANT).top_aspects]
            for _ in range(5)
        ]
        self.assertEqual(len({tuple(run) for run in runs}), 1)

    def test_top_aspects_are_the_head_of_the_ranked_list(self) -> None:
        transits = self.engine.transits(self.natal, INSTANT)
        self.assertEqual(
            [aspect.id for aspect in transits.top_aspects],
            [aspect.id for aspect in transits.transit_to_natal_aspects[:3]],
        )

    def test_top_count_is_configurable_and_defaults_to_three(self) -> None:
        self.assertEqual(len(self.engine.transits(self.natal, INSTANT).top_aspects), 3)
        self.assertEqual(
            len(self.engine.transits(self.natal, INSTANT, top_count=1).top_aspects), 1
        )
        self.assertEqual(
            len(self.engine.transits(self.natal, INSTANT, top_count=0).top_aspects), 0
        )

    def test_full_evidence_is_kept_alongside_the_ranked_subset(self) -> None:
        """Section 17: the ranked subset must not discard the rest."""
        transits = self.engine.transits(self.natal, INSTANT, top_count=1)
        self.assertGreater(len(transits.transit_to_natal_aspects), 1)

    def test_provenance_names_both_profiles_and_their_versions(self) -> None:
        meta = self.engine.transits(self.natal, INSTANT).meta
        self.assertEqual(meta["transitAspectProfile"], "transit-major-v1")
        self.assertEqual(meta["transitAspectProfileVersion"], "1.0.0")
        self.assertEqual(meta["rankingProfile"], "transit-ranking-v1")
        self.assertEqual(meta["rankingProfileVersion"], "1.0.0")
        self.assertIn("aspectWeights", meta["rankingProfileDetail"])


@unittest.skipUnless(_swiss_available(), "Transit tests need Swiss Ephemeris data")
class UnknownTimeTransitTests(unittest.TestCase):
    """Section 29: no angles, no houses, planet-to-planet still works."""

    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        self.engine = AstrologyEngine(
            provider=SwissEphemerisProvider(ephemeris_path=path),
            house_calculator=SwissHouseCalculator(ephemeris_path=path),
        )
        self.unknown = self.engine.natal(
            "1992-11-03", "Asia/Ho_Chi_Minh", 21.0285, 105.8542, unknown_time=True
        )
        self.transits = self.engine.transits(self.unknown, INSTANT)

    def test_no_angle_targets_are_invented(self) -> None:
        self.assertFalse(self.transits.meta["natalAngleTargetsIncluded"])
        for aspect in self.transits.transit_to_natal_aspects:
            self.assertEqual(aspect.natal_target_kind, "body")
            self.assertNotIn(aspect.natal_body, ("ascendant", "mc", "descendant", "ic"))

    def test_no_house_placements(self) -> None:
        self.assertEqual(self.transits.transit_house_placements, ())
        self.assertIn(
            "TRANSIT_HOUSE_PLACEMENT_UNAVAILABLE",
            {warning.code for warning in self.transits.warnings},
        )

    def test_planet_to_planet_transits_still_work_and_rank(self) -> None:
        self.assertTrue(self.transits.transit_to_natal_aspects)
        self.assertTrue(self.transits.top_aspects)
        self.assertEqual([a.rank for a in self.transits.top_aspects], [1, 2, 3])

    def test_a_known_time_chart_does_include_angle_targets(self) -> None:
        known = self.engine.natal(
            "1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542
        )
        transits = self.engine.transits(known, INSTANT)
        self.assertTrue(transits.meta["natalAngleTargetsIncluded"])
