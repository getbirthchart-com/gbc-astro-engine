"""Canonical relationship-chart models (v0.2)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from gbc_astro.models.chart import NatalChart, WarningMessage
from gbc_astro.models.position import AnglePosition, BodyPosition

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

    def to_dict(self) -> dict[str, float | str]:
        return {
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

    def to_dict(self) -> dict[str, float | int | str]:
        return {
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

    def to_dict(self) -> dict[str, float | str]:
        return {
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
        if self.composite_house_method is not None:
            payload["compositeHouseMethod"] = self.composite_house_method
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
    aspects: tuple[Any, ...] = ()
    midpoints: tuple[CompositeMidpoint, ...] = ()
    warnings: tuple[WarningMessage, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "meta": self.meta.to_dict(),
            "bodies": {name: body.to_dict() for name, body in self.bodies.items()},
            "angles": {name: angle.to_dict() for name, angle in self.angles.items()},
            "aspects": [aspect.to_dict() for aspect in self.aspects],
            "midpoints": [midpoint.to_dict() for midpoint in self.midpoints],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)
