"""Circular longitude math primitives."""

from __future__ import annotations

import math


def normalize_longitude(value: float) -> float:
    """Normalize a longitude to the half-open range [0, 360)."""

    normalized = math.fmod(value, 360.0)
    if normalized < 0:
        normalized += 360.0
    if math.isclose(normalized, 360.0, abs_tol=1e-12):
        return 0.0
    return normalized


def shortest_angular_distance(a: float, b: float) -> float:
    """Return shortest absolute circular separation in degrees."""

    delta = abs(normalize_longitude(a) - normalize_longitude(b)) % 360.0
    return min(delta, 360.0 - delta)


def directed_circular_delta(start: float, end: float) -> float:
    """Return signed shortest delta from start to end in (-180, 180]."""

    delta = (normalize_longitude(end) - normalize_longitude(start) + 540.0) % 360.0 - 180.0
    if math.isclose(delta, -180.0, abs_tol=1e-12):
        return 180.0
    return delta


def shortest_arc_midpoint(a: float, b: float) -> float:
    """Return deterministic shortest-arc midpoint for two circular longitudes."""

    return normalize_longitude(normalize_longitude(a) + directed_circular_delta(a, b) / 2.0)

