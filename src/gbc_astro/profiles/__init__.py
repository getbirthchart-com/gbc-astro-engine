"""Versioned calculation profiles."""

from gbc_astro.profiles.aspects import (
    MODERN_EXTENDED_V1,
    STANDARD_ASPECT_PROFILE,
)
from gbc_astro.profiles.defaults import MODERN_MAJOR_V1, WESTERN_MODERN_V1
from gbc_astro.profiles.model import AspectProfile, AspectRule, CalculationProfile
from gbc_astro.profiles.resolve import resolve_calculation_profile

__all__ = [
    "AspectProfile",
    "AspectRule",
    "CalculationProfile",
    "MODERN_EXTENDED_V1",
    "MODERN_MAJOR_V1",
    "STANDARD_ASPECT_PROFILE",
    "WESTERN_MODERN_V1",
    "resolve_calculation_profile",
]
