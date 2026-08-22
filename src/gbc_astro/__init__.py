"""Public package API for GetBirthChart astrology calculations."""

from gbc_astro.chart import (
    calculate_aspects,
    calculate_chart,
    calculate_houses,
    calculate_planet_positions,
    get_zodiac_sign,
    normalize_angle,
)
from gbc_astro.constants import ENGINE_VERSION, PACKAGE_VERSION, SCHEMA_VERSION
from gbc_astro.engine import AstrologyEngine
from gbc_astro.exceptions import (
    InvalidCoordinatesError,
    InvalidDateError,
    InvalidTimeError,
    MissingBirthTimeError,
    UnsupportedHouseSystemError,
)
from gbc_astro.houses.systems import SUPPORTED_HOUSE_SYSTEMS
from gbc_astro.profiles.defaults import WESTERN_MODERN_V1

__version__ = PACKAGE_VERSION

__all__ = [
    "AstrologyEngine",
    "ENGINE_VERSION",
    "SCHEMA_VERSION",
    "SUPPORTED_HOUSE_SYSTEMS",
    "WESTERN_MODERN_V1",
    "__version__",
    "calculate_aspects",
    "calculate_chart",
    "calculate_houses",
    "calculate_planet_positions",
    "get_zodiac_sign",
    "normalize_angle",
    "InvalidCoordinatesError",
    "InvalidDateError",
    "InvalidTimeError",
    "MissingBirthTimeError",
    "UnsupportedHouseSystemError",
]
