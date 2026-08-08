"""Secondary progressions and solar arc directions.

Secondary progression maps one day of real ephemeris motion onto one year of
life. The chart for the tenth day after birth is the chart of the tenth year.
Nothing is symbolic about the astronomy -- the progressed chart is an ordinary
chart cast for an ordinary instant -- and everything is symbolic about the
mapping, which is why the year length is a declared profile value rather than a
constant buried in the code.

Solar arc takes the distance the progressed Sun has travelled and applies that
single arc to every natal point. That makes it a rotation, with the consequence
that directed points hold exactly their natal aspects to each other. Only their
contacts to the *natal* chart say anything new, and the module states that
rather than leaving it to be discovered.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from gbc_astro.aspects.engine import calculate_aspects
from gbc_astro.astronomy.circular import directed_circular_delta, normalize_longitude
from gbc_astro.astronomy.time import isoformat_z
from gbc_astro.constants import ENGINE_NAME, ENGINE_VERSION, TRANSFORM_SCHEMA_VERSION
from gbc_astro.errors import InvalidCalculationProfileError, UnsupportedBodyError
from gbc_astro.models.chart import NatalChart, WarningMessage
from gbc_astro.models.position import AnglePosition, BodyPosition
from gbc_astro.models.transform import TransformedChart
from gbc_astro.profiles.model import CalculationProfile
from gbc_astro.profiles.progression import ProgressionProfile
from gbc_astro.zodiac.tropical import longitude_to_tropical


def progressed_instant(
    birth_utc: datetime,
    target_utc: datetime,
    profile: ProgressionProfile,
) -> tuple[datetime, float]:
    """The instant to cast, and the elapsed years it represents.

    One day per year: the elapsed years become elapsed days. Age zero returns
    the birth instant exactly, and age one returns birth plus one day.
    """
    elapsed_days = (target_utc - birth_utc).total_seconds() / 86400.0
    years = elapsed_days / profile.year_length_days
    return birth_utc + timedelta(days=years), years


def calculate_secondary_progressions(
    chart: NatalChart,
    target: datetime,
    calculation_profile: CalculationProfile,
    profile: ProgressionProfile,
    natal: Callable[..., NatalChart],
) -> TransformedChart:
    """Cast the progressed chart for `target`.

    `natal` is the engine's own natal callable, injected so this module performs
    no ephemeris work and the progressed chart is an ordinary chart from the same
    engine configuration.
    """
    if target.tzinfo is None:
        raise ValueError("target must be timezone-aware.")
    if not chart.subject.birth_time_known:
        raise InvalidCalculationProfileError(
            "Secondary progressions need a known birth time: one day of error in "
            "the progressed instant is a year of symbolic time.",
            {"birthTimeKnown": False},
        )

    birth = _parse_utc(chart.subject.utc_datetime)
    instant, years = progressed_instant(birth, target.astimezone(timezone.utc), profile)

    # The source chart's own house system, not the profile default. Carrying it
    # over keeps the progressed chart a chart of the same kind, and it is what
    # makes a polar birth work at all: above the polar circle Placidus and Koch
    # have no cusps, so a Tromso chart cast in whole sign would otherwise cast
    # its natal fine and then fail here, on a default the caller never chose.
    progressed = natal(
        local_datetime=instant.replace(tzinfo=None),
        timezone="UTC",
        latitude=chart.subject.latitude,
        longitude=chart.subject.longitude,
        altitude_m=chart.subject.altitude_m,
        house_system=chart.meta.house_system,
    )

    return TransformedChart(
        schema_version=TRANSFORM_SCHEMA_VERSION,
        transform="secondary_progression",
        transform_version=profile.version,
        meta={
            "engine": ENGINE_NAME,
            "engineVersion": ENGINE_VERSION,
            "sourceSchemaVersion": chart.schema_version,
            "calculationProfile": calculation_profile.id,
            "progressionProfile": profile.to_dict(),
            "zodiac": chart.meta.zodiac,
            "targetInstant": isoformat_z(target.astimezone(timezone.utc)),
            "progressedInstant": isoformat_z(instant),
            "elapsedYears": years,
            "houseSystem": progressed.meta.house_system,
        },
        subject=chart.subject,
        bodies=progressed.bodies,
        angles=progressed.angles,
        aspects=progressed.aspects,
        warnings=(
            WarningMessage(
                code="PROGRESSED_CHART_IS_A_REAL_CHART",
                severity="info",
                message=(
                    "This is an ordinary chart cast for the progressed instant at the "
                    "birthplace. Its positions, speeds and houses are real; only the "
                    "mapping of one day to one year is symbolic. The year length used "
                    f"is {profile.year_length_days} days ({profile.year_length_name})."
                ),
                fields_affected=("bodies", "angles"),
            ),
        ),
    )


def calculate_solar_arc(
    chart: NatalChart,
    target: datetime,
    calculation_profile: CalculationProfile,
    profile: ProgressionProfile,
    natal: Callable[..., NatalChart],
) -> TransformedChart:
    """Direct every natal point by the progressed Sun's travel."""
    if "sun" not in chart.bodies:
        raise UnsupportedBodyError(
            "Solar arc directions need the natal Sun.", {"body": "sun"}
        )

    progression = calculate_secondary_progressions(
        chart, target, calculation_profile, profile, natal
    )
    arc = directed_circular_delta(
        chart.bodies["sun"].longitude, progression.bodies["sun"].longitude
    )
    # The Sun advances about a degree a year, so the arc grows past 180 degrees
    # after roughly 180 years of life. Unwrap it against the elapsed years rather
    # than letting the shortest-arc convention fold it back.
    years = float(progression.meta["elapsedYears"])
    while arc < 0.0 and years > 0.5:
        arc += 360.0

    bodies = {
        body_id: _direct_body(body, arc) for body_id, body in chart.bodies.items()
    }
    angles = {name: _direct_angle(angle, arc) for name, angle in chart.angles.items()}

    return TransformedChart(
        schema_version=TRANSFORM_SCHEMA_VERSION,
        transform="solar_arc",
        transform_version=profile.version,
        meta={
            "engine": ENGINE_NAME,
            "engineVersion": ENGINE_VERSION,
            "sourceSchemaVersion": chart.schema_version,
            "calculationProfile": calculation_profile.id,
            "progressionProfile": profile.to_dict(),
            "zodiac": chart.meta.zodiac,
            "targetInstant": progression.meta["targetInstant"],
            "progressedInstant": progression.meta["progressedInstant"],
            "elapsedYears": years,
            "solarArcDegrees": arc,
        },
        subject=chart.subject,
        bodies=bodies,
        angles=angles,
        aspects=calculate_aspects(bodies, calculation_profile.aspect_profile),
        warnings=(
            WarningMessage(
                code="SOLAR_ARC_IS_A_ROTATION",
                severity="info",
                message=(
                    "Every point was advanced by the same arc, so the directed points "
                    "hold exactly their natal aspects to one another. Only contacts "
                    "between a directed point and the natal chart carry information."
                ),
                fields_affected=("aspects",),
            ),
            WarningMessage(
                code="SOLAR_ARC_NO_HOUSES",
                severity="info",
                message=(
                    "A directed chart carries no house cusps. The houses of the "
                    "moment belong to the natal chart; directing them by the same arc "
                    "would be a separate convention this profile does not define."
                ),
                fields_affected=("houses",),
            ),
        ),
    )


def _direct_body(body: BodyPosition, arc: float) -> BodyPosition:
    zodiac = longitude_to_tropical(normalize_longitude(body.longitude + arc))
    return BodyPosition(
        body_id=body.body_id,
        longitude=zodiac.longitude,
        latitude=body.latitude,
        distance=body.distance,
        # A directed point is a symbolic construction, not a moving body.
        speed_longitude=None,
        retrograde=None,
        sign=zodiac.sign,
        degree_in_sign=zodiac.degree_in_sign,
        house=None,
    )


def _direct_angle(angle: AnglePosition, arc: float) -> AnglePosition:
    zodiac = longitude_to_tropical(normalize_longitude(angle.longitude + arc))
    return AnglePosition(
        longitude=zodiac.longitude,
        sign=zodiac.sign,
        degree_in_sign=zodiac.degree_in_sign,
    )


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
