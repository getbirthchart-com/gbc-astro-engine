"""Validation-only independent reference abstractions."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol

from gbc_astro.astronomy.circular import directed_circular_delta
from gbc_astro.astronomy.time import normalize_local_datetime
from gbc_astro.errors import ProviderDependencyError, UnsupportedBodyError


@dataclass(frozen=True)
class ValidationCase:
    id: str
    local_datetime: str
    timezone: str
    latitude: float
    longitude: float
    house_system: str
    reason: str
    expected_behavior: str
    unknown_time: bool = False
    fold: int | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ValidationCase:
        fold_value = payload.get("fold")
        return cls(
            id=str(payload["id"]),
            local_datetime=str(payload["local_datetime"]),
            timezone=str(payload["timezone"]),
            latitude=float(payload["latitude"]),
            longitude=float(payload["longitude"]),
            house_system=str(payload["house_system"]),
            reason=str(payload["reason"]),
            expected_behavior=str(payload["expected_behavior"]),
            unknown_time=bool(payload.get("unknown_time", False)),
            fold=None if fold_value is None else int(fold_value),
        )


@dataclass(frozen=True)
class ReferenceNatalResult:
    case_id: str
    source_id: str
    source_version: str
    chart: dict[str, Any]
    notes: str


@dataclass(frozen=True)
class ReferenceBodyPosition:
    body_id: str
    longitude_deg: float
    latitude_deg: float
    longitude_speed_deg_per_day: float | None
    retrograde: bool | None


class ReferenceUnavailableError(RuntimeError):
    """Raised when an independent reference source is unavailable."""


class ReferenceSource(Protocol):
    id: str
    version: str

    def natal_reference(self, case: ValidationCase) -> ReferenceNatalResult:
        ...


class FixtureReferenceSource:
    """Validation source backed by externally captured canonical JSON fixtures."""

    id = "external-fixture"

    def __init__(self, fixture_path: str | Path, version: str = "unversioned") -> None:
        self.version = version
        path = Path(fixture_path)
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        self._fixtures: dict[str, dict[str, Any]] = {
            str(item["case_id"]): item for item in payload.get("fixtures", [])
        }

    def natal_reference(self, case: ValidationCase) -> ReferenceNatalResult:
        fixture = self._fixtures.get(case.id)
        if fixture is None:
            raise ReferenceUnavailableError(f"No reference fixture exists for case {case.id}.")
        return ReferenceNatalResult(
            case_id=case.id,
            source_id=self.id,
            source_version=self.version,
            chart=fixture["chart"],
            notes=str(fixture.get("notes", "")),
        )


class JplReferenceSource:
    """JPL DE440S reference path through Skyfield, independent of Swiss Ephemeris."""

    id = "jpl-de440"
    version = "DE440S"
    supported_bodies = (
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

    _target_by_body = {
        "sun": "sun",
        "moon": "moon",
        "mercury": "mercury",
        "venus": "venus",
        "mars": "mars barycenter",
        "jupiter": "jupiter barycenter",
        "saturn": "saturn barycenter",
        "uranus": "uranus barycenter",
        "neptune": "neptune barycenter",
        "pluto": "pluto barycenter",
    }

    _NODE_BODIES = ("true_node", "mean_node")

    def __init__(self, ephemeris_path: str | Path | None = None) -> None:
        configured = ephemeris_path or os.environ.get("GBC_JPL_EPHEMERIS_PATH")
        if not configured:
            raise ReferenceUnavailableError(
                "GBC_JPL_EPHEMERIS_PATH or --jpl-ephemeris-path is required."
            )
        path = Path(configured).expanduser()
        if path.is_dir():
            path = path / "de440s.bsp"
        if not path.exists():
            raise ReferenceUnavailableError(f"JPL ephemeris kernel not found: {path}")
        self.ephemeris_path = path
        try:
            skyfield_api = import_module("skyfield.api")
        except ImportError as exc:
            raise ProviderDependencyError(
                "JPL reference validation requires the optional 'skyfield' dependency.",
                {"install": 'python -m pip install "gbc-astro[validation]"'},
            ) from exc
        self._load = skyfield_api.load
        self._timescale = self._load.timescale()
        self._ephemeris = self._load(str(path))
        self._osculating_elements_of = import_module("skyfield.elementslib").osculating_elements_of
        self._build_ecliptic_matrix = import_module("skyfield.framelib").build_ecliptic_matrix
        self._earth_tilt = import_module("skyfield.nutationlib").earth_tilt

    def health_check(self) -> dict[str, object]:
        return {
            "status": "ok",
            "reference": self.id,
            "dataPath": str(self.ephemeris_path),
            "dataVersion": self.version,
            "supportedBodies": list(self.supported_bodies),
            "supportedDateRange": ["1849-12-25", "2150-01-21"],
        }

    def natal_reference(self, case: ValidationCase) -> ReferenceNatalResult:
        time_norm = normalize_local_datetime(
            datetime.fromisoformat(case.local_datetime),
            case.timezone,
            fold=case.fold,
        )
        bodies = {
            body: self.body_position(body, time_norm.utc_datetime).__dict__
            for body in self.supported_bodies
        }
        return ReferenceNatalResult(
            case_id=case.id,
            source_id=self.id,
            source_version=self.version,
            chart={"bodies": bodies},
            notes="JPL astronomy reference only; angles/houses are not supplied.",
        )

    def body_position(self, body: str, instant_utc: datetime) -> ReferenceBodyPosition:
        if body not in self._target_by_body and body not in self._NODE_BODIES:
            raise UnsupportedBodyError(
                "JPL reference source does not support this body.",
                {"body": body, "reference": self.id},
            )
        longitude, latitude = self._longitude_latitude(body, instant_utc)
        speed = self._longitude_speed(body, instant_utc)
        return ReferenceBodyPosition(
            body_id=body,
            longitude_deg=longitude,
            latitude_deg=latitude,
            longitude_speed_deg_per_day=speed,
            retrograde=speed < 0,
        )

    def _longitude_speed(self, body: str, instant_utc: datetime) -> float:
        step_seconds = 60
        step = timedelta(seconds=step_seconds)
        current = instant_utc
        previous = current - step
        following = current + step

        if previous.date() == current.date() and following.date() == current.date():
            earlier_longitude, _earlier_latitude = self._longitude_latitude(body, previous)
            later_longitude, _later_latitude = self._longitude_latitude(body, following)
            return directed_circular_delta(earlier_longitude, later_longitude) / (
                2 * step_seconds / 86400.0
            )

        current_longitude, _current_latitude = self._longitude_latitude(body, current)
        if following.date() == current.date():
            following_longitude, _following_latitude = self._longitude_latitude(body, following)
            return directed_circular_delta(current_longitude, following_longitude) / (
                step_seconds / 86400.0
            )

        previous_longitude, _previous_latitude = self._longitude_latitude(body, previous)
        return directed_circular_delta(previous_longitude, current_longitude) / (
            step_seconds / 86400.0
        )

    def _longitude_latitude(self, body: str, instant_utc: datetime) -> tuple[float, float]:
        t = self._time(instant_utc)
        if body in self._NODE_BODIES:
            # Both lunar nodes lie on the ecliptic by definition, so latitude is
            # exactly zero rather than a computed quantity.
            return self._node_longitude(body, t), 0.0
        target = self._target_by_body[body]
        apparent = self._ephemeris["earth"].at(t).observe(self._ephemeris[target]).apparent()
        latitude, longitude, _distance = apparent.ecliptic_latlon(epoch="date")
        return float(longitude.degrees), float(latitude.degrees)

    def _node_longitude(self, body: str, t: Any) -> float:
        """Longitude of the ascending lunar node, referred to the true equinox of date.

        `true_node` is the osculating node: the ascending node of the Moon's
        instantaneous geocentric orbit, taken from Skyfield's osculating elements
        in the ecliptic frame of date.

        `mean_node` uses the mean-element polynomial for the Moon's ascending
        node (Meeus, *Astronomical Algorithms*, ch. 47). That series is referred
        to the *mean* equinox of date, while Swiss Ephemeris reports the node
        against the *true* equinox, so nutation in longitude is added. Without
        that term the two disagree by up to 17 arcseconds, tracking the nutation
        cycle exactly; with it they agree to about 0.1 arcsecond.
        """
        if body == "true_node":
            geocentric_moon = (self._ephemeris["moon"] - self._ephemeris["earth"]).at(t)
            elements = self._osculating_elements_of(
                geocentric_moon,
                reference_frame=self._build_ecliptic_matrix(t),
            )
            return float(elements.longitude_of_ascending_node.degrees) % 360.0

        centuries = (float(t.tt) - 2451545.0) / 36525.0
        mean_node = (
            125.0445479
            - 1934.1362891 * centuries
            + 0.0020754 * centuries**2
            + centuries**3 / 467441.0
            - centuries**4 / 60616000.0
        )
        nutation_in_longitude_arcsec = float(self._earth_tilt(t)[3])
        return (mean_node + nutation_in_longitude_arcsec / 3600.0) % 360.0

    def _time(self, instant_utc: datetime) -> Any:
        return self._timescale.utc(
            instant_utc.year,
            instant_utc.month,
            instant_utc.day,
            instant_utc.hour,
            instant_utc.minute,
            instant_utc.second + instant_utc.microsecond / 1_000_000.0,
        )
