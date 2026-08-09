"""Draconic chart: the zodiac measured from the lunar node.

A draconic chart re-zeroes the zodiac on the Moon's north node instead of the
vernal equinox. Every ecliptic longitude has the node's longitude subtracted, so
the node sits at exactly 0 degrees Aries by construction -- which is the
definition, and therefore something that can be asserted exactly rather than
approximately.

Like the sidereal rotation, this shifts every point by the same amount. Aspects
and their orbs are untouched; only the sign and degree labels move. Unlike
sidereal, the offset comes from a body in the chart rather than from a
precessional constant, so it is specific to that chart.
"""

from __future__ import annotations

from gbc_astro.aspects.engine import calculate_aspects
from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.constants import ENGINE_NAME, ENGINE_VERSION, TRANSFORM_SCHEMA_VERSION
from gbc_astro.errors import UnsupportedBodyError
from gbc_astro.models.chart import NatalChart, WarningMessage
from gbc_astro.models.position import AnglePosition, BodyPosition
from gbc_astro.models.transform import TransformedChart
from gbc_astro.profiles.model import CalculationProfile
from gbc_astro.zodiac.tropical import longitude_to_tropical

DRACONIC_VERSION = "1.0.0"

# Which node the profile's `node_type` selects.
NODE_BY_TYPE = {"true": "true_node", "mean": "mean_node"}


def calculate_draconic(
    chart: NatalChart,
    profile: CalculationProfile,
) -> TransformedChart:
    node_id = NODE_BY_TYPE.get(profile.node_type)
    if node_id is None:
        raise UnsupportedBodyError(
            "The calculation profile does not name a supported node type.",
            {"nodeType": profile.node_type, "supported": sorted(NODE_BY_TYPE)},
        )
    node = chart.bodies.get(node_id)
    if node is None:
        raise UnsupportedBodyError(
            "A draconic chart needs the lunar node, which this chart does not contain.",
            {"body": node_id},
        )

    offset = node.longitude
    bodies = {
        body_id: _rotate_body(body, offset) for body_id, body in chart.bodies.items()
    }
    angles = {name: _rotate_angle(angle, offset) for name, angle in chart.angles.items()}

    warnings = [
        WarningMessage(
            code="DRACONIC_NO_HOUSES",
            severity="info",
            message=(
                "A draconic chart carries no house cusps. The rotation is of the "
                "zodiac, not of the sky, so the houses of the moment are unchanged "
                "and belong to the natal chart rather than to this one."
            ),
            fields_affected=("houses",),
        )
    ]

    return TransformedChart(
        schema_version=TRANSFORM_SCHEMA_VERSION,
        transform="draconic",
        transform_version=DRACONIC_VERSION,
        meta={
            "engine": ENGINE_NAME,
            "engineVersion": ENGINE_VERSION,
            "sourceSchemaVersion": chart.schema_version,
            "calculationProfile": profile.id,
            "aspectProfile": profile.aspect_profile.id,
            "zodiac": chart.meta.zodiac,
            "nodeType": profile.node_type,
            "nodeBody": node_id,
            "nodeLongitude": offset,
            "method": "subtract_node_longitude",
        },
        subject=chart.subject,
        bodies=bodies,
        angles=angles,
        aspects=calculate_aspects(
            bodies, profile.aspect_profile, profile.aspect_bodies
        ),
        warnings=tuple(warnings),
    )


def _rotate_body(body: BodyPosition, offset: float) -> BodyPosition:
    zodiac = longitude_to_tropical(normalize_longitude(body.longitude - offset))
    return BodyPosition(
        body_id=body.body_id,
        longitude=zodiac.longitude,
        latitude=body.latitude,
        distance=body.distance,
        speed_longitude=body.speed_longitude,
        retrograde=body.retrograde,
        sign=zodiac.sign,
        degree_in_sign=zodiac.degree_in_sign,
        # Houses belong to the natal chart, not to this rotation.
        house=None,
    )


def _rotate_angle(angle: AnglePosition, offset: float) -> AnglePosition:
    zodiac = longitude_to_tropical(normalize_longitude(angle.longitude - offset))
    return AnglePosition(
        longitude=zodiac.longitude,
        sign=zodiac.sign,
        degree_in_sign=zodiac.degree_in_sign,
    )
