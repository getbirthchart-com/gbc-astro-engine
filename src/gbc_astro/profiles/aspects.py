"""Natal aspect presets and custom-rule validation.

`standard` is an alias for the existing `modern-major-v1` profile object, not a
second rule table. `extended` is a versioned superset. `custom` is built from a
normalized, sorted rule list so equivalent requests share identity and hash.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from gbc_astro.errors import InvalidCalculationProfileError
from gbc_astro.profiles.defaults import MODERN_MAJOR_V1
from gbc_astro.profiles.model import AspectProfile, AspectRule, CalculationProfile

STANDARD_ASPECT_PRESET = "standard"
EXTENDED_ASPECT_PRESET = "extended"
CUSTOM_ASPECT_PRESET = "custom"

# Same object as the legacy default. Do not copy the rules into a new table.
STANDARD_ASPECT_PROFILE = MODERN_MAJOR_V1

MODERN_EXTENDED_V1 = AspectProfile(
    id="modern-extended-v1",
    version="1.0.0",
    rules=MODERN_MAJOR_V1.rules
    + (
        AspectRule("semisextile", 30.0, 2.0),
        AspectRule("semisquare", 45.0, 2.0),
        AspectRule("sesquiquadrate", 135.0, 2.0),
        AspectRule("quincunx", 150.0, 3.0),
    ),
)

CUSTOM_ASPECT_PROFILE_VERSION = "1.0.0"
MAX_NATAL_ASPECT_ORB = 15.0
MIN_EXACT_ANGLE = 0.0
MAX_EXACT_ANGLE = 180.0
_ANGLE_EPSILON = 1e-6

CANONICAL_ASPECT_ANGLES: dict[str, float] = {
    "conjunction": 0.0,
    "semisextile": 30.0,
    "semisquare": 45.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "sesquiquadrate": 135.0,
    "quincunx": 150.0,
    "opposition": 180.0,
}

_PRESET_ALIASES: dict[str, str] = {
    "standard": STANDARD_ASPECT_PRESET,
    "modern-major-v1": STANDARD_ASPECT_PRESET,
    "extended": EXTENDED_ASPECT_PRESET,
    "modern-extended-v1": EXTENDED_ASPECT_PRESET,
    "custom": CUSTOM_ASPECT_PRESET,
}

_PRESET_PROFILES: dict[str, AspectProfile] = {
    STANDARD_ASPECT_PRESET: STANDARD_ASPECT_PROFILE,
    EXTENDED_ASPECT_PRESET: MODERN_EXTENDED_V1,
}


def normalize_aspect_preset(aspect_preset: str) -> str:
    """Return the canonical preset name (`standard`, `extended`, or `custom`)."""

    if not isinstance(aspect_preset, str) or not aspect_preset.strip():
        raise InvalidCalculationProfileError(
            "Unsupported aspect preset.",
            {
                "aspectPreset": aspect_preset,
                "supported": ["standard", "extended", "custom"],
                "aliases": ["modern-major-v1", "modern-extended-v1"],
                "field": "aspect_preset",
            },
        )
    normalized = aspect_preset.strip().lower()
    preset = _PRESET_ALIASES.get(normalized)
    if preset is None:
        raise InvalidCalculationProfileError(
            "Unsupported aspect preset.",
            {
                "aspectPreset": normalized,
                "supported": ["standard", "extended", "custom"],
                "aliases": ["modern-major-v1", "modern-extended-v1"],
                "field": "aspect_preset",
            },
        )
    return preset


def serialize_aspect_rules(
    rules: Sequence[AspectRule],
) -> list[dict[str, str | float]]:
    """Stable public identity for a rule set: sorted by type, angle, then orb."""

    ordered = sorted(
        rules, key=lambda rule: (rule.aspect_type, rule.exact_angle, rule.orb)
    )
    return [
        {
            "type": rule.aspect_type,
            "exactAngle": rule.exact_angle,
            "orb": rule.orb,
        }
        for rule in ordered
    ]


def custom_aspect_profile_id(rules: Sequence[AspectRule]) -> str:
    """Authoritative identity for a custom rule set.

    The suffix is the full lowercase SHA-256 of the normalized, order-canonical
    rule list. Presentation layers may truncate for display; serialized
    ``meta.aspectProfile`` must not.
    """
    canonical = json.dumps(
        serialize_aspect_rules(rules),
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"custom-v1:{digest}"


def custom_aspect_profile(rules: tuple[AspectRule, ...]) -> AspectProfile:
    return AspectProfile(
        id=custom_aspect_profile_id(rules),
        version=CUSTOM_ASPECT_PROFILE_VERSION,
        rules=rules,
    )


def serialized_custom_aspect_rules(
    profile: CalculationProfile,
) -> tuple[dict[str, str | float], ...] | None:
    if profile.aspect_preset != CUSTOM_ASPECT_PRESET:
        return None
    return tuple(serialize_aspect_rules(profile.aspect_profile.rules))


def normalize_custom_aspect_rules(raw: Any) -> tuple[AspectRule, ...]:
    """Parse, validate, and sort custom natal aspect rules."""

    if raw is None:
        raise InvalidCalculationProfileError(
            "aspect_preset custom requires custom_aspect_rules.",
            {"field": "custom_aspect_rules", "aspectPreset": CUSTOM_ASPECT_PRESET},
        )
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise InvalidCalculationProfileError(
            "custom_aspect_rules must be a list of aspect rules.",
            {"field": "custom_aspect_rules"},
        )
    if len(raw) == 0:
        raise InvalidCalculationProfileError(
            "custom_aspect_rules must not be empty.",
            {"field": "custom_aspect_rules"},
        )

    parsed = tuple(_parse_custom_rule(item, index) for index, item in enumerate(raw))
    seen: set[tuple[str, float]] = set()
    for rule in parsed:
        key = (rule.aspect_type, rule.exact_angle)
        if key in seen:
            raise InvalidCalculationProfileError(
                "custom_aspect_rules must not repeat the same aspect type and angle.",
                {
                    "field": "custom_aspect_rules",
                    "type": rule.aspect_type,
                    "exactAngle": rule.exact_angle,
                },
            )
        seen.add(key)
    return tuple(
        sorted(parsed, key=lambda rule: (rule.aspect_type, rule.exact_angle, rule.orb))
    )


def apply_aspect_settings(
    profile: CalculationProfile,
    aspect_preset: str | None,
    custom_aspect_rules: Any,
) -> CalculationProfile:
    """Apply a validated natal aspect override, or return `profile` unchanged."""

    if aspect_preset is None and custom_aspect_rules is None:
        return profile

    if custom_aspect_rules is not None:
        requested = (
            normalize_aspect_preset(aspect_preset)
            if aspect_preset is not None
            else None
        )
        if requested != CUSTOM_ASPECT_PRESET:
            raise InvalidCalculationProfileError(
                "custom_aspect_rules is only valid when aspect_preset is custom.",
                {
                    "field": "custom_aspect_rules",
                    "aspectPreset": aspect_preset,
                },
            )

    if aspect_preset is None:
        return profile

    preset = normalize_aspect_preset(aspect_preset)
    if preset == CUSTOM_ASPECT_PRESET:
        rules = normalize_custom_aspect_rules(custom_aspect_rules)
        aspect_profile = custom_aspect_profile(rules)
        if (
            profile.aspect_preset == CUSTOM_ASPECT_PRESET
            and profile.aspect_profile.id == aspect_profile.id
            and profile.aspect_profile.rules == rules
        ):
            return profile
        return replace(
            profile,
            aspect_profile=aspect_profile,
            aspect_preset=CUSTOM_ASPECT_PRESET,
        )

    if custom_aspect_rules is not None:
        raise InvalidCalculationProfileError(
            "custom_aspect_rules is only valid when aspect_preset is custom.",
            {"field": "custom_aspect_rules", "aspectPreset": preset},
        )

    target = _PRESET_PROFILES[preset]
    if profile.aspect_preset == preset and profile.aspect_profile is target:
        return profile
    if (
        profile.aspect_preset == preset
        and profile.aspect_profile.id == target.id
        and profile.aspect_profile.rules == target.rules
    ):
        return profile
    return replace(profile, aspect_profile=target, aspect_preset=preset)


def _parse_custom_rule(raw: Any, index: int) -> AspectRule:
    aspect_type: Any
    exact_angle: Any
    orb: Any
    if isinstance(raw, AspectRule):
        aspect_type = raw.aspect_type
        exact_angle = raw.exact_angle
        orb = raw.orb
    elif isinstance(raw, Mapping):
        aspect_type = raw.get("type", raw.get("aspect_type", raw.get("aspectType")))
        exact_angle = raw.get("exact_angle", raw.get("exactAngle"))
        orb = raw.get("orb")
    else:
        raise InvalidCalculationProfileError(
            "Each custom aspect rule must be an object with type, exactAngle, and orb.",
            {"field": "custom_aspect_rules", "index": index},
        )

    if not isinstance(aspect_type, str) or not aspect_type.strip():
        raise InvalidCalculationProfileError(
            "Unknown aspect type.",
            {
                "field": "custom_aspect_rules",
                "index": index,
                "aspectType": aspect_type,
                "supported": sorted(CANONICAL_ASPECT_ANGLES),
            },
        )
    aspect_type = aspect_type.strip().lower()
    canonical_angle = CANONICAL_ASPECT_ANGLES.get(aspect_type)
    if canonical_angle is None:
        raise InvalidCalculationProfileError(
            "Unknown aspect type.",
            {
                "field": "custom_aspect_rules",
                "index": index,
                "aspectType": aspect_type,
                "supported": sorted(CANONICAL_ASPECT_ANGLES),
            },
        )

    angle = _require_finite_number(exact_angle, "exactAngle", index)
    if angle < MIN_EXACT_ANGLE or angle > MAX_EXACT_ANGLE:
        raise InvalidCalculationProfileError(
            "exactAngle is outside the supported range [0, 180].",
            {
                "field": "custom_aspect_rules",
                "index": index,
                "exactAngle": angle,
                "minExactAngle": MIN_EXACT_ANGLE,
                "maxExactAngle": MAX_EXACT_ANGLE,
            },
        )
    if abs(angle - canonical_angle) > _ANGLE_EPSILON:
        raise InvalidCalculationProfileError(
            "exactAngle must match the canonical geometry of the named aspect type.",
            {
                "field": "custom_aspect_rules",
                "index": index,
                "aspectType": aspect_type,
                "exactAngle": angle,
                "canonicalExactAngle": canonical_angle,
            },
        )

    orb_value = _require_finite_number(orb, "orb", index)
    if orb_value < 0:
        raise InvalidCalculationProfileError(
            "Aspect orb must not be negative.",
            {"field": "custom_aspect_rules", "index": index, "orb": orb_value},
        )
    if orb_value > MAX_NATAL_ASPECT_ORB:
        raise InvalidCalculationProfileError(
            "Aspect orb exceeds the documented natal maximum.",
            {
                "field": "custom_aspect_rules",
                "index": index,
                "orb": orb_value,
                "maxOrb": MAX_NATAL_ASPECT_ORB,
            },
        )
    return AspectRule(aspect_type, canonical_angle, orb_value)


def _require_finite_number(value: Any, name: str, index: int) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidCalculationProfileError(
            f"{name} must be a finite number.",
            {"field": "custom_aspect_rules", "index": index, name: value},
        )
    number = float(value)
    if not math.isfinite(number):
        raise InvalidCalculationProfileError(
            f"{name} must be a finite number.",
            {"field": "custom_aspect_rules", "index": index, name: number},
        )
    return number
