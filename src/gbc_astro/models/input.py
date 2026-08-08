"""Input models and validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from gbc_astro.errors import InvalidCoordinateError, UnknownBirthTimeError


def parse_local_datetime(value: str | datetime | date, unknown_time: bool = False) -> datetime:
    """Parse public local datetime input without assigning a timezone."""

    if isinstance(value, datetime):
        local_dt = value
    elif isinstance(value, date):
        local_dt = datetime.combine(value, time.min)
    else:
        raw = value.strip()
        if unknown_time and "T" not in raw and len(raw) == 10:
            local_dt = datetime.combine(date.fromisoformat(raw), time.min)
        else:
            local_dt = datetime.fromisoformat(raw)
    if local_dt.tzinfo is not None:
        raise ValueError("local_datetime must be timezone-naive; pass timezone separately.")
    return local_dt


@dataclass(frozen=True)
class ChartInput:
    local_datetime: datetime
    timezone: str
    latitude: float
    longitude: float
    altitude_m: float | None = None
    birth_time_known: bool = True
    fold: int | None = None

    def __post_init__(self) -> None:
        if not -90 <= self.latitude <= 90:
            raise InvalidCoordinateError(
                "Latitude must be between -90 and 90 degrees.",
                {"latitude": self.latitude},
            )
        if not -180 <= self.longitude <= 180:
            raise InvalidCoordinateError(
                "Longitude must be between -180 and 180 degrees.",
                {"longitude": self.longitude},
            )
        if self.fold not in (None, 0, 1):
            raise ValueError("fold must be None, 0, or 1.")
        if not self.birth_time_known and (
            self.local_datetime.hour,
            self.local_datetime.minute,
            self.local_datetime.second,
            self.local_datetime.microsecond,
        ) != (0, 0, 0, 0):
            raise UnknownBirthTimeError(
                "Unknown-time inputs must be supplied as a local date only.",
                {"localDateTime": self.local_datetime.isoformat()},
            )

    @classmethod
    def from_public(
        cls,
        local_datetime: str | datetime | date,
        timezone: str,
        latitude: float,
        longitude: float,
        altitude_m: float | None = None,
        birth_time_known: bool = True,
        fold: int | None = None,
    ) -> ChartInput:
        return cls(
            local_datetime=parse_local_datetime(local_datetime, unknown_time=not birth_time_known),
            timezone=timezone,
            latitude=latitude,
            longitude=longitude,
            altitude_m=altitude_m,
            birth_time_known=birth_time_known,
            fold=fold,
        )

