"""The relationship timing layer: what is active between two people, and when.

Four kinds of statement, kept apart
-----------------------------------
A transit to A's chart, a transit to B's, a transit to the composite, and a
progressed contact are four different claims about time. Pooling them loses the
only thing that distinguishes a relationship transit from an ordinary one --
whose chart it lands on -- so nothing here is merged and every result carries its
own label.

Activation joins, it does not infer
-----------------------------------
"Transiting Jupiter is conjunct A's Venus" and "A's Venus trines B's Moon" are
two facts sharing a body. Reporting the join is deterministic. Reading meaning
into it is not, and none is read: the activation cites the transit and the
synastry contact and adds nothing of its own, for the same reason ruler
interactions cite rather than mint. The geometry is already counted once.

Progressed comparisons come in three, never pooled
--------------------------------------------------
Progressed A against natal B, natal A against progressed B, and progressed A
against progressed B are three different questions. A list mixing them cannot be
read, so `direction` is mandatory on every contact and the output is grouped by
it.
"""

from __future__ import annotations

from datetime import datetime, timezone

from gbc_astro.aspects.engine import match_aspect_rule
from gbc_astro.astronomy.circular import shortest_angular_distance
from gbc_astro.astronomy.time import isoformat_z
from gbc_astro.constants import ENGINE_NAME, ENGINE_VERSION
from gbc_astro.models.chart import WarningMessage
from gbc_astro.models.forecast import TransitChart
from gbc_astro.models.position import BodyPosition
from gbc_astro.models.relationship import (
    CHART_A,
    CHART_B,
    CompositeChart,
    CompositeTransitContact,
    CompositeTransitResult,
    ProgressedContact,
    ProgressedSynastryResult,
    RelationshipTransitResult,
    SynastryActivation,
    SynastryChart,
)
from gbc_astro.models.transform import TransformedChart
from gbc_astro.profiles.model import AspectProfile
from gbc_astro.profiles.relationship_timing import (
    NATAL_A_TO_PROGRESSED_B,
    PROGRESSED_A_TO_NATAL_B,
    PROGRESSED_A_TO_PROGRESSED_B,
    RelationshipTimingProfile,
)

RELATIONSHIP_TRANSIT_SCHEMA_VERSION = "1.0.0"
COMPOSITE_TRANSIT_SCHEMA_VERSION = "1.0.0"
PROGRESSED_SYNASTRY_SCHEMA_VERSION = "1.0.0"


def _activations_for(
    transits: TransitChart,
    synastry: SynastryChart,
    chart: str,
) -> list[SynastryActivation]:
    """Every synastry contact whose body is currently being transited."""
    found: list[SynastryActivation] = []
    for aspect in transits.transit_to_natal_aspects:
        if aspect.natal_target_kind != "body":
            continue
        for contact in synastry.cross_aspects:
            owned = contact.body_a if chart == CHART_A else contact.body_b
            if owned != aspect.natal_body:
                continue
            found.append(
                SynastryActivation(
                    chart=chart,
                    body=aspect.natal_body,
                    transit_body=aspect.transit_body,
                    transit_aspect=aspect.aspect_type,
                    transit_orb=aspect.orb,
                    transit_evidence_id=aspect.id,
                    synastry_evidence_id=contact.id,
                )
            )
    return found


def calculate_relationship_transits(
    synastry: SynastryChart,
    transits_a: TransitChart,
    transits_b: TransitChart,
    target_instant: datetime,
    profile: RelationshipTimingProfile,
) -> RelationshipTransitResult:
    """Both natal transit charts, kept whole, plus what they activate.

    The two charts are not merged. Which person a transit belongs to is the only
    thing that makes it a relationship transit rather than an ordinary one.
    """
    activations = [
        *_activations_for(transits_a, synastry, CHART_A),
        *_activations_for(transits_b, synastry, CHART_B),
    ]
    # Tightest transit first, then by id so two runs always agree.
    ordered = tuple(
        sorted(activations, key=lambda item: (item.transit_orb, item.id))
    )

    return RelationshipTransitResult(
        schema_version=RELATIONSHIP_TRANSIT_SCHEMA_VERSION,
        meta={
            "engine": ENGINE_NAME,
            "engineVersion": ENGINE_VERSION,
            "timingProfile": profile.id,
            "timingProfileVersion": profile.version,
            "transitProfile": transits_a.meta.get("transitAspectProfile"),
            "synastrySchemaVersion": synastry.schema_version,
            "activationBasis": "shared_body_between_transit_and_synastry_contact",
        },
        target_instant=isoformat_z(target_instant.astimezone(timezone.utc)),
        transits_a=transits_a,
        transits_b=transits_b,
        activations=ordered,
        top_activations=ordered[: profile.top_activations],
        warnings=(
            WarningMessage(
                code="ACTIVATION_IS_A_JOIN_NOT_AN_INFERENCE",
                severity="info",
                message=(
                    "An activation records that a transit and a synastry contact "
                    "share a body. Both are cited and neither is re-derived; no "
                    "meaning is inferred from the join."
                ),
                fields_affected=("activations",),
            ),
        ),
    )


def calculate_composite_transits(
    composite: CompositeChart,
    transiting: dict[str, BodyPosition],
    target_instant: datetime,
    aspect_profile: AspectProfile,
    profile: RelationshipTimingProfile,
) -> CompositeTransitResult:
    """Transiting bodies against the composite positions.

    Composite angles are included only where the composite actually has them,
    which this engine's composite always does because they are derived from the
    midpoint Midheaven rather than averaged. Nothing is invented if they are
    absent.
    """
    contacts: list[CompositeTransitContact] = []
    targets: dict[str, float] = {
        body_id: body.longitude for body_id, body in composite.bodies.items()
    }
    targets.update(
        {name: angle.longitude for name, angle in composite.angles.items()}
    )

    for transit_id, transit_body in sorted(transiting.items()):
        for target_id, target_longitude in sorted(targets.items()):
            separation = shortest_angular_distance(
                transit_body.longitude, target_longitude
            )
            matched = match_aspect_rule(separation, aspect_profile)
            if matched is None:
                continue
            rule, orb = matched
            contacts.append(
                CompositeTransitContact(
                    transit_body=transit_id,
                    composite_body=target_id,
                    aspect_type=rule.aspect_type,
                    exact_angle=rule.exact_angle,
                    actual_angle=separation,
                    orb=orb,
                )
            )

    return CompositeTransitResult(
        schema_version=COMPOSITE_TRANSIT_SCHEMA_VERSION,
        meta={
            "engine": ENGINE_NAME,
            "engineVersion": ENGINE_VERSION,
            "timingProfile": profile.id,
            "timingProfileVersion": profile.version,
            "aspectProfile": aspect_profile.id,
            "compositeSchemaVersion": composite.schema_version,
            "anglesIncluded": bool(composite.angles),
        },
        target_instant=isoformat_z(target_instant.astimezone(timezone.utc)),
        contacts=tuple(sorted(contacts, key=lambda item: (item.id, item.orb))),
    )


def _cross_contacts(
    direction: str,
    bodies_a: dict[str, BodyPosition],
    bodies_b: dict[str, BodyPosition],
    eligible: tuple[str, ...],
    aspect_profile: AspectProfile,
) -> list[ProgressedContact]:
    contacts: list[ProgressedContact] = []
    for body_a_id in eligible:
        body_a = bodies_a.get(body_a_id)
        if body_a is None:
            continue
        for body_b_id in eligible:
            body_b = bodies_b.get(body_b_id)
            if body_b is None:
                continue
            separation = shortest_angular_distance(
                body_a.longitude, body_b.longitude
            )
            matched = match_aspect_rule(separation, aspect_profile)
            if matched is None:
                continue
            rule, orb = matched
            contacts.append(
                ProgressedContact(
                    direction=direction,
                    body_a=body_a_id,
                    body_b=body_b_id,
                    aspect_type=rule.aspect_type,
                    exact_angle=rule.exact_angle,
                    actual_angle=separation,
                    orb=orb,
                )
            )
    return contacts


def calculate_progressed_synastry(
    natal_a_bodies: dict[str, BodyPosition],
    natal_b_bodies: dict[str, BodyPosition],
    progressed_a: TransformedChart,
    progressed_b: TransformedChart,
    target_instant: datetime,
    eligible: tuple[str, ...],
    aspect_profile: AspectProfile,
    profile: RelationshipTimingProfile,
) -> ProgressedSynastryResult:
    """The three progressed comparisons, each labelled and never pooled."""
    contacts: list[ProgressedContact] = []
    sources = {
        PROGRESSED_A_TO_NATAL_B: (progressed_a.bodies, natal_b_bodies),
        NATAL_A_TO_PROGRESSED_B: (natal_a_bodies, progressed_b.bodies),
        PROGRESSED_A_TO_PROGRESSED_B: (progressed_a.bodies, progressed_b.bodies),
    }
    for direction in profile.progressed_directions:
        bodies_a, bodies_b = sources[direction]
        contacts.extend(
            _cross_contacts(direction, bodies_a, bodies_b, eligible, aspect_profile)
        )

    return ProgressedSynastryResult(
        schema_version=PROGRESSED_SYNASTRY_SCHEMA_VERSION,
        meta={
            "engine": ENGINE_NAME,
            "engineVersion": ENGINE_VERSION,
            "timingProfile": profile.id,
            "timingProfileVersion": profile.version,
            "aspectProfile": aspect_profile.id,
            "progressionProfile": progressed_a.meta.get("progressionProfile"),
            "progressedInstantA": progressed_a.meta.get("progressedInstant"),
            "progressedInstantB": progressed_b.meta.get("progressedInstant"),
            "directions": list(profile.progressed_directions),
        },
        target_instant=isoformat_z(target_instant.astimezone(timezone.utc)),
        contacts=tuple(sorted(contacts, key=lambda item: item.id)),
        warnings=(
            WarningMessage(
                code="PROGRESSED_DIRECTIONS_ARE_DISTINCT",
                severity="info",
                message=(
                    "Progressed A to natal B, natal A to progressed B and "
                    "progressed A to progressed B are three different questions "
                    "about three different moments. They are grouped by "
                    "direction and must not be pooled."
                ),
                fields_affected=("byDirection",),
            ),
        ),
    )
