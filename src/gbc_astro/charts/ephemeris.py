"""Ephemeris generator.

Produces a table of positions over a date range at a fixed step. Nothing here is
astrological: it is the provider's output, tabulated, so that a caller wanting a
year of daily Moon positions does not have to call the natal path 365 times and
throw away the houses each time.

Rows are yielded rather than accumulated, so memory stays bounded whatever the
range. `01_MASTER_REQUIREMENTS.md` section 16 asks for a batch path with bounded
memory, and a generator is the honest way to give one.

Every row is exactly what a single-instant call would return, which is the one
property worth validating and is asserted in the tests.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from gbc_astro.astronomy.time import isoformat_z
from gbc_astro.constants import ENGINE_NAME, ENGINE_VERSION
from gbc_astro.errors import UnsupportedBodyError
from gbc_astro.providers.base import EphemerisProvider
from gbc_astro.providers.normalization import normalize_body_position

EPHEMERIS_VERSION = "1.0.0"

# A guard against a step of seconds over a range of centuries turning into an
# accidental denial of service. Callers wanting more can raise it explicitly.
DEFAULT_MAX_ROWS = 200_000


@dataclass(frozen=True)
class EphemerisRow:
    instant_utc: str
    julian_day: float
    bodies: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "instantUtc": self.instant_utc,
            "julianDay": self.julian_day,
            "bodies": self.bodies,
        }


def iter_ephemeris(
    provider: EphemerisProvider,
    bodies: tuple[str, ...],
    start: datetime,
    end: datetime,
    step: timedelta,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> Iterator[EphemerisRow]:
    """Yield one row per step from `start` through `end` inclusive."""
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start and end must be timezone-aware.")
    if end < start:
        raise ValueError("end must not be before start.")
    if step.total_seconds() <= 0:
        raise ValueError("step must be positive.")

    unsupported = [body for body in bodies if not provider.supports_body(body)]
    if unsupported:
        raise UnsupportedBodyError(
            "The configured provider does not support these bodies.",
            {"provider": provider.id, "bodies": unsupported},
        )

    from gbc_astro.astronomy.provider_time import julian_day_ut

    instant = start.astimezone(timezone.utc)
    finish = end.astimezone(timezone.utc)
    emitted = 0
    while instant <= finish:
        if emitted >= max_rows:
            raise ValueError(
                f"Ephemeris would exceed {max_rows} rows. Narrow the range, widen "
                "the step, or raise max_rows deliberately."
            )
        yield EphemerisRow(
            instant_utc=isoformat_z(instant),
            julian_day=julian_day_ut(instant),
            bodies={
                body: normalize_body_position(
                    body, provider.position(body, instant)
                ).to_dict()
                for body in bodies
            },
        )
        emitted += 1
        instant += step


def generate_ephemeris(
    provider: EphemerisProvider,
    bodies: tuple[str, ...],
    start: datetime,
    end: datetime,
    step: timedelta,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> dict[str, Any]:
    """Materialise the table, with provenance."""
    rows = list(iter_ephemeris(provider, bodies, start, end, step, max_rows))
    return {
        "engine": ENGINE_NAME,
        "engineVersion": ENGINE_VERSION,
        "version": EPHEMERIS_VERSION,
        "ephemerisProvider": provider.id,
        "ephemerisDataVersion": provider.data_version,
        "bodies": list(bodies),
        "range": {
            "start": isoformat_z(start.astimezone(timezone.utc)),
            "end": isoformat_z(end.astimezone(timezone.utc)),
            "stepSeconds": step.total_seconds(),
        },
        "rowCount": len(rows),
        "rows": [row.to_dict() for row in rows],
        "notes": (
            "Each row is exactly what a single-instant call returns; the generator "
            "is a convenience, not a second calculation path.",
            "Rows are produced lazily by iter_ephemeris when memory matters.",
        ),
    }
