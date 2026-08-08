"""Relocated charts.

A relocated chart asks what the same birth moment looked like from somewhere
else. The sky is unchanged -- the planets were where they were -- so the
geocentric longitudes are carried over untouched. What changes is the observer's
horizon and meridian, so the angles, the house cusps and therefore every house
placement are recalculated for the new place.

The consequence worth stating: aspects are identical, because aspects are
relationships between longitudes and no longitude moved. Only the houses say
anything new. A relocation that appears to change an aspect would be a bug.

Positions are geocentric throughout, as everywhere else in this engine. A truly
topocentric chart would shift the Moon by up to about a degree, but that is a
different calculation from relocation and mixing them would make it unclear
which effect a reader was looking at.
"""

from __future__ import annotations

from gbc_astro.aspects.engine import calculate_aspects
from gbc_astro.constants import ENGINE_NAME, ENGINE_VERSION, SCHEMA_VERSION
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.houses.base import HouseCalculator, assign_house, is_sequence_degenerate
from gbc_astro.models.chart import ChartMeta, ChartSubject, NatalChart, WarningMessage
from gbc_astro.models.input import ChartInput
from gbc_astro.models.position import BodyPosition
from gbc_astro.profiles.model import CalculationProfile

RELOCATION_VERSION = "1.0.0"


def calculate_relocation(
    chart: NatalChart,
    latitude: float,
    longitude: float,
    calculation_profile: CalculationProfile,
    house_calculator: HouseCalculator,
    house_system: str | None = None,
    altitude_m: float | None = None,
) -> NatalChart:
    """Recast `chart`'s moment for a different place.

    Returns an ordinary natal chart, because that is what a relocated chart is:
    the same instant, a different horizon.
    """
    if not chart.subject.birth_time_known:
        raise InvalidCalculationProfileError(
            "Relocation only changes the angles and houses, and a chart without a "
            "birth time has neither. Nothing would be relocated.",
            {"birthTimeKnown": False},
        )

    # Validate the destination through the same input model the natal path uses,
    # so a bad coordinate fails identically wherever it arrives from.
    ChartInput.from_public(
        local_datetime=chart.subject.local_datetime,
        timezone=chart.subject.timezone,
        latitude=latitude,
        longitude=longitude,
        altitude_m=altitude_m,
        birth_time_known=True,
    )

    system = (house_system or chart.meta.house_system or calculation_profile.house_system).lower()
    geometry = house_calculator.calculate(
        julian_day=chart.subject.julian_day,
        latitude=latitude,
        longitude=longitude,
        house_system=system,
    )

    bodies = {
        body_id: _with_house(body, assign_house(body.longitude, geometry.houses))
        for body_id, body in chart.bodies.items()
    }

    warnings: list[WarningMessage] = [
        WarningMessage(
            code="RELOCATION_POSITIONS_UNCHANGED",
            severity="info",
            message=(
                "Body longitudes are geocentric and identical to the natal chart: the "
                "planets were where they were. Only the angles, the cusps and the "
                "house placements differ, so the aspects are unchanged by "
                "construction."
            ),
            fields_affected=("bodies", "aspects"),
        )
    ]
    if is_sequence_degenerate(geometry.houses):
        warnings.append(
            WarningMessage(
                code="HOUSE_SEQUENCE_DEGENERATE",
                severity="warning",
                message=(
                    f"The {system} cusps do not advance in zodiacal order at the "
                    "relocated latitude. House assignments should not be relied on."
                ),
                fields_affected=("houses", "bodies.*.house"),
            )
        )

    subject = ChartSubject(
        local_datetime=chart.subject.local_datetime,
        timezone=chart.subject.timezone,
        utc_datetime=chart.subject.utc_datetime,
        julian_day=chart.subject.julian_day,
        latitude=latitude,
        longitude=longitude,
        altitude_m=altitude_m,
        birth_time_known=True,
    )
    meta = ChartMeta(
        schema_version=SCHEMA_VERSION,
        engine=ENGINE_NAME,
        engine_version=ENGINE_VERSION,
        ephemeris_provider=chart.meta.ephemeris_provider,
        ephemeris_data_version=chart.meta.ephemeris_data_version,
        timezone_data_version=chart.meta.timezone_data_version,
        calculation_profile=calculation_profile.id,
        house_system=system,
        aspect_profile=calculation_profile.aspect_profile.id,
        zodiac=chart.meta.zodiac,
        house_algorithm_version=geometry.algorithm_version,
        ayanamsa=chart.meta.ayanamsa,
        ayanamsa_version=chart.meta.ayanamsa_version,
        ayanamsa_degrees=chart.meta.ayanamsa_degrees,
    )
    return NatalChart(
        schema_version=SCHEMA_VERSION,
        meta=meta,
        subject=subject,
        angles=geometry.angles,
        bodies=bodies,
        houses=geometry.houses,
        aspects=calculate_aspects(bodies, calculation_profile.aspect_profile),
        derived=chart.derived,
        warnings=tuple(warnings),
    )


def _with_house(body: BodyPosition, house: int) -> BodyPosition:
    return BodyPosition(
        body_id=body.body_id,
        longitude=body.longitude,
        latitude=body.latitude,
        distance=body.distance,
        speed_longitude=body.speed_longitude,
        retrograde=body.retrograde,
        sign=body.sign,
        degree_in_sign=body.degree_in_sign,
        house=house,
    )
