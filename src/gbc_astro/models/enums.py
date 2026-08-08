"""Stable enum identifiers used by the canonical contract."""

from __future__ import annotations

from enum import Enum


class StableEnum(str, Enum):
    """String enum that serializes to the stable identifier value."""

    def __str__(self) -> str:
        return str(self.value)


class HouseSystem(StableEnum):
    WHOLE_SIGN = "whole_sign"
    EQUAL = "equal"
    PLACIDUS = "placidus"


class AspectType(StableEnum):
    CONJUNCTION = "conjunction"
    SEXTILE = "sextile"
    SQUARE = "square"
    TRINE = "trine"
    OPPOSITION = "opposition"


class AspectPhase(StableEnum):
    APPLYING = "applying"
    SEPARATING = "separating"
    EXACT = "exact"
    INDETERMINATE = "indeterminate"


class WarningSeverity(StableEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
