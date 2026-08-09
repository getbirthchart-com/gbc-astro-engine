"""Canonical relationship-chart models (v0.2)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from gbc_astro.models.chart import NatalChart, WarningMessage
from gbc_astro.models.position import AnglePosition, BodyPosition, HouseCusp

CHART_A = "A"
CHART_B = "B"


@dataclass(frozen=True)
class CrossAspect:
    """An aspect between a body in one chart and a body in the other.

    `phase` is always `indeterminate`. Applying and separating describe two
    bodies converging or parting along a shared timeline; two natal charts are
    two frozen instants belonging to different people, so there is no such
    timeline. Reusing the natal speeds here would produce a number that looks
    physical and is not, so the field records that the question does not apply.
    """

    body_a: str
    body_b: str
    aspect_type: str
    exact_angle: float
    actual_angle: float
    orb: float
    phase: str = "indeterminate"

    @property
    def id(self) -> str:
        """Deterministic, derived only from whose body aspects whose.

        A and B are part of the identity and never collapse: `a.sun.trine.b.moon`
        and `a.moon.trine.b.sun` are two different facts about two different
        people, and a caller keying interpretation or user state off the id has
        to be able to tell them apart.

        The orb and the profile are deliberately absent. Orbs move when a
        profile version changes, and an id that changed with them could not be
        referenced by a stored result. Which profile produced the contact is
        already in the result's provenance.
        """
        return f"synastry.cross.a.{self.body_a}.{self.aspect_type}.b.{self.body_b}"

    def to_dict(self) -> dict[str, float | str]:
        return {
            "id": self.id,
            "a": self.body_a,
            "b": self.body_b,
            "type": self.aspect_type,
            "exactAngle": self.exact_angle,
            "actualAngle": self.actual_angle,
            "orb": self.orb,
            "phase": self.phase,
        }


@dataclass(frozen=True)
class HouseOverlay:
    """Where one chart's body falls among the other chart's houses."""

    body: str
    body_chart: str
    house_chart: str
    house: int
    body_longitude: float

    @property
    def id(self) -> str:
        """Direction is the fact here, so it is the first thing in the id.

        A's Sun in B's seventh house and B's Sun in A's seventh house are
        different statements about different people, and an overlay that
        flattened them would say neither.
        """
        return (
            f"synastry.overlay.{self.body_chart.lower()}.{self.body}"
            f".in.{self.house_chart.lower()}.house_{self.house}"
        )

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            "id": self.id,
            "body": self.body,
            "bodyChart": self.body_chart,
            "houseChart": self.house_chart,
            "house": self.house,
            "bodyLongitude": self.body_longitude,
        }


@dataclass(frozen=True)
class AngleInteraction:
    """An aspect between a body in one chart and an angle in the other."""

    body: str
    body_chart: str
    angle: str
    angle_chart: str
    aspect_type: str
    exact_angle: float
    actual_angle: float
    orb: float

    @property
    def id(self) -> str:
        return (
            f"synastry.angle.{self.body_chart.lower()}.{self.body}"
            f".{self.aspect_type}.{self.angle_chart.lower()}.{self.angle}"
        )

    def to_dict(self) -> dict[str, float | str]:
        return {
            "id": self.id,
            "body": self.body,
            "bodyChart": self.body_chart,
            "angle": self.angle,
            "angleChart": self.angle_chart,
            "type": self.aspect_type,
            "exactAngle": self.exact_angle,
            "actualAngle": self.actual_angle,
            "orb": self.orb,
        }


@dataclass(frozen=True)
class RelationshipPattern:
    """A named configuration between two charts.

    Discrete where a dimension score is continuous: present or absent, with the
    contacts it rests on named. Not scored -- every contact behind it is already
    scored once as itself, and scoring the pattern too would count the same
    geometry a second time for having been noticed.
    """

    pattern_type: str
    members: tuple[str, ...]
    evidence_ids: tuple[str, ...] = ()
    detail: dict[str, Any] = field(default_factory=dict)
    scored: bool = False

    @property
    def id(self) -> str:
        return f"synastry.pattern.{self.pattern_type}." + ".".join(self.members)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.pattern_type,
            "members": list(self.members),
            "evidenceIds": list(self.evidence_ids),
            "detail": self.detail,
            "scored": self.scored,
        }


@dataclass(frozen=True)
class PointContact:
    """A derived point of one chart aspecting a body of the other.

    Reported, never scored. Weighting the vertex and the Lot of Fortune against
    the planets would need another table of editorial numbers with nothing to
    validate it against, so `scored` is published as false rather than left to
    be inferred.
    """

    point: str
    point_chart: str
    body: str
    body_chart: str
    aspect_type: str
    exact_angle: float
    actual_angle: float
    orb: float
    scored: bool = False

    @property
    def id(self) -> str:
        return (
            f"synastry.point.{self.point_chart.lower()}.{self.point}"
            f".{self.aspect_type}.{self.body_chart.lower()}.{self.body}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "point": self.point,
            "pointChart": self.point_chart,
            "body": self.body,
            "bodyChart": self.body_chart,
            "type": self.aspect_type,
            "exactAngle": self.exact_angle,
            "actualAngle": self.actual_angle,
            "orb": self.orb,
            "scored": self.scored,
        }


@dataclass(frozen=True)
class RulerInteraction:
    """A house ruler of one chart meeting something in the other.

    Not a new contact. If Mercury rules A's seventh house, "A's seventh ruler
    conjunct B's Venus" *is* the cross aspect `a.mercury.conjunction.b.venus`,
    which is already in the result and already scored. `evidence_id` points at
    that fact rather than minting a second one, so the same geometry cannot
    enter the scoring twice.
    """

    direction: str
    house: int
    ruler: str
    kind: str
    target: str
    evidence_id: str
    aspect_type: str | None = None
    orb: float | None = None

    @property
    def id(self) -> str:
        source = self.direction.split("_")[0].lower()
        target = self.direction.split("_")[-1].lower()
        detail = self.aspect_type or "in"
        return (
            f"synastry.ruler.{source}.house_{self.house}.{self.ruler}"
            f".{detail}.{target}.{self.target}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "direction": self.direction,
            "house": self.house,
            "ruler": self.ruler,
            "kind": self.kind,
            "target": self.target,
            "type": self.aspect_type,
            "orb": self.orb,
            "evidenceId": self.evidence_id,
        }


@dataclass(frozen=True)
class DirectionalTheme:
    """Which way a group of directional facts runs, and what they touch.

    Built from house overlays and angle contacts only. A cross aspect is a
    mutual relation with no direction of influence, and grouping one here would
    assert a direction the geometry does not have.
    """

    direction: str
    theme: str
    contact_count: int
    evidence_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "theme": self.theme,
            "contactCount": self.contact_count,
            "evidenceIds": list(self.evidence_ids),
        }


@dataclass(frozen=True)
class RelationshipMeta:
    schema_version: str
    engine: str
    engine_version: str
    relationship_profile: str
    aspect_profile: str
    zodiac: str
    chart_a_schema_version: str
    chart_b_schema_version: str
    composite_position_method: str | None = None
    composite_angle_method: str | None = None
    composite_house_method: str | None = None
    composite_house_system: str | None = None
    composite_reference_latitude_method: str | None = None
    composite_obliquity_epoch: str | None = None
    davison_location_method: str | None = None
    cross_aspect_phase_policy: str | None = None
    house_algorithm_version: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        payload: dict[str, str | None] = {
            "engine": self.engine,
            "engineVersion": self.engine_version,
            "relationshipProfile": self.relationship_profile,
            "aspectProfile": self.aspect_profile,
            "zodiac": self.zodiac,
            "chartASchemaVersion": self.chart_a_schema_version,
            "chartBSchemaVersion": self.chart_b_schema_version,
        }
        if self.composite_position_method is not None:
            payload["compositePositionMethod"] = self.composite_position_method
        if self.composite_angle_method is not None:
            payload["compositeAngleMethod"] = self.composite_angle_method
        for key, value in (
            ("compositeHouseMethod", self.composite_house_method),
            ("compositeHouseSystem", self.composite_house_system),
            ("compositeReferenceLatitudeMethod", self.composite_reference_latitude_method),
            ("compositeObliquityEpoch", self.composite_obliquity_epoch),
            ("davisonLocationMethod", self.davison_location_method),
            ("crossAspectPhasePolicy", self.cross_aspect_phase_policy),
            ("houseAlgorithmVersion", self.house_algorithm_version),
        ):
            if value is not None:
                payload[key] = value
        return payload


@dataclass(frozen=True)
class SynastryChart:
    schema_version: str
    meta: RelationshipMeta
    chart_a: NatalChart
    chart_b: NatalChart
    cross_aspects: tuple[CrossAspect, ...] = ()
    a_bodies_in_b_houses: tuple[HouseOverlay, ...] = ()
    b_bodies_in_a_houses: tuple[HouseOverlay, ...] = ()
    angle_interactions: tuple[AngleInteraction, ...] = ()
    point_contacts: tuple[PointContact, ...] = ()
    patterns: tuple[RelationshipPattern, ...] = ()
    ruler_interactions: tuple[RulerInteraction, ...] = ()
    directional_themes: tuple[DirectionalTheme, ...] = ()
    warnings: tuple[WarningMessage, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "meta": self.meta.to_dict(),
            "chartA": self.chart_a.to_dict(),
            "chartB": self.chart_b.to_dict(),
            "crossAspects": [aspect.to_dict() for aspect in self.cross_aspects],
            "aBodiesInBHouses": [overlay.to_dict() for overlay in self.a_bodies_in_b_houses],
            "bBodiesInAHouses": [overlay.to_dict() for overlay in self.b_bodies_in_a_houses],
            "angleInteractions": [
                interaction.to_dict() for interaction in self.angle_interactions
            ],
            "pointContacts": [contact.to_dict() for contact in self.point_contacts],
            "patterns": [pattern.to_dict() for pattern in self.patterns],
            "rulerInteractions": [
                interaction.to_dict() for interaction in self.ruler_interactions
            ],
            "directionalThemes": [
                theme.to_dict() for theme in self.directional_themes
            ],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


@dataclass(frozen=True)
class CompositeMidpoint:
    """A composite position, with the ambiguity of its construction recorded."""

    body_id: str
    longitude_a: float
    longitude_b: float
    separation: float
    ambiguous: bool

    def to_dict(self) -> dict[str, float | str | bool]:
        return {
            "bodyId": self.body_id,
            "longitudeA": self.longitude_a,
            "longitudeB": self.longitude_b,
            "separation": self.separation,
            "ambiguous": self.ambiguous,
        }


@dataclass(frozen=True)
class CompositeChart:
    schema_version: str
    meta: RelationshipMeta
    bodies: dict[str, BodyPosition]
    angles: dict[str, AnglePosition] = field(default_factory=dict)
    houses: tuple[HouseCusp, ...] = ()
    aspects: tuple[Any, ...] = ()
    midpoints: tuple[CompositeMidpoint, ...] = ()
    warnings: tuple[WarningMessage, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "meta": self.meta.to_dict(),
            "bodies": {name: body.to_dict() for name, body in self.bodies.items()},
            "angles": {name: angle.to_dict() for name, angle in self.angles.items()},
            "houses": [house.to_dict() for house in self.houses],
            "aspects": [aspect.to_dict() for aspect in self.aspects],
            "midpoints": [midpoint.to_dict() for midpoint in self.midpoints],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


@dataclass(frozen=True)
class DavisonChart:
    """A real chart for the midpoint moment and midpoint place of two births.

    Unlike a composite, this is an actual instant at an actual location, so it
    carries genuine speeds, retrograde states, houses and angles, and its
    aspects have meaningful applying and separating phases. It is the physically
    grounded answer to the questions a midpoint composite can only approximate.
    """

    schema_version: str
    meta: RelationshipMeta
    chart: NatalChart
    derived_utc_datetime: str
    derived_latitude: float
    derived_longitude: float
    warnings: tuple[WarningMessage, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "meta": self.meta.to_dict(),
            "derivedFrom": {
                "utcDateTime": self.derived_utc_datetime,
                "latitude": self.derived_latitude,
                "longitude": self.derived_longitude,
            },
            "chart": self.chart.to_dict(),
            "warnings": [warning.to_dict() for warning in self.warnings],
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


@dataclass(frozen=True)
class ScoreContribution:
    """One scored contact, with every factor that produced it kept visible."""

    kind: str
    # The synastry fact this line scores, by its canonical id. The roadmap's
    # evidence rule turns on this: no score may exist that cannot be taken apart
    # into contacts a caller can look up.
    evidence_id: str
    subject_a: str
    subject_b: str
    aspect_type: str
    orb: float
    aspect_weight: float
    pair_weight: float
    orb_factor: float
    value: float
    # Which dimensions this contact speaks to, and what it contributed to each.
    # Empty when the bodies involved are mapped to no dimension, which is a
    # statement rather than an oversight -- see `profiles.dimensions`.
    dimension_values: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "evidenceId": self.evidence_id,
            "a": self.subject_a,
            "b": self.subject_b,
            "type": self.aspect_type,
            "orb": self.orb,
            "aspectWeight": self.aspect_weight,
            "pairWeight": self.pair_weight,
            "orbFactor": self.orb_factor,
            "value": self.value,
            "dimensionValues": dict(self.dimension_values),
        }


@dataclass(frozen=True)
class DimensionScore:
    """One dimension, its two signals, and the contacts they came from.

    `supportive` and `challenging` are kept apart rather than netted. A pair
    with strong attraction and strong friction in the same dimension is not the
    same as a pair with neither, and a single net figure cannot tell them apart.

    `contact_count` is the coverage signal. A dimension with no contacts is not
    a zero: zero means the geometry is neutral, absent means it is silent, and a
    pair with an unknown birth time is silent about everything the angles would
    have said.
    """

    dimension: str
    supportive: float
    challenging: float
    activity: float
    contact_count: int
    # The relationship-type multiplier already folded into the numbers above,
    # published so a caller can see it without dividing it back out.
    profile_weight: float = 1.0
    evidence_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "supportive": self.supportive,
            "challenging": self.challenging,
            "activity": self.activity,
            "contactCount": self.contact_count,
            "profileWeight": self.profile_weight,
            "evidenceIds": list(self.evidence_ids),
        }


@dataclass(frozen=True)
class RankedContact:
    """One contact selected for the strengths or challenges list.

    Carries its evidence id, so it can be looked up in the synastry result, and
    the two numbers behind its position: the raw contribution value and the
    diversity-adjusted basis it was actually ranked on. Publishing both is what
    keeps a surprising order explainable -- a strong contact placed low was
    demoted for repeating a dimension, and the numbers show it.
    """

    rank: int
    evidence_id: str
    kind: str
    subject_a: str
    subject_b: str
    aspect_type: str
    orb: float
    value: float
    dimensions: tuple[str, ...]
    selection_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "evidenceId": self.evidence_id,
            "kind": self.kind,
            "a": self.subject_a,
            "b": self.subject_b,
            "type": self.aspect_type,
            "orb": self.orb,
            "value": self.value,
            "dimensions": list(self.dimensions),
            "selectionScore": self.selection_score,
        }


@dataclass(frozen=True)
class RelationshipScore:
    """A profile-scoped relationship score, reported as three totals.

    Deliberately not a percentage: a percentage implies an absolute scale, and
    there is no defensible answer to what one hundred percent would mean.
    """

    schema_version: str
    engine: str
    engine_version: str
    scoring_profile: str
    scoring_profile_version: str
    supportive: float
    challenging: float
    activity: float
    balance: float
    activity_band: str | None
    balance_band: str | None
    contribution_count: int
    contributions: tuple[ScoreContribution, ...] = ()
    dimensions: tuple[DimensionScore, ...] = ()
    dimension_profile: str | None = None
    dimension_profile_version: str | None = None
    relationship_type: str | None = None
    relationship_type_version: str | None = None
    ranking_profile: str | None = None
    ranking_profile_version: str | None = None
    top_strengths: tuple[RankedContact, ...] = ()
    top_challenges: tuple[RankedContact, ...] = ()
    profile_detail: dict[str, Any] = field(default_factory=dict)
    dimension_profile_detail: dict[str, Any] = field(default_factory=dict)
    relationship_type_detail: dict[str, Any] = field(default_factory=dict)
    ranking_profile_detail: dict[str, Any] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "meta": {
                "engine": self.engine,
                "engineVersion": self.engine_version,
                "scoringProfile": self.scoring_profile,
                "scoringProfileVersion": self.scoring_profile_version,
                "dimensionProfile": self.dimension_profile,
                "dimensionProfileVersion": self.dimension_profile_version,
                "relationshipType": self.relationship_type,
                "relationshipTypeVersion": self.relationship_type_version,
                "rankingProfile": self.ranking_profile,
                "rankingProfileVersion": self.ranking_profile_version,
            },
            "dimensions": [dimension.to_dict() for dimension in self.dimensions],
            "dimensionProfile": self.dimension_profile_detail,
            "relationshipTypeProfile": self.relationship_type_detail,
            "rankingProfile": self.ranking_profile_detail,
            "topStrengths": [contact.to_dict() for contact in self.top_strengths],
            "topChallenges": [contact.to_dict() for contact in self.top_challenges],
            "totals": {
                "supportive": self.supportive,
                "challenging": self.challenging,
                "activity": self.activity,
                "balance": self.balance,
                "activityBand": self.activity_band,
                "balanceBand": self.balance_band,
            },
            "contributionCount": self.contribution_count,
            "contributions": [item.to_dict() for item in self.contributions],
            "profile": self.profile_detail,
            "notes": list(self.notes),
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)
