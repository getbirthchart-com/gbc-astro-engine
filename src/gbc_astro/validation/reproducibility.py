"""Canonical deterministic serialization and hashing."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from gbc_astro.models.chart import NatalChart

VOLATILE_KEYS = {"runtime", "runtimeMs", "generatedAt"}


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


def canonical_json_for_hash(chart: NatalChart) -> str:
    return json.dumps(
        canonicalize_for_hash(chart.to_dict()),
        separators=(",", ":"),
        sort_keys=True,
    )


def calculation_hash(chart: NatalChart) -> str:
    return hashlib.sha256(canonical_json_for_hash(chart).encode("utf-8")).hexdigest()

