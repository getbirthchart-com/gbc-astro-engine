"""Astrocartography primitives.

An astrocartography line marks every place on Earth where, at one fixed instant,
a given body sits on one of the four angles. The instant never changes -- only
the observer moves -- so the body's right ascension and declination are constants
and each line has a closed form. No root finding is needed and none is used.

    MC line   geographic longitude = RA - GST
    IC line   the same meridian, half a turn away
    ASC line  for each latitude: hour angle H = -acos(-tan(lat) * tan(dec)),
              then longitude = RA + H - GST
    DSC line  the same with +acos

The MC and IC lines are meridians: one longitude, valid at every latitude. The
ASC and DSC lines are curves, sampled per latitude, and they simply stop where
`|tan(lat) * tan(dec)| > 1`, because a body that never rises at a latitude has no
rising line there. Those latitudes are omitted rather than clamped.

Self-consistency is the validation. Standing on a computed MC line and casting
the chart there must put the body on the Midheaven, and the test asserts exactly
that using the ordinary house calculation -- machinery that shares no code with
this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.constants import ENGINE_NAME, ENGINE_VERSION
from gbc_astro.errors import UnsupportedBodyError

ASTROCARTOGRAPHY_VERSION = "1.0.0"

# Latitudes sampled for the rising and setting curves. Beyond roughly 66 degrees
# most bodies stop rising and setting at all, so the default stops short of the
# poles rather than producing a line that is mostly gaps.
DEFAULT_LATITUDE_RANGE = (-66.0, 66.0)
DEFAULT_LATITUDE_STEP = 2.0

ANGLE_LINES = ("mc", "ic", "ascendant", "descendant")


@dataclass(frozen=True)
class LinePoint:
    latitude: float
    longitude: float

    def to_dict(self) -> dict[str, float]:
        return {"latitude": self.latitude, "longitude": self.longitude}


@dataclass(frozen=True)
class AstroLine:
    """One body on one angle, as a set of geographic points."""

    body: str
    angle: str
    kind: str
    points: tuple[LinePoint, ...]
    detail: dict[str, Any]

    @property
    def id(self) -> str:
        return f"acg.{self.body}.{self.angle}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "body": self.body,
            "angle": self.angle,
            "kind": self.kind,
            "pointCount": len(self.points),
            "points": [point.to_dict() for point in self.points],
            "detail": self.detail,
        }


def _to_signed_longitude(longitude: float) -> float:
    """Geographic longitude in [-180, 180], the convention the engine uses."""
    normalized = normalize_longitude(longitude)
    return normalized - 360.0 if normalized > 180.0 else normalized


def meridian_longitude(right_ascension: float, sidereal_time_deg: float) -> float:
    """Where the body is exactly on the Midheaven."""
    return _to_signed_longitude(right_ascension - sidereal_time_deg)


def horizon_longitude(
    right_ascension: float,
    declination: float,
    latitude: float,
    sidereal_time_deg: float,
    rising: bool,
) -> float | None:
    """Where the body is exactly on the horizon at this latitude.

    Returns None when the body never rises or sets there: at high latitude a
    body can be circumpolar or permanently below the horizon, and neither has a
    rising line. Omitted, never clamped to the nearest latitude that works.
    """
    argument = -math.tan(math.radians(latitude)) * math.tan(math.radians(declination))
    if abs(argument) > 1.0:
        return None
    hour_angle = math.degrees(math.acos(argument))
    if rising:
        hour_angle = -hour_angle
    return _to_signed_longitude(right_ascension + hour_angle - sidereal_time_deg)


def calculate_astrocartography(
    equatorial: dict[str, tuple[float, float]],
    sidereal_time_deg: float,
    bodies: tuple[str, ...] | None = None,
    latitude_range: tuple[float, float] = DEFAULT_LATITUDE_RANGE,
    latitude_step: float = DEFAULT_LATITUDE_STEP,
) -> dict[str, Any]:
    """Build all four lines for each requested body.

    `equatorial` maps a body id to its (right ascension, declination) in degrees
    at the chart's instant. Both are constants of the moment, which is why every
    line here is closed form.
    """
    if latitude_step <= 0.0:
        raise ValueError("latitude_step must be positive.")
    requested = bodies or tuple(sorted(equatorial))
    missing = [body for body in requested if body not in equatorial]
    if missing:
        raise UnsupportedBodyError(
            "No equatorial position was supplied for these bodies.",
            {"bodies": missing},
        )

    latitudes: list[float] = []
    current = latitude_range[0]
    while current <= latitude_range[1] + 1e-9:
        latitudes.append(round(current, 6))
        current += latitude_step

    lines: list[AstroLine] = []
    for body in requested:
        right_ascension, declination = equatorial[body]
        meridian = meridian_longitude(right_ascension, sidereal_time_deg)

        for angle, longitude in (
            ("mc", meridian),
            ("ic", _to_signed_longitude(meridian + 180.0)),
        ):
            lines.append(
                AstroLine(
                    body=body,
                    angle=angle,
                    kind="meridian",
                    points=tuple(
                        LinePoint(latitude=value, longitude=longitude)
                        for value in latitudes
                    ),
                    detail={
                        "longitude": longitude,
                        "rightAscension": right_ascension,
                        "declination": declination,
                    },
                )
            )

        for angle, rising in (("ascendant", True), ("descendant", False)):
            points: list[LinePoint] = []
            for value in latitudes:
                horizon = horizon_longitude(
                    right_ascension, declination, value, sidereal_time_deg, rising
                )
                if horizon is not None:
                    points.append(LinePoint(latitude=value, longitude=horizon))
            lines.append(
                AstroLine(
                    body=body,
                    angle=angle,
                    kind="curve",
                    points=tuple(points),
                    detail={
                        "rightAscension": right_ascension,
                        "declination": declination,
                        "omittedLatitudes": len(latitudes) - len(points),
                    },
                )
            )

    return {
        "engine": ENGINE_NAME,
        "engineVersion": ENGINE_VERSION,
        "method": "closed_form_angular_lines",
        "version": ASTROCARTOGRAPHY_VERSION,
        "siderealTimeDeg": sidereal_time_deg,
        "latitudeRange": list(latitude_range),
        "latitudeStep": latitude_step,
        "lineCount": len(lines),
        "lines": [line.to_dict() for line in lines],
        "notes": (
            "MC and IC lines are meridians: one longitude valid at every latitude. "
            "Ascendant and Descendant lines are curves sampled per latitude.",
            "A body that is circumpolar or never rises at a latitude has no rising "
            "line there. Those latitudes are omitted, never clamped.",
            "Longitudes use the signed convention, -180 to 180, matching chart input.",
        ),
    }
