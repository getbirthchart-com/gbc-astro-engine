"""Canonical forecast models (v0.3): transits, events and returns."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from gbc_astro.models.chart import NatalChart, WarningMessage
from gbc_astro.models.position import BodyPosition


@dataclass(frozen=True)
class TransitAspect:
    """An aspect between a moving transit body and a fixed natal point.

    Unlike a synastry cross aspect, `phase` here is real. A transit chart has a
    genuine shared timeline: the transiting body is moving and the natal point
    is not, so applying and separating describe something that is actually
    happening rather than a convention.
    """

    transit_body: str
    natal_body: str
    aspect_type: str
    exact_angle: float
    actual_angle: float
    orb: float
    phase: str

    def to_dict(self) -> dict[str, float | str]:
        return {
            "transitBody": self.transit_body,
            "natalBody": self.natal_body,
            "type": self.aspect_type,
            "exactAngle": self.exact_angle,
            "actualAngle": self.actual_angle,
            "orb": self.orb,
            "phase": self.phase,
        }


@dataclass(frozen=True)
class TransitHousePlacement:
    transit_body: str
    natal_house: int
    longitude: float

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            "transitBody": self.transit_body,
            "natalHouse": self.natal_house,
            "longitude": self.longitude,
        }


@dataclass(frozen=True)
class TransitChart:
    schema_version: str
    meta: dict[str, Any]
    target_instant: str
    transit_bodies: dict[str, BodyPosition]
    transit_to_natal_aspects: tuple[TransitAspect, ...] = ()
    transit_house_placements: tuple[TransitHousePlacement, ...] = ()
    natal_chart: NatalChart | None = None
    warnings: tuple[WarningMessage, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "meta": self.meta,
            "targetInstant": self.target_instant,
            "transitBodies": {
                name: body.to_dict() for name, body in self.transit_bodies.items()
            },
            "transitToNatalAspects": [
                aspect.to_dict() for aspect in self.transit_to_natal_aspects
            ],
            "transitHousePlacements": [
                placement.to_dict() for placement in self.transit_house_placements
            ],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


@dataclass(frozen=True)
class EventSearchResult:
    """Events located by the numerical solver, with the query that produced them."""

    schema_version: str
    meta: dict[str, Any]
    query: dict[str, Any]
    events: tuple[Any, ...] = ()
    warnings: tuple[WarningMessage, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "meta": self.meta,
            "query": self.query,
            "eventCount": len(self.events),
            "events": [event.to_dict() for event in self.events],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


@dataclass(frozen=True)
class ReturnHit:
    """One exact return, and the chart cast for it.

    Retrograde motion means a return is often not a single moment. Saturn
    commonly returns three times over several months, and every one of them is
    exact. They are all reported, in order, rather than reduced to the first.
    """

    ordinal: int
    instant_utc: str
    julian_day: float
    longitude: float
    direction: str
    precision_seconds: float
    chart: NatalChart | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "instantUtc": self.instant_utc,
            "julianDay": self.julian_day,
            "longitude": self.longitude,
            "direction": self.direction,
            "precisionSeconds": self.precision_seconds,
            "chart": self.chart.to_dict() if self.chart else None,
        }


@dataclass(frozen=True)
class ReturnSearchResult:
    schema_version: str
    meta: dict[str, Any]
    body: str
    natal_longitude: float
    window_start: str
    window_end: str
    hits: tuple[ReturnHit, ...] = ()
    warnings: tuple[WarningMessage, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "meta": self.meta,
            "body": self.body,
            "natalLongitude": self.natal_longitude,
            "window": {"start": self.window_start, "end": self.window_end},
            "hitCount": len(self.hits),
            "hits": [hit.to_dict() for hit in self.hits],
            "warnings": [warning.to_dict() for warning in self.warnings],
            "notes": list(self.notes),
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)
