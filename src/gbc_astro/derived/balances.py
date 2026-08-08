"""Element, modality, polarity, hemisphere and quadrant counts."""

from __future__ import annotations

from gbc_astro.models.position import BodyPosition

ELEMENT_BY_SIGN = {
    "aries": "fire",
    "leo": "fire",
    "sagittarius": "fire",
    "taurus": "earth",
    "virgo": "earth",
    "capricorn": "earth",
    "gemini": "air",
    "libra": "air",
    "aquarius": "air",
    "cancer": "water",
    "scorpio": "water",
    "pisces": "water",
}

MODALITY_BY_SIGN = {
    "aries": "cardinal",
    "cancer": "cardinal",
    "libra": "cardinal",
    "capricorn": "cardinal",
    "taurus": "fixed",
    "leo": "fixed",
    "scorpio": "fixed",
    "aquarius": "fixed",
    "gemini": "mutable",
    "virgo": "mutable",
    "sagittarius": "mutable",
    "pisces": "mutable",
}

POLARITY_BY_SIGN = {
    "aries": "positive",
    "gemini": "positive",
    "leo": "positive",
    "libra": "positive",
    "sagittarius": "positive",
    "aquarius": "positive",
    "taurus": "negative",
    "cancer": "negative",
    "virgo": "negative",
    "scorpio": "negative",
    "capricorn": "negative",
    "pisces": "negative",
}


def balance_counts(
    bodies: dict[str, BodyPosition],
    selected_body_ids: tuple[str, ...],
    mapping: dict[str, str],
    buckets: tuple[str, ...],
) -> dict[str, int]:
    counts = {bucket: 0 for bucket in buckets}
    for body_id in selected_body_ids:
        body = bodies.get(body_id)
        if body is None:
            continue
        counts[mapping[body.sign]] += 1
    return counts


def element_counts(
    bodies: dict[str, BodyPosition],
    selected_body_ids: tuple[str, ...],
) -> dict[str, int]:
    return balance_counts(
        bodies,
        selected_body_ids,
        ELEMENT_BY_SIGN,
        ("fire", "earth", "air", "water"),
    )


def modality_counts(
    bodies: dict[str, BodyPosition],
    selected_body_ids: tuple[str, ...],
) -> dict[str, int]:
    return balance_counts(
        bodies,
        selected_body_ids,
        MODALITY_BY_SIGN,
        ("cardinal", "fixed", "mutable"),
    )


def polarity_counts(
    bodies: dict[str, BodyPosition],
    selected_body_ids: tuple[str, ...],
) -> dict[str, int]:
    return balance_counts(bodies, selected_body_ids, POLARITY_BY_SIGN, ("positive", "negative"))


def hemisphere_counts(
    bodies: dict[str, BodyPosition],
    selected_body_ids: tuple[str, ...],
) -> dict[str, int]:
    counts = {"above_horizon": 0, "below_horizon": 0, "eastern": 0, "western": 0}
    for body_id in selected_body_ids:
        body = bodies.get(body_id)
        if body is None or body.house is None:
            continue
        if 1 <= body.house <= 6:
            counts["below_horizon"] += 1
        else:
            counts["above_horizon"] += 1
        if body.house in {10, 11, 12, 1, 2, 3}:
            counts["eastern"] += 1
        else:
            counts["western"] += 1
    return counts


def quadrant_counts(
    bodies: dict[str, BodyPosition],
    selected_body_ids: tuple[str, ...],
) -> dict[str, int]:
    counts = {"q1": 0, "q2": 0, "q3": 0, "q4": 0}
    for body_id in selected_body_ids:
        body = bodies.get(body_id)
        if body is None or body.house is None:
            continue
        if 1 <= body.house <= 3:
            counts["q1"] += 1
        elif 4 <= body.house <= 6:
            counts["q2"] += 1
        elif 7 <= body.house <= 9:
            counts["q3"] += 1
        else:
            counts["q4"] += 1
    return counts
