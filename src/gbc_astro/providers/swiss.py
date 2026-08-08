"""Swiss Ephemeris provider wrapper.

The implementation delegates astronomy to `pyswisseph`. The engine deliberately
does not provide fallback planetary formulas when this dependency is absent.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from importlib import import_module
from types import ModuleType
from typing import Any

from gbc_astro.astronomy.provider_time import julian_day_ut
from gbc_astro.constants import BODY_IDS
from gbc_astro.errors import EphemerisOutOfRangeError, ProviderDependencyError
from gbc_astro.models.position import RawBodyPosition
from gbc_astro.providers.asteroids import (
    OPTIONAL_BODIES,
    parse_numbered_asteroid,
    swisseph_code,
)
from gbc_astro.providers.base import ProviderCapabilities
from gbc_astro.providers.swiss_manifest import manifest_summary


def _load_swisseph() -> ModuleType:
    try:
        return import_module("swisseph")
    except ImportError as exc:
        raise ProviderDependencyError(
            "Swiss Ephemeris provider requires the optional 'pyswisseph' dependency.",
            {"install": 'python -m pip install "gbc-astro[swiss]"'},
        ) from exc


class SwissEphemerisProvider:
    """EphemerisProvider backed by pyswisseph."""

    id = "swiss"

    def __init__(self, ephemeris_path: str | None = None) -> None:
        self._swe = _load_swisseph()
        self.ephemeris_path = ephemeris_path or os.environ.get("GBC_SWISS_EPHE_PATH")
        if self.ephemeris_path:
            self._swe.set_ephe_path(self.ephemeris_path)
        self._body_codes = self._build_body_codes(self._swe)

    @property
    def data_version(self) -> str:
        version: Any = getattr(self._swe, "version", "unknown")
        return str(version() if callable(version) else version)

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_bodies=BODY_IDS,
            date_range=("-13200-01-01", "17191-01-01"),
            supports_speed=True,
            supports_latitude=True,
            supports_distance=True,
        )

    def supports_body(self, body: str) -> bool:
        if body in self._body_codes:
            return True
        # Optional bodies are resolved on demand: whether a numbered asteroid
        # works depends on a data file being present, which is a provisioning
        # question rather than a provider one.
        return body in OPTIONAL_BODIES or parse_numbered_asteroid(body) is not None

    def health_check(self) -> dict[str, object]:
        manifest = manifest_summary(self.ephemeris_path)
        available = []
        unavailable = []
        from datetime import datetime, timezone

        probe = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
        for body in self.capabilities.supported_bodies:
            try:
                self.position(body, probe)
            except Exception:
                unavailable.append(body)
            else:
                available.append(body)
        status = "ok" if not unavailable else "degraded"
        if manifest["missingRequiredData"]:
            status = "error"
        return {
            "status": status,
            "provider": self.id,
            "providerVersion": self.data_version,
            "ephemerisPath": self.ephemeris_path,
            "availableCapabilities": available,
            "unavailableCapabilities": unavailable,
            "manifest": manifest,
        }

    def position(self, body: str, instant_utc: datetime) -> RawBodyPosition:
        code = self._body_codes.get(body)
        if code is None:
            # Raises UnsupportedBodyError for anything genuinely unknown.
            code = swisseph_code(body, self._swe)
        utc_dt = instant_utc.astimezone(timezone.utc)
        jd_ut = julian_day_ut(utc_dt)
        flags = self._swe.FLG_SWIEPH | self._swe.FLG_SPEED
        try:
            result, _retflag = self._swe.calc_ut(jd_ut, code, flags)
        except Exception as exc:
            message = str(exc)
            if "not found" in message or "file" in message.lower():
                raise ProviderDependencyError(
                    "Swiss Ephemeris data file is missing for this calculation.",
                    {
                        "provider": self.id,
                        "body": body,
                        "instantUtc": utc_dt.isoformat(),
                        "ephemerisPath": self.ephemeris_path,
                        "hint": "Set GBC_SWISS_EPHE_PATH or pass --swiss-ephe-path.",
                    },
                ) from exc
            raise EphemerisOutOfRangeError(
                "Swiss Ephemeris could not calculate this body at the requested instant.",
                {"provider": self.id, "body": body, "instantUtc": utc_dt.isoformat()},
            ) from exc
        if not (_retflag & self._swe.FLG_SWIEPH):
            raise ProviderDependencyError(
                "Swiss Ephemeris data file is missing for this calculation.",
                {
                    "provider": self.id,
                    "body": body,
                    "instantUtc": utc_dt.isoformat(),
                    "ephemerisPath": self.ephemeris_path,
                    "retflag": int(_retflag),
                    "hint": (
                        "Provision matching sepl_*.se1/semo_*.se1 files and set "
                        "GBC_SWISS_EPHE_PATH or pass --swiss-ephe-path."
                    ),
                },
            )
        return RawBodyPosition(
            longitude_deg=float(result[0]),
            latitude_deg=float(result[1]),
            distance=float(result[2]),
            longitude_speed_deg_per_day=float(result[3]),
        )

    @staticmethod
    def _build_body_codes(swe: ModuleType) -> dict[str, int]:
        return {
            "sun": swe.SUN,
            "moon": swe.MOON,
            "mercury": swe.MERCURY,
            "venus": swe.VENUS,
            "mars": swe.MARS,
            "jupiter": swe.JUPITER,
            "saturn": swe.SATURN,
            "uranus": swe.URANUS,
            "neptune": swe.NEPTUNE,
            "pluto": swe.PLUTO,
            "true_node": swe.TRUE_NODE,
            "mean_node": swe.MEAN_NODE,
            "chiron": swe.CHIRON,
        }
