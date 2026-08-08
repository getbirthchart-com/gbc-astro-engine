"""Davison relationship chart: a real chart at the midpoint moment and place.

A composite chart is an arithmetic construct -- it averages two charts and has
no instant of its own, which is why it carries no speeds and why its houses need
a declared methodology. A Davison chart is different in kind: it is an ordinary
natal calculation run at the midpoint in time between the two births and at the
midpoint of the two locations. Everything is therefore real. The bodies have
genuine speeds and retrograde states, the houses come from an actual time and
place, and applying and separating mean what they mean in any other chart.

The one trap is geographic longitude. It wraps at the antimeridian, so 179 East
and 179 West average to 180, not to 0. Latitude does not wrap and takes the
plain mean. The profile names this as
`mean_latitude_circular_mean_longitude`; note that it is the astrological
convention and not the great-circle midpoint of the two points, which would be a
different location.
"""

from __future__ import annotations

from datetime import datetime, timezone

from gbc_astro.astronomy.circular import normalize_longitude, shortest_arc_midpoint
from gbc_astro.constants import DAVISON_SCHEMA_VERSION, ENGINE_NAME, ENGINE_VERSION
from gbc_astro.errors import InvalidCalculationProfileError, UnknownBirthTimeError
from gbc_astro.models.chart import NatalChart, WarningMessage
from gbc_astro.models.relationship import DavisonChart, RelationshipMeta
from gbc_astro.profiles.model import RelationshipProfile


def midpoint_latitude(latitude_a: float, latitude_b: float) -> float:
    """Latitude does not wrap, so the plain mean is the midpoint."""
    return (latitude_a + latitude_b) / 2.0


def midpoint_longitude(longitude_a: float, longitude_b: float) -> float:
    """Circular midpoint of two geographic longitudes, returned in [-180, 180].

    Geographic longitude is circular exactly as ecliptic longitude is, but uses
    a signed convention. Converting to [0, 360) for the midpoint and back keeps
    the antimeridian correct: 179 and -179 give 180, not 0.

    The two inputs are sorted first. `shortest_arc_midpoint` is commutative in
    exact arithmetic but not in floating point -- the two argument orders differ
    in the last bit or two -- and here the result is not the answer but the
    *input* to a fresh chart calculation, so a difference of 1e-14 degrees would
    make `davison(a, b)` and `davison(b, a)` disagree. Sorting removes the
    dependence at the source rather than rounding it away afterwards.
    """
    first, second = sorted(
        (normalize_longitude(longitude_a), normalize_longitude(longitude_b))
    )
    midpoint = shortest_arc_midpoint(first, second)
    # Exactly 180 is the antimeridian, which the signed convention writes as
    # +180 rather than -180.
    return midpoint - 360.0 if midpoint > 180.0 else midpoint


def midpoint_instant(first: datetime, second: datetime) -> datetime:
    """The instant halfway between two moments, to microsecond resolution."""
    earlier, later = sorted((first, second))
    return earlier + (later - earlier) / 2


def calculate_davison(
    chart_a: NatalChart,
    chart_b: NatalChart,
    profile: RelationshipProfile,
    natal: object,
) -> DavisonChart:
    """Build the Davison chart for two natal charts.

    `natal` is the engine's own natal callable, injected so this module performs
    no ephemeris work of its own and the resulting chart is byte-for-byte an
    ordinary chart from the same engine configuration.
    """
    _assert_comparable(chart_a, chart_b)

    for label, chart in (("A", chart_a), ("B", chart_b)):
        if not chart.subject.birth_time_known:
            raise UnknownBirthTimeError(
                "A Davison chart is calculated at the midpoint moment of the two "
                "births, so both birth times must be known. No substitute time was "
                "used.",
                {"chart": label},
            )

    instant = midpoint_instant(
        _parse_utc(chart_a.subject.utc_datetime), _parse_utc(chart_b.subject.utc_datetime)
    )
    latitude = midpoint_latitude(chart_a.subject.latitude, chart_b.subject.latitude)
    longitude = midpoint_longitude(chart_a.subject.longitude, chart_b.subject.longitude)

    chart = natal(  # type: ignore[operator]
        local_datetime=instant.replace(tzinfo=None),
        timezone="UTC",
        latitude=latitude,
        longitude=longitude,
    )

    return DavisonChart(
        schema_version=DAVISON_SCHEMA_VERSION,
        meta=RelationshipMeta(
            schema_version=DAVISON_SCHEMA_VERSION,
            engine=ENGINE_NAME,
            engine_version=ENGINE_VERSION,
            relationship_profile=profile.id,
            aspect_profile=profile.aspect_profile.id,
            zodiac=chart_a.meta.zodiac,
            chart_a_schema_version=chart_a.schema_version,
            chart_b_schema_version=chart_b.schema_version,
            davison_location_method=profile.davison_location_method,
            house_algorithm_version=chart.meta.house_algorithm_version,
        ),
        chart=chart,
        derived_utc_datetime=instant.isoformat().replace("+00:00", "Z"),
        derived_latitude=latitude,
        derived_longitude=longitude,
        warnings=(
            WarningMessage(
                code="DAVISON_DERIVED_LOCATION",
                severity="info",
                message=(
                    "This chart is calculated for the midpoint moment and midpoint "
                    "location of the two births, which is a real instant and place. "
                    "Its speeds, houses and applying/separating phases are therefore "
                    "genuine, unlike a midpoint composite. The location uses the mean "
                    "latitude and the circular mean longitude, not the great-circle "
                    "midpoint of the two birthplaces."
                ),
                fields_affected=("chart.subject",),
            ),
        ),
    )


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _assert_comparable(chart_a: NatalChart, chart_b: NatalChart) -> None:
    if chart_a.meta.zodiac != chart_b.meta.zodiac:
        raise InvalidCalculationProfileError(
            "A Davison chart requires both charts to use the same zodiac.",
            {"chartAZodiac": chart_a.meta.zodiac, "chartBZodiac": chart_b.meta.zodiac},
        )
    if chart_a.schema_version != chart_b.schema_version:
        raise InvalidCalculationProfileError(
            "A Davison chart requires both charts to use the same schema version.",
            {
                "chartASchemaVersion": chart_a.schema_version,
                "chartBSchemaVersion": chart_b.schema_version,
            },
        )
