"""Tropical zodiac mapping."""

from __future__ import annotations

from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.constants import SIGN_IDS
from gbc_astro.models.position import ZodiacPosition


def longitude_to_tropical(longitude: float) -> ZodiacPosition:
    normalized = normalize_longitude(longitude)
    index = int(normalized // 30.0)
    sign = SIGN_IDS[index]
    return ZodiacPosition(
        longitude=normalized,
        sign=sign,
        degree_in_sign=normalized - index * 30.0,
    )

