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

