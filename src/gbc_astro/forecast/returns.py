"""Planetary returns, including the retrograde multi-hit case.

A return is the instant a body comes back to the exact ecliptic longitude it
held at birth. That instant is found by root finding, never by scanning for the
nearest daily sample -- see `gbc_astro.search.solver` for why the spec forbids
the latter.

Multiple hits are the normal case, not an exception. A body that turns
retrograde near its natal degree crosses it three times: direct, retrograde,
then direct again. A Saturn return typically has three exact hits spread over
months, and each is a real return. All of them are reported, in order. Reducing
them to the first would throw away most of what a Saturn return is.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from gbc_astro.constants import ENGINE_NAME, ENGINE_VERSION, RETURN_SCHEMA_VERSION
from gbc_astro.errors import UnsupportedBodyError
from gbc_astro.models.chart import NatalChart, WarningMessage
from gbc_astro.models.forecast import ReturnHit, ReturnSearchResult
from gbc_astro.providers.base import EphemerisProvider
from gbc_astro.search.events import find_longitude_crossings

# Mean tropical/sidereal periods in days, used only to size a default search
# window around an expected return. The returns themselves are always solved,
# never estimated from these numbers.
MEAN_PERIOD_DAYS: dict[str, float] = {
    "sun": 365.2422,
    "moon": 27.3216,
    "mercury": 365.2422,
    "venus": 365.2422,
    "mars": 686.98,
    "jupiter": 4332.59,
    "saturn": 10759.22,
    "uranus": 30688.5,
    "neptune": 60182.0,
    "pluto": 90560.0,
}


def _hit_notes(body: str) -> tuple[str, ...]:
    return (
        "Every exact crossing in the window is reported. A body stationing near "
        "its natal degree crosses it three times, and all three are real returns.",
        "Instants come from bracketed root finding refined by bisection, not from "
        "sampling the ephemeris at fixed intervals.",
        f"Mean period used only to size the default window for {body}; the returns "
        "themselves are solved, never estimated.",
    )


def calculate_returns(
    natal_chart: NatalChart,
    body: str,
    window_start: datetime,
    window_end: datetime,
    provider: EphemerisProvider,
    chart_builder: Callable[[datetime], NatalChart] | None = None,
) -> ReturnSearchResult:
    """Every exact return of `body` to its natal longitude inside the window.

    `chart_builder` casts a chart for each hit when supplied. It is injected so
    this module performs no chart assembly of its own and each return chart is
    an ordinary chart from the same engine configuration.
    """
    natal_body = natal_chart.bodies.get(body)
    if natal_body is None:
        raise UnsupportedBodyError(
            "The natal chart does not contain this body, so it has no return.",
            {"body": body},
        )
    if window_end <= window_start:
        raise ValueError("window_end must be after window_start.")

    crossings = find_longitude_crossings(
        provider,
        body,
        natal_body.longitude,
        window_start.astimezone(timezone.utc),
        window_end.astimezone(timezone.utc),
    )

    hits = tuple(
        ReturnHit(
            ordinal=index,
            instant_utc=event.instant_utc,
            julian_day=event.julian_day,
            longitude=event.longitude,
            direction=event.direction,
            precision_seconds=event.precision_seconds,
            chart=(
                chart_builder(datetime.fromisoformat(event.instant_utc.replace("Z", "+00:00")))
                if chart_builder
                else None
            ),
        )
        for index, event in enumerate(crossings, start=1)
    )

    warnings: list[WarningMessage] = []
    if not hits:
        warnings.append(
            WarningMessage(
                code="NO_RETURN_IN_WINDOW",
                severity="info",
                message=(
                    f"{body} does not return to its natal longitude inside this window. "
                    "The window was searched exhaustively; this is not a resolution "
                    "failure."
                ),
                fields_affected=("hits",),
            )
        )

    return ReturnSearchResult(
        schema_version=RETURN_SCHEMA_VERSION,
        meta={
            "engine": ENGINE_NAME,
            "engineVersion": ENGINE_VERSION,
            "ephemerisProvider": provider.id,
            "ephemerisDataVersion": provider.data_version,
            "method": "bracketed_root_find_bisection_refined",
        },
        body=body,
        natal_longitude=natal_body.longitude,
        window_start=window_start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        window_end=window_end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        hits=hits,
        warnings=tuple(warnings),
        notes=_hit_notes(body),
    )


def default_window_around(
    natal_chart: NatalChart,
    body: str,
    reference: datetime,
    margin_days: float = 45.0,
) -> tuple[datetime, datetime]:
    """A window wide enough to contain the return nearest `reference`.

    The margin has to cover a whole retrograde loop, otherwise the window can
    clip the first or last of a three-hit return and silently report two.
    """
    period = MEAN_PERIOD_DAYS.get(body)
    if period is None:
        raise UnsupportedBodyError(
            "No mean period is known for this body, so a default window cannot be "
            "sized. Supply an explicit window.",
            {"body": body},
        )
    reference_utc = reference.astimezone(timezone.utc)
    half = min(period / 2.0, 200.0) + margin_days
    return reference_utc - timedelta(days=half), reference_utc + timedelta(days=half)


def solar_return_window(birth_utc: datetime, year: int) -> tuple[datetime, datetime]:
    """A window around the birthday in `year`.

    The Sun never retrogrades, so a solar return has exactly one hit and a tight
    window is safe.
    """
    anchor = birth_utc.astimezone(timezone.utc).replace(year=year)
    return anchor - timedelta(days=3), anchor + timedelta(days=3)


def lunar_return_window(reference: datetime) -> tuple[datetime, datetime]:
    """A window covering one full lunar cycle from `reference`.

    The Moon never retrogrades either, so this yields exactly one hit.
    """
    start = reference.astimezone(timezone.utc)
    return start, start + timedelta(days=MEAN_PERIOD_DAYS["moon"] + 1.0)
