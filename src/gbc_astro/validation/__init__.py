"""Validation and differential-testing helpers."""

from gbc_astro.validation.differential import (
    DifferentialMismatch,
    DifferentialReport,
    compare_natal,
)
from gbc_astro.validation.reference import (
    FixtureReferenceSource,
    JplReferenceSource,
    ReferenceNatalResult,
    ReferenceSource,
    ReferenceUnavailableError,
    ValidationCase,
)
from gbc_astro.validation.reproducibility import (
    CALCULATION_HASH_VERSION,
    calculation_hash,
    calculation_identity_payload,
    identify_calculation_hash,
    synastry_hash,
    synastry_identity_payload,
)
from gbc_astro.validation.tolerance import DEFAULT_V0_1_TOLERANCE, ToleranceProfile

__all__ = [
    "DEFAULT_V0_1_TOLERANCE",
    "DifferentialMismatch",
    "DifferentialReport",
    "FixtureReferenceSource",
    "JplReferenceSource",
    "ReferenceNatalResult",
    "ReferenceSource",
    "ReferenceUnavailableError",
    "ToleranceProfile",
    "ValidationCase",
    "CALCULATION_HASH_VERSION",
    "calculation_hash",
    "calculation_identity_payload",
    "identify_calculation_hash",
    "synastry_hash",
    "synastry_identity_payload",
    "compare_natal",
]
