"""Chart ruler, house rulers, dignity, dispositors and dominance.

Nothing here touches an ephemeris, so most of these are exact assertions rather
than tolerances. The two that matter most are structural: that the rulership
table follows the calculation profile rather than a hardcoded default, and that
a dispositor walk terminates on a chart made entirely of loops.
"""

from __future__ import annotations

import os
import unittest

from gbc_astro import AstrologyEngine
from gbc_astro.derived.rulership import (
    dignity_of,
    dispositor_chains,
    dominant_planets,
    final_dispositors,
    mutual_receptions,
)
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.models.position import BodyPosition
from gbc_astro.profiles.defaults import VEDIC_SIDEREAL_V1
from gbc_astro.profiles.rulership import (
    DOMINANT_WESTERN_V1,
    MODERN_WESTERN_V1,
    TRADITIONAL_SEPTENARY_V1,
    resolve_rulership_profile,
)
from gbc_astro.providers.swiss import SwissEphemerisProvider

BIRTH = ("1992-11-03T14:35:00", "Asia/Ho_Chi_Minh", 21.0285, 105.8542)


def _body(body_id: str, sign: str, degree: float = 10.0, house: int = 1) -> BodyPosition:
    return BodyPosition(
        body_id=body_id,
        longitude=0.0,
        latitude=0.0,
        distance=None,
        speed_longitude=None,
        retrograde=False,
        sign=sign,
        degree_in_sign=degree,
        house=house,
    )


def _swiss_available() -> bool:
    try:
        import swisseph  # noqa: F401
    except ImportError:
        return False
    path = os.environ.get("GBC_SWISS_EPHE_PATH")
    return bool(path and os.path.exists(os.path.join(path, "sepl_18.se1")))


class RulershipTableTests(unittest.TestCase):
    """The tables themselves, checked against what tradition actually says."""

    def test_every_sign_has_exactly_one_ruler_in_both_schemes(self) -> None:
        for profile in (TRADITIONAL_SEPTENARY_V1, MODERN_WESTERN_V1):
            with self.subTest(profile=profile.id):
                self.assertEqual(len(profile.domicile), 12)

    def test_the_septenary_scheme_uses_only_the_classical_seven(self) -> None:
        self.assertEqual(
            set(TRADITIONAL_SEPTENARY_V1.domicile.values()),
            {"sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"},
        )

    def test_the_luminaries_rule_one_sign_and_the_rest_rule_two(self) -> None:
        for body_id in ("sun", "moon"):
            self.assertEqual(len(TRADITIONAL_SEPTENARY_V1.rules(body_id)), 1)
        for body_id in ("mercury", "venus", "mars", "jupiter", "saturn"):
            with self.subTest(body=body_id):
                self.assertEqual(len(TRADITIONAL_SEPTENARY_V1.rules(body_id)), 2)

    def test_the_modern_scheme_reassigns_exactly_three_signs(self) -> None:
        differences = {
            sign
            for sign, ruler in MODERN_WESTERN_V1.domicile.items()
            if TRADITIONAL_SEPTENARY_V1.domicile[sign] != ruler
        }
        self.assertEqual(differences, {"scorpio", "aquarius", "pisces"})

    def test_displaced_classical_rulers_survive_as_co_rulers(self) -> None:
        self.assertEqual(MODERN_WESTERN_V1.co_rulers["scorpio"], ("mars",))
        self.assertEqual(MODERN_WESTERN_V1.co_rulers["aquarius"], ("saturn",))
        self.assertEqual(MODERN_WESTERN_V1.co_rulers["pisces"], ("jupiter",))

    def test_detriment_and_fall_are_derived_so_they_cannot_disagree(self) -> None:
        """Every detriment faces a sign the body rules; every fall its exaltation."""
        for profile in (TRADITIONAL_SEPTENARY_V1, MODERN_WESTERN_V1):
            for sign, ruler in profile.domicile.items():
                with self.subTest(profile=profile.id, body=ruler):
                    self.assertIn(profile.opposite_sign(sign), profile.detriment_signs(ruler))
            for sign, exalted in profile.exaltation.items():
                with self.subTest(profile=profile.id, exalted=exalted):
                    self.assertEqual(profile.fall_sign(exalted), profile.opposite_sign(sign))

    def test_an_unknown_scheme_is_refused_rather_than_defaulted(self) -> None:
        with self.assertRaises(InvalidCalculationProfileError):
            resolve_rulership_profile("hellenistic-with-extras")


class DignityTests(unittest.TestCase):
    def test_the_four_major_dignities(self) -> None:
        cases = (
            ("mars", "aries", "domicile"),
            ("sun", "aries", "exaltation"),
            ("mercury", "sagittarius", "detriment"),
            ("mars", "cancer", "fall"),
            ("jupiter", "taurus", "peregrine"),
        )
        for body_id, sign, expected in cases:
            with self.subTest(body=body_id, sign=sign):
                self.assertEqual(
                    dignity_of(_body(body_id, sign), MODERN_WESTERN_V1).state, expected
                )

    def test_an_unrated_body_is_not_reported_as_peregrine(self) -> None:
        """Peregrine means "in none of its dignities" and presupposes it has some.

        An outer planet under a septenary scheme has no rulership at all, which
        is a different statement, and merging the two would claim a judgement
        the scheme does not make.
        """
        self.assertEqual(
            dignity_of(_body("pluto", "scorpio"), TRADITIONAL_SEPTENARY_V1).state,
            "unrated",
        )
        self.assertEqual(
            dignity_of(_body("pluto", "scorpio"), MODERN_WESTERN_V1).state, "domicile"
        )

    def test_exact_exaltation_is_flagged_only_at_the_traditional_degree(self) -> None:
        self.assertTrue(
            dignity_of(_body("sun", "aries", degree=19.0), MODERN_WESTERN_V1).exact_exaltation
        )
        self.assertFalse(
            dignity_of(_body("sun", "aries", degree=3.0), MODERN_WESTERN_V1).exact_exaltation
        )


class DispositorTests(unittest.TestCase):
    def test_a_planet_in_its_own_sign_is_a_final_dispositor(self) -> None:
        bodies = {
            "mars": _body("mars", "aries"),
            "venus": _body("venus", "aries"),
        }
        chains = dispositor_chains(bodies, MODERN_WESTERN_V1)
        self.assertEqual(final_dispositors(chains), ("mars",))

    def test_a_chart_of_nothing_but_a_loop_terminates_and_says_so(self) -> None:
        """A walk that assumes a self-ruler exists never returns on this input.

        Venus in a Mars sign and Mars in a Venus sign close a two-planet loop
        with no final dispositor anywhere in the chart. That is a real chart, not
        a degenerate one, and the honest answer is an empty tuple.
        """
        bodies = {
            "venus": _body("venus", "aries"),
            "mars": _body("mars", "taurus"),
        }
        chains = dispositor_chains(bodies, MODERN_WESTERN_V1)
        self.assertEqual(final_dispositors(chains), ())
        for chain in chains:
            with self.subTest(body=chain.body_id):
                self.assertEqual(set(chain.loop), {"venus", "mars"})

    def test_a_three_planet_loop_is_reported_whole(self) -> None:
        bodies = {
            "mars": _body("mars", "taurus"),
            "venus": _body("venus", "gemini"),
            "mercury": _body("mercury", "aries"),
        }
        chains = dispositor_chains(bodies, MODERN_WESTERN_V1)
        self.assertEqual(final_dispositors(chains), ())
        for chain in chains:
            with self.subTest(body=chain.body_id):
                self.assertEqual(set(chain.loop), {"mars", "venus", "mercury"})

    def test_mutual_reception_is_symmetric_and_reported_once(self) -> None:
        bodies = {
            "venus": _body("venus", "aries"),
            "mars": _body("mars", "taurus"),
        }
        self.assertEqual(
            mutual_receptions(bodies, MODERN_WESTERN_V1), (("mars", "venus"),)
        )

    def test_unrated_bodies_start_no_chain(self) -> None:
        bodies = {
            "sun": _body("sun", "leo"),
            "chiron": _body("chiron", "leo"),
        }
        chains = dispositor_chains(bodies, MODERN_WESTERN_V1)
        self.assertEqual({chain.body_id for chain in chains}, {"sun"})


class DominanceTests(unittest.TestCase):
    def test_angularity_outweighs_a_cadent_placement_of_the_same_planet(self) -> None:
        angular = {"mars": _body("mars", "gemini", house=1)}
        cadent = {"mars": _body("mars", "gemini", house=12)}
        first = dominant_planets(angular, (), {"mars": "peregrine"}, None, DOMINANT_WESTERN_V1)
        second = dominant_planets(cadent, (), {"mars": "peregrine"}, None, DOMINANT_WESTERN_V1)
        self.assertGreater(first[0].score, second[0].score)

    def test_every_component_of_the_score_is_returned(self) -> None:
        """A score with no breakdown is a number a caller has to trust."""
        result = dominant_planets(
            {"sun": _body("sun", "leo", house=1)},
            (),
            {"sun": "domicile"},
            "sun",
            DOMINANT_WESTERN_V1,
        )
        components = result[0].components
        self.assertEqual(
            set(components),
            {"house", "sign", "dignity", "aspects", "luminary", "chartRuler"},
        )
        self.assertAlmostEqual(sum(components.values()), result[0].score, places=9)

    def test_ranking_is_stable_for_tied_scores(self) -> None:
        bodies = {
            "venus": _body("venus", "gemini", house=3),
            "mars": _body("mars", "gemini", house=3),
        }
        dignity = {"venus": "peregrine", "mars": "peregrine"}
        first = dominant_planets(bodies, (), dignity, None, DOMINANT_WESTERN_V1)
        second = dominant_planets(
            dict(reversed(list(bodies.items()))), (), dignity, None, DOMINANT_WESTERN_V1
        )
        self.assertEqual(
            [planet.body_id for planet in first],
            [planet.body_id for planet in second],
        )


@unittest.skipUnless(_swiss_available(), "Rulership on real charts needs Swiss data")
class RulershipOnRealChartsTests(unittest.TestCase):
    def setUp(self) -> None:
        path = os.environ["GBC_SWISS_EPHE_PATH"]
        provider = SwissEphemerisProvider(ephemeris_path=path)
        houses = SwissHouseCalculator(ephemeris_path=path)
        self.tropical = AstrologyEngine(provider=provider, house_calculator=houses)
        self.sidereal = AstrologyEngine(
            provider=provider, house_calculator=houses, profile=VEDIC_SIDEREAL_V1
        )

    def test_the_table_follows_the_calculation_profile_not_a_default(self) -> None:
        """The whole reason this lives in the engine rather than in a client.

        A sidereal chart cast in the Vedic tradition does not give Scorpio to
        Pluto. Answering it from the modern table would name the wrong ruler for
        three signs in twelve and corrupt every chain passing through them.
        """
        chart = self.sidereal.natal(*BIRTH)
        self.assertEqual(chart.meta.rulership_profile, "traditional-septenary-v1")
        self.assertEqual(
            self.tropical.natal(*BIRTH).meta.rulership_profile, "modern-western-v1"
        )

        pluto = next(d for d in chart.derived.dignities if d.body_id == "pluto")
        self.assertEqual(pluto.state, "unrated")

    def test_the_chart_ruler_is_the_ruler_of_the_rising_sign(self) -> None:
        for engine in (self.tropical, self.sidereal):
            chart = engine.natal(*BIRTH)
            with self.subTest(profile=chart.meta.rulership_profile):
                profile = resolve_rulership_profile(engine.profile.rulership)
                assert chart.derived.chart_ruler is not None
                self.assertEqual(
                    chart.derived.chart_ruler.body_id,
                    profile.domicile[chart.angles["ascendant"].sign],
                )

    def test_a_chart_with_no_ascendant_has_no_chart_ruler_and_no_house_rulers(
        self,
    ) -> None:
        """No rising sign is invented for an unknown birth time."""
        chart = self.tropical.natal(
            "1992-11-03", "Asia/Ho_Chi_Minh", 21.0285, 105.8542, unknown_time=True
        )
        self.assertIsNone(chart.derived.chart_ruler)
        self.assertEqual(chart.derived.house_rulers, ())
        # Dignity needs only a sign, so it survives an unknown birth time.
        self.assertEqual(len(chart.derived.dignities), len(chart.bodies))

    def test_house_rulers_cover_every_cusp(self) -> None:
        chart = self.tropical.natal(*BIRTH)
        self.assertEqual(
            [ruler.house for ruler in chart.derived.house_rulers], list(range(1, 13))
        )
        for ruler in chart.derived.house_rulers:
            with self.subTest(house=ruler.house):
                self.assertEqual(
                    ruler.cusp_sign, chart.houses[ruler.house - 1].sign
                )

    def test_the_profiles_that_shaped_the_answer_are_published(self) -> None:
        meta = self.tropical.natal(*BIRTH).meta
        self.assertEqual(meta.rulership_profile_version, MODERN_WESTERN_V1.version)
        self.assertEqual(meta.dominant_profile, DOMINANT_WESTERN_V1.id)
        self.assertEqual(meta.dominant_profile_version, DOMINANT_WESTERN_V1.version)

    def test_dominance_ranks_every_participating_body_once(self) -> None:
        chart = self.tropical.natal(*BIRTH)
        ranked = chart.derived.dominant_planets
        self.assertEqual(
            [planet.rank for planet in ranked], list(range(1, len(ranked) + 1))
        )
        self.assertEqual(
            len({planet.body_id for planet in ranked}), len(ranked)
        )
        # The nodes and Chiron are not planets and do not compete for dominance.
        self.assertNotIn("chiron", {planet.body_id for planet in ranked})
