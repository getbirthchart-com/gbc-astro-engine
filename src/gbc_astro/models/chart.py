"""Canonical chart result models."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from gbc_astro.models.aspect import Aspect
from gbc_astro.models.position import AnglePosition, BodyPosition, HouseCusp
from gbc_astro.models.rulership import (
    Dignity,
    DispositorChain,
    DominantPlanet,
    HouseRuler,
    RulerPlacement,
)


@dataclass(frozen=True)
class WarningMessage:
    code: str
    severity: str
    message: str
    fields_affected: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "fieldsAffected": list(self.fields_affected),
        }


@dataclass(frozen=True)
class ChartMeta:
    schema_version: str
    engine: str
    engine_version: str
    ephemeris_provider: str
    ephemeris_data_version: str
    timezone_data_version: str
    calculation_profile: str
    house_system: str | None
    aspect_profile: str
    zodiac: str
    house_algorithm_version: str | None
    ayanamsa: str | None = None
    ayanamsa_version: str | None = None
    ayanamsa_degrees: float | None = None
    rulership_profile: str | None = None
    rulership_profile_version: str | None = None
    dominant_profile: str | None = None
    dominant_profile_version: str | None = None

    def to_dict(self) -> dict[str, str | float | None]:
        return {
            "engine": self.engine,
            "engineVersion": self.engine_version,
            "ephemerisProvider": self.ephemeris_provider,
            "ephemerisDataVersion": self.ephemeris_data_version,
            "timezoneDataVersion": self.timezone_data_version,
            "calculationProfile": self.calculation_profile,
            "houseSystem": self.house_system,
            "aspectProfile": self.aspect_profile,
            "zodiac": self.zodiac,
            "houseAlgorithmVersion": self.house_algorithm_version,
            "rulershipProfile": self.rulership_profile,
            "rulershipProfileVersion": self.rulership_profile_version,
            "dominantProfile": self.dominant_profile,
            "dominantProfileVersion": self.dominant_profile_version,
            **(
                {
                    "ayanamsa": self.ayanamsa,
                    "ayanamsaVersion": self.ayanamsa_version,
                    "ayanamsaDegrees": self.ayanamsa_degrees,
                }
                if self.ayanamsa is not None
                else {}
            ),
        }


@dataclass(frozen=True)
class ChartSubject:
    local_datetime: str
    timezone: str
    utc_datetime: str
    julian_day: float
    latitude: float
    longitude: float
    altitude_m: float | None
    birth_time_known: bool
    calendar: str = "gregorian"

    def to_dict(self) -> dict[str, float | str | bool | None]:
        return {
            "localDateTime": self.local_datetime,
            "timezone": self.timezone,
            "utcDateTime": self.utc_datetime,
            "julianDay": self.julian_day,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitudeM": self.altitude_m,
            "birthTimeKnown": self.birth_time_known,
            "calendar": self.calendar,
        }


@dataclass(frozen=True)
class MoonPhase:
    phase_angle: float
    name: str
    waxing: bool | None

    def to_dict(self) -> dict[str, float | str | bool | None]:
        return {
            "phaseAngle": self.phase_angle,
            "name": self.name,
            "waxing": self.waxing,
        }


@dataclass(frozen=True)
class DerivedNatal:
    big_three: dict[str, str | None] = field(default_factory=dict)
    moon_phase: MoonPhase | None = None
    elements: dict[str, int] = field(default_factory=dict)
    modalities: dict[str, int] = field(default_factory=dict)
    polarities: dict[str, int] = field(default_factory=dict)
    hemispheres: dict[str, int] = field(default_factory=dict)
    quadrants: dict[str, int] = field(default_factory=dict)
    # Rulership-derived. All of it is a function of the signs above plus the
    # rulership table the profile names, and none of it touches an ephemeris.
    chart_ruler: RulerPlacement | None = None
    house_rulers: tuple[HouseRuler, ...] = ()
    dignities: tuple[Dignity, ...] = ()
    dispositors: tuple[DispositorChain, ...] = ()
    final_dispositors: tuple[str, ...] = ()
    mutual_receptions: tuple[tuple[str, str], ...] = ()
    dominant_planets: tuple[DominantPlanet, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "bigThree": self.big_three,
            "moonPhase": self.moon_phase.to_dict() if self.moon_phase else {},
            "elements": self.elements,
            "modalities": self.modalities,
            "polarities": self.polarities,
            "hemispheres": self.hemispheres,
            "quadrants": self.quadrants,
            "chartRuler": self.chart_ruler.to_dict() if self.chart_ruler else None,
            "houseRulers": [ruler.to_dict() for ruler in self.house_rulers],
            "dignities": [dignity.to_dict() for dignity in self.dignities],
            "dispositors": [chain.to_dict() for chain in self.dispositors],
            "finalDispositors": list(self.final_dispositors),
            "mutualReceptions": [list(pair) for pair in self.mutual_receptions],
            "dominantPlanets": [planet.to_dict() for planet in self.dominant_planets],
        }


@dataclass(frozen=True)
class NatalChart:
    schema_version: str
    meta: ChartMeta
    subject: ChartSubject
    angles: dict[str, AnglePosition]
    bodies: dict[str, BodyPosition]
    houses: tuple[HouseCusp, ...]
    aspects: tuple[Aspect, ...]
    derived: DerivedNatal
    warnings: tuple[WarningMessage, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "meta": self.meta.to_dict(),
            "subject": self.subject.to_dict(),
            "angles": {name: angle.to_dict() for name, angle in self.angles.items()},
            "bodies": {name: body.to_dict() for name, body in self.bodies.items()},
            "houses": [house.to_dict() for house in self.houses],
            "aspects": [aspect.to_dict() for aspect in self.aspects],
            "derived": self.derived.to_dict(),
            "warnings": [warning.to_dict() for warning in self.warnings],
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

