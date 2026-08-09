"""Position value objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ZodiacPosition:
    longitude: float
    sign: str
    degree_in_sign: float

    def to_dict(self) -> dict[str, float | str]:
        return {
            "longitude": self.longitude,
            "sign": self.sign,
            "degreeInSign": self.degree_in_sign,
        }


@dataclass(frozen=True)
class RawBodyPosition:
    longitude_deg: float
    latitude_deg: float
    distance: float | None
    longitude_speed_deg_per_day: float | None


@dataclass(frozen=True)
class BodyPosition:
    body_id: str
    longitude: float
    latitude: float
    distance: float | None
    speed_longitude: float | None
    retrograde: bool | None
    sign: str
    degree_in_sign: float
    house: int | None

    def to_dict(self) -> dict[str, float | int | str | bool | None]:
        return {
            "longitude": self.longitude,
            "latitude": self.latitude,
            "distance": self.distance,
            "speedLongitude": self.speed_longitude,
            "retrograde": self.retrograde,
            "sign": self.sign,
            "degreeInSign": self.degree_in_sign,
            "house": self.house,
        }


@dataclass(frozen=True)
class AnglePosition:
    longitude: float
    sign: str
    degree_in_sign: float

    def to_dict(self) -> dict[str, float | str]:
        return {
            "longitude": self.longitude,
            "sign": self.sign,
            "degreeInSign": self.degree_in_sign,
        }


@dataclass(frozen=True)
class HouseCusp:
    number: int
    cusp_longitude: float
    sign: str
    degree_in_sign: float

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            "number": self.number,
            "cuspLongitude": self.cusp_longitude,
            "sign": self.sign,
            "degreeInSign": self.degree_in_sign,
        }



@dataclass(frozen=True)
class DerivedPoint:
    """A position derived from the chart rather than looked up in an ephemeris.

    `alternative_longitude` is populated only where a real convention dispute
    changed the answer -- currently the Part of Fortune in a night chart. It is
    not a margin of error; it is where the other school would have put the same
    point, published so that a difference against another program reads as a
    documented choice rather than as a defect.
    """

    point_id: str
    longitude: float
    sign: str
    degree_in_sign: float
    house: int | None
    method: str
    requires_birth_time: bool
    alternative_longitude: float | None = None

    def to_dict(self) -> dict[str, float | int | str | bool | None]:
        return {
            "longitude": self.longitude,
            "sign": self.sign,
            "degreeInSign": self.degree_in_sign,
            "house": self.house,
            "method": self.method,
            "requiresBirthTime": self.requires_birth_time,
            "alternativeLongitude": self.alternative_longitude,
        }
