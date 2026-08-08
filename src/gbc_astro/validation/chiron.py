"""Chiron parity against a frozen JPL Horizons reference.

DE440S carries only the major planets, so the JPL track that validates Sun
through Pluto cannot reach Chiron. Horizons publishes its own small-body orbit
solution for 2060 Chiron, independent of the Swiss `seas_18.se1` integration the
engine uses, so a frozen sample of it is a valid independent reference under
`docs/HOUSE_REFERENCE_METHODOLOGY.md`.

The fixture is committed and read offline; this module never touches the
network. Regenerate it with `tools/fetch_chiron_horizons.py`.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from gbc_astro.astronomy.circular import shortest_angular_distance
from gbc_astro.constants import ENGINE_VERSION
from gbc_astro.providers.swiss import SwissEphemerisProvider

DEFAULT_FIXTURE_PATH = "tests/fixtures/chiron_horizons_reference.json"


@dataclass(frozen=True)
class ChironToleranceProfile:
    id: str
    version: str
    rationale: str
    longitude_deg: float
    latitude_deg: float


CHIRON_HORIZONS_V1 = ChironToleranceProfile(
    id="chiron-horizons-parity-v1",
    version="1.0.0",
    rationale=(
        "Compares Swiss apparent geocentric ecliptic-of-date Chiron against JPL "
        "Horizons QUANTITIES=31 for the same instants. The two rest on different "
        "orbit solutions for a minor planet whose osculating elements are perturbed "
        "by Saturn and Uranus, so looser agreement than the major planets would be "
        "unsurprising. Measured across the committed 1900-2026 corpus it is not: "
        "longitude agrees to 0.44 arcsecond at worst (p95 0.22) and latitude to "
        "0.18. The threshold is 0.001 deg (3.6 arcsecond), about eightfold headroom "
        "over the observed maximum and the same figure used for the major planets. "
        "Loosening it requires new measured evidence recorded in "
        "evidence/v0.1-validation/CHIRON_PARITY.md."
    ),
    longitude_deg=0.001,
    latitude_deg=0.001,
)


def load_chiron_fixture(path: str | Path = DEFAULT_FIXTURE_PATH) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload: dict[str, Any] = json.load(handle)
    if not payload.get("samples"):
        raise ValueError(f"Chiron fixture {path} has no samples.")
    return payload


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def run_chiron_parity(
    fixture: dict[str, Any],
    swiss_ephemeris_path: str | None = None,
    tolerance: ChironToleranceProfile = CHIRON_HORIZONS_V1,
) -> dict[str, Any]:
    swiss = SwissEphemerisProvider(ephemeris_path=swiss_ephemeris_path)

    longitude_deltas: list[float] = []
    latitude_deltas: list[float] = []
    outside: list[dict[str, Any]] = []

    for sample in fixture["samples"]:
        instant = datetime.fromisoformat(str(sample["utc"]).replace("Z", "+00:00"))
        actual = swiss.position("chiron", instant)

        longitude_delta = shortest_angular_distance(
            actual.longitude_deg, float(sample["longitudeDeg"])
        )
        latitude_delta = abs(actual.latitude_deg - float(sample["latitudeDeg"]))
        longitude_deltas.append(longitude_delta)
        latitude_deltas.append(latitude_delta)

        if (
            longitude_delta > tolerance.longitude_deg
            or latitude_delta > tolerance.latitude_deg
        ):
            outside.append(
                {
                    "utc": sample["utc"],
                    "longitudeDeltaDeg": longitude_delta,
                    "latitudeDeltaDeg": latitude_delta,
                }
            )

    status = "PASS" if not outside and longitude_deltas else "FAIL"
    return {
        "status": status,
        "engineVersion": ENGINE_VERSION,
        "reference": {
            "id": "jpl-horizons-2060-chiron",
            "source": fixture.get("source"),
            "target": fixture.get("target"),
            "frame": fixture.get("frame"),
            "capturedAt": fixture.get("capturedAt"),
            "independentOfSwissEphemeris": fixture.get("independentOfSwissEphemeris", True),
        },
        "tolerance": {
            "id": tolerance.id,
            "version": tolerance.version,
            "rationale": tolerance.rationale,
            "longitudeDeg": tolerance.longitude_deg,
            "latitudeDeg": tolerance.latitude_deg,
        },
        "sampleCount": len(longitude_deltas),
        "range": fixture.get("range"),
        "longitude": {
            "maxDeg": max(longitude_deltas) if longitude_deltas else 0.0,
            "p95Deg": _percentile(longitude_deltas, 0.95),
            "maxArcsec": (max(longitude_deltas) if longitude_deltas else 0.0) * 3600.0,
        },
        "latitude": {
            "maxDeg": max(latitude_deltas) if latitude_deltas else 0.0,
            "p95Deg": _percentile(latitude_deltas, 0.95),
            "maxArcsec": (max(latitude_deltas) if latitude_deltas else 0.0) * 3600.0,
        },
        "outsideToleranceCount": len(outside),
        "outsideTolerance": outside[:20],
    }
