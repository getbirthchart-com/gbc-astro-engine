"""Structured exceptions for public API and adapters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class GbcAstroError(Exception):
    """Base class for errors that should map to stable API error codes."""

    code = "GBC_ASTRO_ERROR"

    def __init__(self, message: str, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = dict(details or {})

    def to_error_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class InvalidCoordinateError(GbcAstroError):
    code = "INVALID_COORDINATE"


class UnknownTimezoneError(GbcAstroError):
    code = "UNKNOWN_TIMEZONE"


class AmbiguousLocalTimeError(GbcAstroError):
    code = "AMBIGUOUS_LOCAL_TIME"


class NonexistentLocalTimeError(GbcAstroError):
    code = "NONEXISTENT_LOCAL_TIME"


class EphemerisOutOfRangeError(GbcAstroError):
    code = "EPHEMERIS_OUT_OF_RANGE"


class UnsupportedBodyError(GbcAstroError):
    code = "UNSUPPORTED_BODY"


class HouseCalculationUnavailableError(GbcAstroError):
    code = "HOUSE_CALCULATION_UNAVAILABLE"


class UnknownBirthTimeError(GbcAstroError):
    code = "UNKNOWN_BIRTH_TIME"


class InvalidCalculationProfileError(GbcAstroError):
    code = "INVALID_CALCULATION_PROFILE"


class ProviderDependencyError(GbcAstroError):
    code = "PROVIDER_DEPENDENCY_MISSING"

