"""Swiss Ephemeris data manifest and health helpers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

CORE_PLANETARY_BODIES = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
    "true_node",
    "mean_node",
)

PLANETARY_FILE_BODIES = tuple(body for body in CORE_PLANETARY_BODIES if body != "moon")
CHIRON_BODIES = ("chiron",)


@dataclass(frozen=True)
class EphemerisDataFile:
    filename: str
    purpose: str
    required_for: tuple[str, ...]
    required: bool
    sha256: str | None = None


SWISS_DATA_FILES = (
    EphemerisDataFile(
        filename="sepl_18.se1",
        purpose=(
            "Swiss planetary ephemeris for the v0.1 production validation range "
            "covering 1900-2026."
        ),
        required_for=PLANETARY_FILE_BODIES,
        required=True,
    ),
    EphemerisDataFile(
        filename="semo_18.se1",
        purpose=(
            "Swiss lunar ephemeris for the v0.1 production validation range "
            "covering 1900-2026."
        ),
        required_for=("moon",),
        required=True,
    ),
    EphemerisDataFile(
        filename="seas_18.se1",
        purpose="Chiron and asteroid-style Swiss Ephemeris calculations around modern eras.",
        required_for=CHIRON_BODIES,
        required=False,
    ),
)


def manifest_summary(ephemeris_path: str | None) -> dict[str, object]:
    path = Path(ephemeris_path).expanduser() if ephemeris_path else None
    files = []
    missing_optional: list[str] = []
    missing_required: list[str] = []
    for entry in SWISS_DATA_FILES:
        file_path = path / entry.filename if path else None
        exists = bool(file_path and file_path.exists())
        checksum = _sha256(file_path) if file_path and exists else None
        if not exists:
            if entry.required:
                missing_required.append(entry.filename)
            else:
                missing_optional.append(entry.filename)
        files.append(
            {
                "filename": entry.filename,
                "purpose": entry.purpose,
                "requiredFor": list(entry.required_for),
                "required": entry.required,
                "exists": exists,
                "sha256": checksum,
                "expectedSha256": entry.sha256,
            }
        )
    status = "ok"
    if missing_required:
        status = "error"
    elif missing_optional:
        status = "degraded"
    return {
        "status": status,
        "ephemerisPath": str(path) if path else None,
        "coreBodies": list(CORE_PLANETARY_BODIES),
        "chironBodies": list(CHIRON_BODIES),
        "files": files,
        "missingRequiredData": missing_required,
        "missingOptionalData": missing_optional,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
