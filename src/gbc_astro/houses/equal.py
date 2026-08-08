"""Equal house helpers."""

from __future__ import annotations

from gbc_astro.astronomy.circular import normalize_longitude


def equal_cusp_longitudes(ascendant_longitude: float) -> tuple[float, ...]:
    first = normalize_longitude(ascendant_longitude)
    return tuple(normalize_longitude(first + 30.0 * index) for index in range(12))

