"""Validation corpus loading helpers."""

from __future__ import annotations

import json
from pathlib import Path

from gbc_astro.validation.reference import ValidationCase


def load_validation_cases(path: str | Path) -> tuple[ValidationCase, ...]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return tuple(ValidationCase.from_dict(item) for item in payload)

