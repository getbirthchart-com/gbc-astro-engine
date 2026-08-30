"""Resolve validated calculation-profile overrides from an immutable base.

One resolver. There is no second settings object beside `CalculationProfile`.
Public callers may override house system, node type, natal aspect settings,
and additional natal points.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from gbc_astro.errors import InvalidCalculationProfileError, UnsupportedHouseSystemError
from gbc_astro.houses.systems import HOUSE_SYSTEMS, PRODUCT_HOUSE_SYSTEMS
from gbc_astro.profiles.additional import apply_additional_points
from gbc_astro.profiles.aspects import apply_aspect_settings
from gbc_astro.profiles.defaults import WESTERN_MODERN_V1
from gbc_astro.profiles.model import CalculationProfile
from gbc_astro.profiles.nodes import profile_with_node_type
from gbc_astro.zodiac.sidereal import resolve_ayanamsa_profile


def resolve_calculation_profile(
    base: CalculationProfile = WESTERN_MODERN_V1,
    *,
    zodiac: str | None = None,
    ayanamsa: str | None = None,
    house_system: str | None = None,
    node_type: str | None = None,
    aspect_preset: str | None = None,
    custom_aspect_rules: Any = None,
    additional_points: Any = None,
) -> CalculationProfile:
    """Return `base` with validated overrides applied.

    An omitted override leaves the base field unchanged. An explicit value that
    equals the base field is a no-op, so omitted and explicit defaults compare
    equal (same profile identity). Node convention is applied through
    `profile_with_node_type`, never a raw `node_type` replace.
    """

    profile = base
    if house_system is not None:
        profile = _with_house_system(profile, house_system)
    if zodiac is not None or ayanamsa is not None:
        profile = _with_zodiac(profile, zodiac, ayanamsa)
    if node_type is not None:
        profile = profile_with_node_type(profile, node_type)
    if aspect_preset is not None or custom_aspect_rules is not None:
        profile = apply_aspect_settings(profile, aspect_preset, custom_aspect_rules)
    if additional_points is not None:
        profile = apply_additional_points(profile, additional_points)
    return profile


def _normalize_house_system(house_system: str) -> str:
    if not isinstance(house_system, str) or not house_system.strip():
        raise UnsupportedHouseSystemError(
            "Unsupported house system.",
            {
                "houseSystem": house_system,
                "supported": sorted(HOUSE_SYSTEMS),
                "productHouseSystems": list(PRODUCT_HOUSE_SYSTEMS),
            },
        )
    system = house_system.strip().lower()
    if system not in HOUSE_SYSTEMS:
        raise UnsupportedHouseSystemError(
            "Unsupported house system.",
            {
                "houseSystem": system,
                "supported": sorted(HOUSE_SYSTEMS),
                "productHouseSystems": list(PRODUCT_HOUSE_SYSTEMS),
            },
        )
    return system


def _with_house_system(profile: CalculationProfile, house_system: str) -> CalculationProfile:
    system = _normalize_house_system(house_system)
    if system == profile.house_system:
        return profile
    return replace(profile, house_system=system)


def _with_zodiac(
    profile: CalculationProfile,
    zodiac: str | None,
    ayanamsa: str | None,
) -> CalculationProfile:
    requested = (zodiac or profile.zodiac).strip().lower()
    if requested not in {"tropical", "sidereal"}:
        raise InvalidCalculationProfileError(
            "Unsupported zodiac.",
            {"zodiac": requested, "supported": ["tropical", "sidereal"], "field": "zodiac"},
        )
    if requested == "sidereal":
        selected_ayanamsa = ayanamsa if ayanamsa is not None else profile.ayanamsa
        if selected_ayanamsa is None:
            raise InvalidCalculationProfileError(
                "ayanamsa is required when zodiac is sidereal.",
                {"zodiac": "sidereal", "field": "ayanamsa"},
            )
        resolve_ayanamsa_profile(selected_ayanamsa)
        if profile.zodiac == "sidereal" and profile.ayanamsa == selected_ayanamsa:
            return profile
        return replace(
            profile,
            id=f"{profile.id}+sidereal-{selected_ayanamsa}",
            zodiac="sidereal",
            ayanamsa=selected_ayanamsa,
        )
    if ayanamsa is not None:
        raise InvalidCalculationProfileError(
            "ayanamsa is only meaningful when zodiac is sidereal.",
            {"zodiac": requested, "ayanamsa": ayanamsa, "field": "ayanamsa"},
        )
    if profile.zodiac == "tropical":
        return profile
    return replace(profile, id=f"{profile.id}+tropical", zodiac="tropical", ayanamsa=None)
