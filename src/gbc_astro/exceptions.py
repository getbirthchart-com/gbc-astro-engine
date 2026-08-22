"""Public exception aliases for the library API.

Implementation lives in `gbc_astro.errors`. This module is the stable import
path for package users.
"""

from gbc_astro.errors import (
    AmbiguousLocalTimeError,
    EphemerisOutOfRangeError,
    GbcAstroError,
    HouseCalculationUnavailableError,
    InvalidCalculationProfileError,
    InvalidCoordinateError,
    InvalidCoordinatesError,
    InvalidDateError,
    InvalidTimeError,
    MissingBirthTimeError,
    NonexistentLocalTimeError,
    ProviderDependencyError,
    UnknownBirthTimeError,
    UnknownTimezoneError,
    UnsupportedBodyError,
    UnsupportedHouseSystemError,
)

__all__ = [
    "AmbiguousLocalTimeError",
    "EphemerisOutOfRangeError",
    "GbcAstroError",
    "HouseCalculationUnavailableError",
    "InvalidCalculationProfileError",
    "InvalidCoordinateError",
    "InvalidCoordinatesError",
    "InvalidDateError",
    "InvalidTimeError",
    "MissingBirthTimeError",
    "NonexistentLocalTimeError",
    "ProviderDependencyError",
    "UnknownBirthTimeError",
    "UnknownTimezoneError",
    "UnsupportedBodyError",
    "UnsupportedHouseSystemError",
]
