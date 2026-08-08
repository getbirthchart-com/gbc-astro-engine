"""Whole Sign house helpers."""

from __future__ import annotations

from gbc_astro.astronomy.circular import normalize_longitude


def whole_sign_cusp_longitudes(ascendant_longitude: float) -> tuple[float, ...]:
    first = int(normalize_longitude(ascendant_longitude) // 30.0) * 30.0
    return tuple(normalize_longitude(first + 30.0 * index) for index in range(12))

