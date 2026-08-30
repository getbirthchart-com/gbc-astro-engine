"""Product-facing additional natal points.

Lilith variants are optional ephemeris bodies and are never added to default
`BODY_IDS` or Standard aspect bodies. Vertex and Part of Fortune remain the
existing derived points: they are produced when birth time is known, and they
are omitted (not invented from midnight) when it is not.

Selecting Vertex or Part of Fortune in `additional_points` is allowed as an
explicit request; it does not change default known-time output. Selecting a
Lilith id adds that body to the chart and to calculation identity.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.profiles.model import CalculationProfile

MEAN_LILITH = "mean_lilith"
TRUE_LILITH = "true_lilith"
PART_OF_FORTUNE = "part_of_fortune"
VERTEX = "vertex"

PRODUCT_ADDITIONAL_POINTS: tuple[str, ...] = (
    MEAN_LILITH,
    TRUE_LILITH,
    PART_OF_FORTUNE,
    VERTEX,
)

LILITH_BODY_IDS: frozenset[str] = frozenset({MEAN_LILITH, TRUE_LILITH})
TIME_SENSITIVE_ADDITIONAL_POINTS: frozenset[str] = frozenset(
    {PART_OF_FORTUNE, VERTEX}
)

_ALIASES: dict[str, str] = {
    "osculating_lilith": TRUE_LILITH,
}


def normalize_additional_points(raw: Any) -> tuple[str, ...]:
    """Return canonical, de-duplicated, product-order additional point ids."""

    if raw is None:
        return ()
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise InvalidCalculationProfileError(
            "additional_points must be a list of point identifiers.",
            {"field": "additional_points"},
        )
    selected: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        canonical = _canonical_point_id(item, index)
        if canonical in seen:
            raise InvalidCalculationProfileError(
                "additional_points must not contain duplicate identifiers.",
                {
                    "field": "additional_points",
                    "duplicate": canonical,
                    "index": index,
                },
            )
        seen.add(canonical)
        selected.append(canonical)
    return tuple(point for point in PRODUCT_ADDITIONAL_POINTS if point in seen)


def additional_body_ids(additional_points: tuple[str, ...]) -> tuple[str, ...]:
    """Lilith bodies to fetch from the ephemeris. Never includes default planets."""

    return tuple(point for point in additional_points if point in LILITH_BODY_IDS)


def apply_additional_points(
    profile: CalculationProfile,
    additional_points: Any,
) -> CalculationProfile:
    normalized = normalize_additional_points(additional_points)
    if normalized == profile.additional_points:
        return profile
    return replace(profile, additional_points=normalized)


def _canonical_point_id(raw: Any, index: int) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise InvalidCalculationProfileError(
            "Unknown additional point identifier.",
            {
                "field": "additional_points",
                "index": index,
                "additionalPoint": raw,
                "supported": list(PRODUCT_ADDITIONAL_POINTS),
                "aliases": sorted(_ALIASES),
            },
        )
    requested = raw.strip().lower()
    canonical = _ALIASES.get(requested, requested)
    if canonical not in PRODUCT_ADDITIONAL_POINTS:
        raise InvalidCalculationProfileError(
            "Unknown additional point identifier.",
            {
                "field": "additional_points",
                "index": index,
                "additionalPoint": requested,
                "supported": list(PRODUCT_ADDITIONAL_POINTS),
                "aliases": sorted(_ALIASES),
            },
        )
    return canonical
