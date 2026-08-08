"""Chart ruler, house rulers, essential dignity, dispositors and dominance.

None of this touches an ephemeris. Every answer here is a function of the signs
the chart already reports plus the rulership table the calculation profile
names, which is why it belongs in `derived` alongside the element counts rather
than behind its own endpoint.

That it needs no astronomy is not a reason to compute it in a client. The
tables encode contested decisions -- traditional or modern rulership changes
the chart ruler, every dispositor chain, and half the detriments -- and a
decision that is not published is a decision two clients can disagree about
without either knowing. Here it travels in the result.

Dispositor chains
-----------------
The one part with real structure. Follow a planet to the ruler of its sign,
then that ruler to the ruler of *its* sign, and so on. The walk always
terminates, but it terminates in one of two very different ways, and conflating
them is the usual error:

* A planet in its own sign rules itself, ending the chain in a **final
  dispositor** -- one planet the whole chart, or part of it, answers to.
* Two or more planets can rule each other's signs in a closed loop with no
  final dispositor at all. A chart can consist entirely of such loops and have
  no final dispositor whatever.

A walk that assumes termination in a self-ruler hangs forever on the second
case, so the loop is detected explicitly and reported as what it is. A
two-planet loop is also a **mutual reception**, which is worth naming
separately because it is read as a relationship between the pair rather than as
a defect in the chain.
"""

from __future__ import annotations

from gbc_astro.models.aspect import Aspect
from gbc_astro.models.position import AnglePosition, BodyPosition, HouseCusp
from gbc_astro.models.rulership import (
    Dignity,
    DispositorChain,
    DominantPlanet,
    HouseRuler,
    RulerPlacement,
)
from gbc_astro.profiles.rulership import DominantProfile, RulershipProfile

# Houses 1, 4, 7 and 10 are angular; 2, 5, 8, 11 succedent; the rest cadent.
ANGULAR_HOUSES = frozenset({1, 4, 7, 10})
SUCCEDENT_HOUSES = frozenset({2, 5, 8, 11})

DOMICILE = "domicile"
EXALTATION = "exaltation"
DETRIMENT = "detriment"
FALL = "fall"
PEREGRINE = "peregrine"
UNRATED = "unrated"


def _placement(body_id: str, bodies: dict[str, BodyPosition]) -> RulerPlacement:
    body = bodies.get(body_id)
    if body is None:
        # The ruler is named by the table but absent from the chart, which
        # happens when a septenary scheme meets a body set that excludes an
        # outer planet, or the other way round. Naming it with no placement is
        # more useful than dropping the ruler entirely.
        return RulerPlacement(body_id, None, None, None, None)
    return RulerPlacement(
        body_id=body_id,
        sign=body.sign,
        house=body.house,
        longitude=body.longitude,
        retrograde=body.retrograde,
    )


def chart_ruler(
    angles: dict[str, AnglePosition],
    bodies: dict[str, BodyPosition],
    profile: RulershipProfile,
) -> RulerPlacement | None:
    """The ruler of the rising sign, and where it sits.

    None when the chart has no Ascendant, which is every chart with an unknown
    birth time. No substitute rising sign is invented.
    """
    ascendant = angles.get("ascendant")
    if ascendant is None:
        return None
    ruler_id = profile.domicile.get(ascendant.sign)
    if ruler_id is None:
        return None
    return _placement(ruler_id, bodies)


def house_rulers(
    houses: tuple[HouseCusp, ...],
    bodies: dict[str, BodyPosition],
    profile: RulershipProfile,
) -> tuple[HouseRuler, ...]:
    """The ruler of the sign on each cusp, and where that ruler is."""
    rulers: list[HouseRuler] = []
    for cusp in houses:
        ruler_id = profile.domicile.get(cusp.sign)
        if ruler_id is None:
            continue
        rulers.append(
            HouseRuler(
                house=cusp.number,
                cusp_sign=cusp.sign,
                ruler=_placement(ruler_id, bodies),
                co_rulers=profile.co_rulers.get(cusp.sign, ()),
            )
        )
    return tuple(rulers)


def dignity_of(body: BodyPosition, profile: RulershipProfile) -> Dignity:
    """Which of the four major dignities this body's sign puts it in.

    `unrated` is not a fifth dignity. It marks a body the scheme assigns no
    rulership to at all -- an outer planet under the septenary tables -- which
    is a different statement from peregrine, and collapsing the two would claim
    a judgement the scheme does not make.
    """
    if body.body_id in profile.unrated_bodies:
        return Dignity(body.body_id, body.sign, UNRATED)

    if profile.domicile.get(body.sign) == body.body_id:
        return Dignity(body.body_id, body.sign, DOMICILE)

    if profile.exaltation.get(body.sign) == body.body_id:
        degree = profile.exaltation_degrees.get(body.body_id)
        exact = degree is not None and abs(body.degree_in_sign - degree) <= 1.0
        return Dignity(body.body_id, body.sign, EXALTATION, exact_exaltation=exact)

    if body.sign in profile.detriment_signs(body.body_id):
        return Dignity(body.body_id, body.sign, DETRIMENT)

    if profile.fall_sign(body.body_id) == body.sign:
        return Dignity(body.body_id, body.sign, FALL)

    return Dignity(body.body_id, body.sign, PEREGRINE)


def dignities(
    bodies: dict[str, BodyPosition],
    profile: RulershipProfile,
) -> tuple[Dignity, ...]:
    return tuple(dignity_of(body, profile) for body in bodies.values())


def dispositor_chains(
    bodies: dict[str, BodyPosition],
    profile: RulershipProfile,
) -> tuple[DispositorChain, ...]:
    """Walk each body to its final dispositor, or to the loop it falls into.

    The walk is bounded by construction: each step moves to the ruler of the
    current body's sign, there are finitely many bodies, and a repeat is
    detected, so it terminates on every input including a chart that is nothing
    but mutual receptions.
    """
    chains: list[DispositorChain] = []
    for body_id, body in bodies.items():
        if body_id in profile.unrated_bodies:
            continue

        chain: list[str] = []
        seen = [body_id]
        current = body

        while True:
            ruler_id = profile.domicile.get(current.sign)
            if ruler_id is None or ruler_id not in bodies:
                # The chain runs off the end of the chart rather than closing.
                chains.append(DispositorChain(body_id, tuple(chain), None))
                break

            if ruler_id == current.body_id:
                # Self-ruling: a planet in its own sign disposits itself.
                chains.append(DispositorChain(body_id, tuple(chain), ruler_id))
                break

            if ruler_id in seen:
                # Closed loop. Report the members from where it closes, so a
                # mutual reception reads as the pair and not as the path in.
                loop = tuple(seen[seen.index(ruler_id) :])
                chain.append(ruler_id)
                chains.append(
                    DispositorChain(body_id, tuple(chain), None, loop=loop)
                )
                break

            chain.append(ruler_id)
            seen.append(ruler_id)
            current = bodies[ruler_id]

    return tuple(chains)


def final_dispositors(chains: tuple[DispositorChain, ...]) -> tuple[str, ...]:
    """Every planet the chart ultimately answers to, in a stable order.

    Empty is a real and reportable result: a chart whose chains all close in
    loops has no final dispositor, and saying so is the answer.
    """
    return tuple(
        sorted({chain.final_dispositor for chain in chains if chain.final_dispositor})
    )


def mutual_receptions(
    bodies: dict[str, BodyPosition],
    profile: RulershipProfile,
) -> tuple[tuple[str, str], ...]:
    """Pairs where each planet sits in a sign the other rules."""
    pairs: set[tuple[str, str]] = set()
    for body_id, body in bodies.items():
        if body_id in profile.unrated_bodies:
            continue
        other_id = profile.domicile.get(body.sign)
        if other_id is None or other_id == body_id or other_id not in bodies:
            continue
        if profile.domicile.get(bodies[other_id].sign) == body_id:
            pairs.add(tuple(sorted((body_id, other_id))))  # type: ignore[arg-type]
    return tuple(sorted(pairs))


def _house_multiplier(house: int | None, profile: DominantProfile) -> float:
    if house is None:
        return 1.0
    if house in ANGULAR_HOUSES:
        return profile.angular_house_multiplier
    if house in SUCCEDENT_HOUSES:
        return profile.succedent_house_multiplier
    return profile.cadent_house_multiplier


def dominant_planets(
    bodies: dict[str, BodyPosition],
    aspects: tuple[Aspect, ...],
    dignity_by_body: dict[str, str],
    ruling_body: str | None,
    profile: DominantProfile,
) -> tuple[DominantPlanet, ...]:
    """Order the planets of a chart by prominence under a published profile.

    Every component is returned alongside the total, so a caller can see what
    made a planet dominant instead of being handed a number to trust. The
    ordering is a product decision; the tie-break is by body name so two runs
    of the same chart always agree.
    """
    scored: list[tuple[float, str, dict[str, float]]] = []

    for body_id in profile.participating_bodies:
        body = bodies.get(body_id)
        if body is None:
            continue

        components: dict[str, float] = {}
        components["house"] = profile.house_weight * _house_multiplier(
            body.house, profile
        )
        components["sign"] = profile.sign_weight
        components["dignity"] = profile.dignity_weights.get(
            dignity_by_body.get(body_id, UNRATED), 0.0
        )

        aspect_total = 0.0
        for aspect in aspects:
            if aspect.body_a == body_id:
                target = aspect.body_b
            elif aspect.body_b == body_id:
                target = aspect.body_a
            else:
                continue
            aspect_total += profile.aspect_weight_by_type.get(
                aspect.aspect_type, 0.0
            ) * profile.aspect_target_weights.get(
                target, profile.aspect_target_weights.get("default", 1.0)
            )
        components["aspects"] = aspect_total

        components["luminary"] = (
            profile.luminary_bonus if body_id in ("sun", "moon") else 0.0
        )
        components["chartRuler"] = (
            profile.chart_ruler_bonus if body_id == ruling_body else 0.0
        )

        scored.append((sum(components.values()), body_id, components))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return tuple(
        DominantPlanet(body_id=body_id, score=score, rank=rank, components=components)
        for rank, (score, body_id, components) in enumerate(scored, start=1)
    )
