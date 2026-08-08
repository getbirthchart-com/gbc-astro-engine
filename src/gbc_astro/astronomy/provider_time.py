"""Provider-neutral time conversion helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from gbc_astro.astronomy.time import datetime_to_julian_day


def julian_day_ut(instant_utc: datetime) -> float:
    """Return Julian Day UT for provider calls.

    Providers may need additional timescale conversions later; keeping this
    function isolated preserves the boundary required by the spec.
    """

    if instant_utc.tzinfo is None:
        raise ValueError("instant_utc must be timezone-aware.")
    return datetime_to_julian_day(instant_utc.astimezone(timezone.utc))
