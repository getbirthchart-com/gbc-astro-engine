"""Civil-day interval for unknown-birth-time assessment.

This is not two known birth times. Endpoints are converted independently
through the existing IANA/DST pipeline. The natal midnight snapshot remains
the compatibility anchor; this object only names the interval that snapshot
does not represent.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone

from gbc_astro.astronomy.time import TimeNormalization, isoformat_z, normalize_local_datetime

END_OF_CIVIL_DAY = time(23, 59, 59, 999999)


def isoformat_z_precise(utc_datetime: datetime) -> str:
    """UTC instant with microseconds when the civil-day end is not a whole second."""

    naive = utc_datetime.astimezone(timezone.utc).replace(tzinfo=None)
    if naive.microsecond:
        return naive.isoformat(timespec="microseconds") + "Z"
    return isoformat_z(utc_datetime)


@dataclass(frozen=True)
class CivilDayInterval:
    """JD span of one local civil date. Not a ChartInput and not a birth time."""

    local_date: date
    timezone_id: str
    start_local: datetime
    end_local: datetime
    start: TimeNormalization
    end: TimeNormalization

    @property
    def start_jd(self) -> float:
        return self.start.julian_day

    @property
    def end_jd(self) -> float:
        return self.end.julian_day

    @property
    def duration_days(self) -> float:
        return self.end_jd - self.start_jd

    def to_dict(self) -> dict[str, str]:
        return {
            "startLocal": self.start_local.isoformat(),
            "endLocal": self.end_local.isoformat(),
            "startUtc": isoformat_z_precise(self.start.utc_datetime),
            "endUtc": isoformat_z_precise(self.end.utc_datetime),
        }


def resolve_civil_day_interval(
    local_date: date,
    timezone_id: str,
    fold: int | None = None,
) -> CivilDayInterval:
    """Convert local 00:00:00 and 23:59:59.999999 independently.

    Ambiguous or nonexistent endpoints raise the same errors as a known-time
    natal at that civil instant. Interior DST gaps and repeats are handled by
    sampling uniformly in Julian Day between the two UTC instants, not by
    walking local clock hours.
    """

    start_local = datetime.combine(local_date, time.min)
    end_local = datetime.combine(local_date, END_OF_CIVIL_DAY)
    start = normalize_local_datetime(start_local, timezone_id, fold=fold)
    end = normalize_local_datetime(end_local, timezone_id, fold=fold)
    if end.julian_day <= start.julian_day:
        raise ValueError("Civil-day interval end must be after start.")
    return CivilDayInterval(
        local_date=local_date,
        timezone_id=timezone_id,
        start_local=start_local,
        end_local=end_local,
        start=start,
        end=end,
    )


def sample_julian_days(interval: CivilDayInterval, coarse_intervals: int) -> tuple[float, ...]:
    """Uniform JD samples including both endpoints."""

    if coarse_intervals < 1:
        raise ValueError("coarse_intervals must be at least 1.")
    start = interval.start_jd
    span = interval.duration_days
    return tuple(start + span * index / coarse_intervals for index in range(coarse_intervals + 1))
