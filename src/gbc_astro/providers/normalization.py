"""Normalize provider raw positions into canonical body positions."""

from __future__ import annotations

from gbc_astro.models.position import BodyPosition, RawBodyPosition
from gbc_astro.zodiac.tropical import longitude_to_tropical


def normalize_body_position(
    body_id: str,
    raw: RawBodyPosition,
    house: int | None = None,
) -> BodyPosition:
    zpos = longitude_to_tropical(raw.longitude_deg)
    speed = raw.longitude_speed_deg_per_day
    return BodyPosition(
        body_id=body_id,
        longitude=zpos.longitude,
        latitude=raw.latitude_deg,
        distance=raw.distance,
        speed_longitude=speed,
        retrograde=None if speed is None else speed < 0,
        sign=zpos.sign,
        degree_in_sign=zpos.degree_in_sign,
        house=house,
    )

