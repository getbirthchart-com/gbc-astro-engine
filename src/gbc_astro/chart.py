"""Small natal-chart facade over the existing calculation engine.

This module does not change planetary, house, or aspect math. It validates
public inputs and delegates to `AstrologyEngine.natal`.
"""

from __future__ import annotations

import re
from datetime import date as date_cls, time as time_cls

from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.engine import AstrologyEngine
from gbc_astro.errors import (
    InvalidDateError,
    InvalidTimeError,
    MissingBirthTimeError,
    UnsupportedHouseSystemError,
)
from gbc_astro.houses.systems import HOUSE_SYSTEMS, SUPPORTED_HOUSE_SYSTEMS
from gbc_astro.models.aspect import Aspect
from gbc_astro.models.chart import NatalChart
from gbc_astro.models.position import BodyPosition, HouseCusp
from gbc_astro.zodiac.tropical import longitude_to_tropical

_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$")


def normalize_angle(value: float) -> float:
    """Normalize a longitude or azimuth to the half-open range [0, 360)."""

    return normalize_longitude(value)


def get_zodiac_sign(longitude: float) -> str:
    """Return the tropical zodiac sign for an ecliptic longitude in degrees."""

    return longitude_to_tropical(longitude).sign


def calculate_chart(
    date: str,
    time: str | None = None,
    *,
    latitude: float,
    longitude: float,
    timezone: str,
    house_system: str = "placidus",
    fold: int | None = None,
    engine: AstrologyEngine | None = None,
) -> NatalChart:
    """Calculate a natal chart from civil date, optional time, and coordinates.

    If `time` is omitted, the chart is an unknown-birth-time calculation:
    bodies are computed at local date start, and Ascendant, Midheaven, and
    houses are omitted. Unknown time is never replaced with noon.
    """

    civil_date = _parse_date(date)
    unknown_time = time is None or str(time).strip() == ""
    if unknown_time:
        local_datetime = civil_date.isoformat()
    else:
        parsed_time = _parse_time(str(time))
        local_datetime = (
            f"{civil_date.isoformat()}T{parsed_time.hour:02d}:{parsed_time.minute:02d}:"
            f"{parsed_time.second:02d}"
        )

    system = _require_house_system(house_system)
    calc = engine or AstrologyEngine()
    return calc.natal(
        local_datetime=local_datetime,
        timezone=timezone,
        latitude=latitude,
        longitude=longitude,
        house_system=system,
        unknown_time=unknown_time,
        fold=fold,
    )


def calculate_planet_positions(
    date: str,
    time: str | None = None,
    *,
    latitude: float,
    longitude: float,
    timezone: str,
    house_system: str = "placidus",
    fold: int | None = None,
    engine: AstrologyEngine | None = None,
) -> dict[str, BodyPosition]:
    """Return natal body positions. Houses on bodies are null when time is unknown."""

    return calculate_chart(
        date,
        time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        house_system=house_system,
        fold=fold,
        engine=engine,
    ).bodies


def calculate_houses(
    date: str,
    time: str | None = None,
    *,
    latitude: float,
    longitude: float,
    timezone: str,
    house_system: str = "placidus",
    fold: int | None = None,
    engine: AstrologyEngine | None = None,
) -> tuple[HouseCusp, ...]:
    """Return house cusps for a known birth time.

    Raises `MissingBirthTimeError` rather than inventing a clock time.
    """

    if time is None or str(time).strip() == "":
        raise MissingBirthTimeError(
            "House cusps require a known birth time. No substitute time was used.",
            {"fieldsAffected": ["houses", "angles"]},
        )
    return calculate_chart(
        date,
        time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        house_system=house_system,
        fold=fold,
        engine=engine,
    ).houses


def calculate_aspects(
    date: str,
    time: str | None = None,
    *,
    latitude: float,
    longitude: float,
    timezone: str,
    house_system: str = "placidus",
    fold: int | None = None,
    engine: AstrologyEngine | None = None,
) -> tuple[Aspect, ...]:
    """Return natal aspects. Moon aspects use the same instant as other bodies."""

    return calculate_chart(
        date,
        time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        house_system=house_system,
        fold=fold,
        engine=engine,
    ).aspects


def _parse_date(value: str) -> date_cls:
    if not isinstance(value, str):
        raise InvalidDateError(
            "Date must be a YYYY-MM-DD string.",
            {"date": value},
        )
    match = _DATE_RE.fullmatch(value.strip())
    if match is None:
        raise InvalidDateError(
            "Date must be a real calendar date in YYYY-MM-DD format.",
            {"date": value},
        )
    year, month, day = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    try:
        return date_cls(year, month, day)
    except ValueError as exc:
        raise InvalidDateError(
            "Date is not a valid calendar date.",
            {"date": value},
        ) from exc


def _parse_time(value: str) -> time_cls:
    match = _TIME_RE.fullmatch(value.strip())
    if match is None:
        raise InvalidTimeError(
            "Time must be HH:MM or HH:MM:SS.",
            {"time": value},
        )
    hour = int(match.group(1))
    minute = int(match.group(2))
    second = int(match.group(3) or 0)
    try:
        return time_cls(hour, minute, second)
    except ValueError as exc:
        raise InvalidTimeError(
            "Time is not a valid clock time.",
            {"time": value},
        ) from exc


def _require_house_system(house_system: str) -> str:
    if not isinstance(house_system, str) or not house_system.strip():
        raise UnsupportedHouseSystemError(
            "Unsupported house system.",
            {
                "houseSystem": house_system,
                "supported": list(SUPPORTED_HOUSE_SYSTEMS),
            },
        )
    system = house_system.strip().lower()
    if system not in HOUSE_SYSTEMS:
        raise UnsupportedHouseSystemError(
            "Unsupported house system.",
            {
                "houseSystem": system,
                "supported": list(SUPPORTED_HOUSE_SYSTEMS),
            },
        )
    return system
