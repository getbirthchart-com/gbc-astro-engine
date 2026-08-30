"""Canonical natal calculation identity and hashing.

v2 (active)
-----------
``calculation_hash`` returns a versioned digest ``v2:<sha256-hex>`` of a
canonical *calculation identity* payload. That payload is not
``NatalChart.to_dict()``. It contains normalized input, the settings that
change astronomical results, engine/ephemeris provenance, and normalized
positions/aspects. It omits warning prose, sign labels, and other
presentation-only fields.

v1 (legacy)
-----------
Unprefixed 64-character lowercase hex strings are treated as v1. v1 was
SHA-256 of the full canonical natal JSON document. The package no longer
emits v1 hashes. ``identify_calculation_hash`` still recognizes them so
stored artifacts can be classified. v1 and v2 values must not be compared
as equal or unequal evidence of the same calculation: they hash different
documents.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from gbc_astro.models.aspect import Aspect
from gbc_astro.models.chart import NatalChart
from gbc_astro.models.position import (
    AnglePosition,
    BodyPosition,
    DerivedPoint,
    HouseCusp,
)
from gbc_astro.models.relationship import SynastryChart

CALCULATION_HASH_VERSION = "v2"
LEGACY_CALCULATION_HASH_VERSION = "v1"
V2_PREFIX = "v2:"

VOLATILE_KEYS = {"runtime", "runtimeMs", "generatedAt"}
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class IdentifiedCalculationHash:
    """A stored or newly computed calculation-hash string, classified by version."""

    version: str
    digest: str
    encoded: str


def canonicalize_for_hash(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: canonicalize_for_hash(inner)
            for key, inner in sorted(value.items())
            if key not in VOLATILE_KEYS
        }
    if isinstance(value, list):
        return [canonicalize_for_hash(item) for item in value]
    return value


def _omit_none_dict(value: dict[str, Any]) -> dict[str, Any]:
    return {key: inner for key, inner in value.items() if inner is not None}


def _body_identity(body: BodyPosition) -> dict[str, Any]:
    return _omit_none_dict(
        {
            "longitude": body.longitude,
            "latitude": body.latitude,
            "distance": body.distance,
            "speedLongitude": body.speed_longitude,
            "retrograde": body.retrograde,
            "house": body.house,
        }
    )


def _angle_identity(angle: AnglePosition) -> dict[str, Any]:
    return {"longitude": angle.longitude}


def _house_identity(house: HouseCusp) -> dict[str, Any]:
    return {"number": house.number, "cuspLongitude": house.cusp_longitude}


def _point_identity(point: DerivedPoint) -> dict[str, Any]:
    return _omit_none_dict(
        {
            "longitude": point.longitude,
            "house": point.house,
            "method": point.method,
            "requiresBirthTime": point.requires_birth_time,
            "alternativeLongitude": point.alternative_longitude,
        }
    )


def _aspect_identity(aspect: Aspect) -> dict[str, Any]:
    return {
        "a": aspect.body_a,
        "b": aspect.body_b,
        "type": aspect.aspect_type,
        "exactAngle": aspect.exact_angle,
        "actualAngle": aspect.actual_angle,
        "orb": aspect.orb,
        "phase": aspect.phase,
    }


def calculation_identity_payload(chart: NatalChart) -> dict[str, Any]:
    """Return the canonical v2 identity document for ``chart``.

    Sign names, degree-in-sign labels, warning text, interpretive derived
    blocks, and incidental ``to_dict()`` conveniences are excluded.
    """

    meta = chart.meta
    subject = chart.subject
    aspects = sorted(
        (_aspect_identity(aspect) for aspect in chart.aspects),
        key=lambda row: (row["a"], row["b"], row["type"]),
    )
    houses = sorted(
        (_house_identity(house) for house in chart.houses),
        key=lambda row: row["number"],
    )
    payload = {
        "calculationHashVersion": CALCULATION_HASH_VERSION,
        "input": _omit_none_dict(
            {
                "localDateTime": subject.local_datetime,
                "utcDateTime": subject.utc_datetime,
                "timezone": subject.timezone,
                "latitude": subject.latitude,
                "longitude": subject.longitude,
                "altitudeM": subject.altitude_m,
                "birthTimeKnown": subject.birth_time_known,
                "calendar": subject.calendar,
                "julianDay": subject.julian_day,
            }
        ),
        "settings": _omit_none_dict(
            {
                "zodiac": meta.zodiac,
                "ayanamsa": meta.ayanamsa,
                "ayanamsaVersion": meta.ayanamsa_version,
                "ayanamsaDegrees": meta.ayanamsa_degrees,
                "houseSystem": meta.house_system,
                "requestedHouseSystem": meta.requested_house_system,
                "nodeType": meta.node_type,
                "aspectPreset": meta.aspect_preset,
                "aspectProfile": meta.aspect_profile,
                "aspectProfileVersion": meta.aspect_profile_version,
                "customAspectRules": (
                    [dict(rule) for rule in meta.custom_aspect_rules]
                    if meta.custom_aspect_rules is not None
                    else None
                ),
                "pointProfile": meta.point_profile,
                "pointProfileVersion": meta.point_profile_version,
                "calculationProfile": meta.calculation_profile,
                "additionalPoints": list(meta.additional_points),
            }
        ),
        "provenance": _omit_none_dict(
            {
                "engine": meta.engine,
                "engineVersion": meta.engine_version,
                "ephemerisProvider": meta.ephemeris_provider,
                "ephemerisDataVersion": meta.ephemeris_data_version,
                "timezoneDataVersion": meta.timezone_data_version,
                "houseAlgorithmVersion": meta.house_algorithm_version,
            }
        ),
        "results": {
            "bodies": {
                body_id: _body_identity(body)
                for body_id, body in sorted(chart.bodies.items())
            },
            "houses": houses,
            "angles": {
                name: _angle_identity(angle)
                for name, angle in sorted(chart.angles.items())
            },
            "aspects": aspects,
            "points": {
                point_id: _point_identity(point)
                for point_id, point in sorted(chart.points.items())
            },
        },
    }
    if chart.unknown_time_assessment is not None:
        payload["unknownTimeAssessment"] = chart.unknown_time_assessment.identity_dict()
    return payload


def synastry_identity_payload(chart: SynastryChart) -> dict[str, Any]:
    """Canonical v2 identity for a synastry result, including node convention."""

    cross_aspects = sorted(
        (
            {
                "a": aspect.body_a,
                "b": aspect.body_b,
                "type": aspect.aspect_type,
                "exactAngle": aspect.exact_angle,
                "actualAngle": aspect.actual_angle,
                "orb": aspect.orb,
                "phase": aspect.phase,
            }
            for aspect in chart.cross_aspects
        ),
        key=lambda row: (row["a"], row["b"], row["type"]),
    )
    return {
        "calculationHashVersion": CALCULATION_HASH_VERSION,
        "settings": _omit_none_dict(
            {
                "nodeType": chart.meta.node_type,
                "relationshipProfile": chart.meta.relationship_profile,
                "aspectProfile": chart.meta.aspect_profile,
                "zodiac": chart.meta.zodiac,
                "crossAspectPhasePolicy": chart.meta.cross_aspect_phase_policy,
            }
        ),
        "chartA": calculation_identity_payload(chart.chart_a),
        "chartB": calculation_identity_payload(chart.chart_b),
        "results": {
            "crossAspects": cross_aspects,
        },
    }


def synastry_hash(chart: SynastryChart) -> str:
    """Return the active (v2) identity hash for a synastry chart."""

    return encode_calculation_hash(synastry_identity_payload(chart))


def encode_calculation_hash(payload: dict[str, Any]) -> str:
    """SHA-256 of a canonical identity payload, encoded as ``v2:<hex>``."""

    canonical = json.dumps(
        canonicalize_for_hash(payload),
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{V2_PREFIX}{digest}"


def canonical_json_for_hash(chart: NatalChart) -> str:
    """Canonical JSON of the v2 identity payload (not the public natal document)."""

    return json.dumps(
        canonicalize_for_hash(calculation_identity_payload(chart)),
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )


def calculation_hash(chart: NatalChart) -> str:
    """Return the active (v2) calculation identity hash for ``chart``."""

    return encode_calculation_hash(calculation_identity_payload(chart))


def identify_calculation_hash(value: str) -> IdentifiedCalculationHash:
    """Classify a stored hash string as v1 (legacy unprefixed) or v2.

    v1 and v2 must not be compared directly. This helper only identifies
    which encoding a stored artifact uses.
    """

    if not isinstance(value, str) or not value:
        raise ValueError("Calculation hash must be a non-empty string.")
    if value.startswith(V2_PREFIX):
        digest = value[len(V2_PREFIX) :]
        if not _SHA256_HEX.fullmatch(digest):
            raise ValueError("Malformed v2 calculation hash.")
        return IdentifiedCalculationHash(
            version=CALCULATION_HASH_VERSION,
            digest=digest,
            encoded=value,
        )
    if _SHA256_HEX.fullmatch(value):
        return IdentifiedCalculationHash(
            version=LEGACY_CALCULATION_HASH_VERSION,
            digest=value,
            encoded=value,
        )
    raise ValueError("Unrecognized calculation hash encoding.")
