"""IANA timezone normalization and provider-neutral Julian day helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from gbc_astro.errors import (
    AmbiguousLocalTimeError,
    NonexistentLocalTimeError,
    UnknownTimezoneError,
)


@dataclass(frozen=True)
class TimeNormalization:
    local_datetime: datetime
    timezone_id: str
    utc_datetime: datetime
    julian_day: float
    timezone_data_version: str


def normalize_local_datetime(
    local_datetime: datetime,
    timezone_id: str,
    fold: int | None = None,
) -> TimeNormalization:
    """Resolve a naive local datetime through an IANA timezone.

    Ambiguous local times require an explicit PEP 495 fold. Nonexistent local
    times raise instead of being silently shifted.
    """

    if local_datetime.tzinfo is not None:
        raise ValueError("local_datetime must be naive; timezone_id owns resolution.")
    try:
        tz = ZoneInfo(timezone_id)
    except ZoneInfoNotFoundError as exc:
        raise UnknownTimezoneError(
            "Timezone must be a valid IANA identifier.",
            {"timezone": timezone_id},
        ) from exc

    valid_folds: list[tuple[int, datetime, object]] = []
    for candidate_fold in (0, 1):
        aware = local_datetime.replace(tzinfo=tz, fold=candidate_fold)
        utc_dt = aware.astimezone(timezone.utc)
        round_trip = utc_dt.astimezone(tz).replace(tzinfo=None)
        if round_trip == local_datetime:
            valid_folds.append((candidate_fold, utc_dt, aware.utcoffset()))

    if not valid_folds:
        raise NonexistentLocalTimeError(
            "The supplied local datetime does not exist in the timezone.",
            {"timezone": timezone_id, "localDateTime": local_datetime.isoformat()},
        )

    unique_offsets = {item[2] for item in valid_folds}
    if len(unique_offsets) > 1:
        if fold is None:
            raise AmbiguousLocalTimeError(
                "The supplied local datetime occurs twice due to a DST transition.",
                {"timezone": timezone_id, "localDateTime": local_datetime.isoformat()},
            )
        selected = [item for item in valid_folds if item[0] == fold]
        if not selected:
            raise AmbiguousLocalTimeError(
                "The supplied fold does not resolve this ambiguous local datetime.",
                {
                    "timezone": timezone_id,
                    "localDateTime": local_datetime.isoformat(),
                    "fold": fold,
                },
            )
        utc_datetime = selected[0][1]
    else:
        utc_datetime = valid_folds[0][1]

    return TimeNormalization(
        local_datetime=local_datetime,
        timezone_id=timezone_id,
        utc_datetime=utc_datetime,
        julian_day=datetime_to_julian_day(utc_datetime),
        timezone_data_version="system-zoneinfo",
    )


def datetime_to_julian_day(utc_datetime: datetime) -> float:
    """Convert a UTC datetime to Julian Day using the Gregorian calendar."""

    if utc_datetime.tzinfo is None:
        raise ValueError("utc_datetime must be timezone-aware.")
    dt = utc_datetime.astimezone(timezone.utc)
    year = dt.year
    month = dt.month
    day_fraction = (
        dt.day
        + dt.hour / 24.0
        + dt.minute / 1440.0
        + (dt.second + dt.microsecond / 1_000_000.0) / 86400.0
    )
    if month <= 2:
        year -= 1
        month += 12
    century = year // 100
    correction = 2 - century + century // 4
    return (
        int(365.25 * (year + 4716))
        + int(30.6001 * (month + 1))
        + day_fraction
        + correction
        - 1524.5
    )


def isoformat_z(utc_datetime: datetime) -> str:
    """Serialize a UTC datetime with a trailing Z."""

    dt = utc_datetime.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat(timespec="seconds") + "Z"


def julian_day_to_datetime(julian_day: float) -> datetime:
    """Convert a Julian Day back to a UTC datetime.

    Inverse of `datetime_to_julian_day`. The numerical search engine works in
    Julian Days because they are a continuous real line, while providers take
    datetimes, so the boundary needs both directions.
    """

    shifted = julian_day + 0.5
    integer_part = math.floor(shifted)
    day_fraction = shifted - integer_part

    if integer_part >= 2299161:
        alpha = math.floor((integer_part - 1867216.25) / 36524.25)
        integer_part += 1 + alpha - math.floor(alpha / 4)

    b = integer_part + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)

    day = b - d - math.floor(30.6001 * e)
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715

    # Round to whole microseconds so the value round-trips cleanly; Julian Days
    # carry more precision in the fraction than datetime can represent.
    microseconds = int(round(day_fraction * 86400.0 * 1_000_000.0))
    return datetime(int(year), int(month), int(day), tzinfo=timezone.utc) + timedelta(
        microseconds=microseconds
    )
