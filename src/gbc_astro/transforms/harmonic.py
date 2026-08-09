"""Harmonic charts.

The harmonic-n chart multiplies every ecliptic longitude by n and takes the
result modulo 360. Unlike sidereal and draconic, this is not a rotation, and the
difference is the entire point: a rotation preserves the angles between bodies,
whereas multiplication collapses one aspect family onto conjunctions. Two bodies
exactly 120 degrees apart are conjunct in the third harmonic, two bodies 90
degrees apart are conjunct in the fourth, and so on. That is what a harmonic
chart is for.

Consequences worth stating rather than discovering:

* Aspects are **not** preserved. Recomputing them is the purpose.
* Speed multiplies by n as well, since it is the derivative of the longitude.
  Retrograde state is unchanged, because n is positive and does not flip a sign.
* There are no houses. A harmonic chart is not the chart of any instant or
  place, so it has no RAMC to derive cusps from. Nothing is substituted.
* Latitude and distance are left alone: the transform is defined on longitude,
  and multiplying an ecliptic latitude would be inventing a meaning for it.
"""

from __future__ import annotations

from gbc_astro.aspects.engine import calculate_aspects
from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.constants import ENGINE_NAME, ENGINE_VERSION, TRANSFORM_SCHEMA_VERSION
from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.models.chart import NatalChart, WarningMessage
from gbc_astro.models.position import AnglePosition, BodyPosition
from gbc_astro.models.transform import TransformedChart
from gbc_astro.profiles.model import CalculationProfile
from gbc_astro.zodiac.tropical import longitude_to_tropical

HARMONIC_VERSION = "1.0.0"

# Above this the transform is arithmetically fine but astrologically noise: a
# degree of natal error becomes n degrees of harmonic error, so at n = 200 an
# arcminute of uncertainty in a birth time swings a body across three signs.
MAX_HARMONIC = 180


def calculate_harmonic(
    chart: NatalChart,
    harmonic: int,
    profile: CalculationProfile,
) -> TransformedChart:
    if harmonic < 1 or harmonic > MAX_HARMONIC:
        raise InvalidCalculationProfileError(
            "Harmonic must be a whole number between 1 and the supported maximum.",
            {"harmonic": harmonic, "maximum": MAX_HARMONIC},
        )

    bodies = {
        body_id: _multiply_body(body, harmonic)
        for body_id, body in chart.bodies.items()
    }
    angles = {
        name: _multiply_angle(angle, harmonic) for name, angle in chart.angles.items()
    }

    warnings = [
        WarningMessage(
            code="HARMONIC_NO_HOUSES",
            severity="info",
            message=(
                "A harmonic chart carries no house cusps. It is not the chart of any "
                "instant or place, so there is no right ascension of the Midheaven to "
                "derive them from and none was substituted."
            ),
            fields_affected=("houses",),
        ),
        WarningMessage(
            code="HARMONIC_ERROR_AMPLIFIED",
            severity="info",
            message=(
                f"Positional uncertainty is multiplied by {harmonic} in this chart. "
                "An arcminute of doubt in the birth time becomes "
                f"{harmonic} arcminutes here, so a harmonic chart is only as "
                "trustworthy as the birth time behind it."
            ),
            fields_affected=("bodies", "angles"),
        ),
    ]

    return TransformedChart(
        schema_version=TRANSFORM_SCHEMA_VERSION,
        transform=f"harmonic-{harmonic}",
        transform_version=HARMONIC_VERSION,
        meta={
            "engine": ENGINE_NAME,
            "engineVersion": ENGINE_VERSION,
            "sourceSchemaVersion": chart.schema_version,
            "calculationProfile": profile.id,
            "aspectProfile": profile.aspect_profile.id,
            "zodiac": chart.meta.zodiac,
            "harmonic": harmonic,
            "method": "multiply_longitude_modulo_360",
        },
        subject=chart.subject,
        bodies=bodies,
        angles=angles,
        # Recomputed, not carried over: collapsing an aspect family onto
        # conjunctions is the point of the transform.
        aspects=calculate_aspects(
            bodies, profile.aspect_profile, profile.aspect_bodies
        ),
        warnings=tuple(warnings),
    )


def _multiply_body(body: BodyPosition, harmonic: int) -> BodyPosition:
    zodiac = longitude_to_tropical(normalize_longitude(body.longitude * harmonic))
    return BodyPosition(
        body_id=body.body_id,
        longitude=zodiac.longitude,
        latitude=body.latitude,
        distance=body.distance,
        speed_longitude=(
            None if body.speed_longitude is None else body.speed_longitude * harmonic
        ),
        retrograde=body.retrograde,
        sign=zodiac.sign,
        degree_in_sign=zodiac.degree_in_sign,
        house=None,
    )


def _multiply_angle(angle: AnglePosition, harmonic: int) -> AnglePosition:
    zodiac = longitude_to_tropical(normalize_longitude(angle.longitude * harmonic))
    return AnglePosition(
        longitude=zodiac.longitude,
        sign=zodiac.sign,
        degree_in_sign=zodiac.degree_in_sign,
    )
