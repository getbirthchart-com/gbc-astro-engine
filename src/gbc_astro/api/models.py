"""Pydantic request models for the HTTP adapter.

Field names are HTTP-friendly; mapping into AstrologyEngine.natal(...) is explicit
in the natal route. Canonical chart responses use NatalChart.to_dict().
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HouseSystem(str, Enum):
    """House systems supported by AstrologyEngine.natal."""

    placidus = "placidus"
    whole_sign = "whole_sign"
    equal = "equal"


class NatalChartRequest(BaseModel):
    """Natal chart calculation request.

    Preserves local civil date + optional local clock time + IANA timezone.
    The engine owns historical timezone / DST interpretation — clients must not
    pre-convert to UTC.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "local_date": "1996-06-14",
                    "local_time": "04:12",
                    "unknown_time": False,
                    "timezone": "Europe/Lisbon",
                    "latitude": 38.7223,
                    "longitude": -9.1393,
                },
                {
                    "local_date": "1996-06-14",
                    "local_time": None,
                    "unknown_time": True,
                    "timezone": "Europe/Lisbon",
                    "latitude": 38.7223,
                    "longitude": -9.1393,
                },
            ]
        },
    )

    local_date: str = Field(
        ...,
        description="Local civil birth date as YYYY-MM-DD.",
        json_schema_extra={"examples": ["1996-06-14"]},
    )
    local_time: str | None = Field(
        default=None,
        description=(
            "Local clock time as HH:MM or HH:MM:SS when birth time is known. "
            "Must be null when unknown_time is true."
        ),
        json_schema_extra={"examples": ["04:12", "04:12:00"]},
    )
    unknown_time: bool = Field(
        default=False,
        description=(
            "When true, birth time is unknown. Angles/houses are omitted by the "
            "engine; local_time must be null."
        ),
    )
    timezone: str = Field(
        ...,
        min_length=1,
        description="IANA timezone identifier (not a fixed UTC offset).",
        json_schema_extra={"examples": ["Europe/Lisbon", "Asia/Ho_Chi_Minh"]},
    )
    latitude: float = Field(..., description="WGS84 latitude in degrees (-90 to 90).")
    longitude: float = Field(..., description="WGS84 longitude in degrees (-180 to 180).")
    altitude_m: float | None = Field(
        default=None,
        description="Optional altitude in meters.",
    )
    house_system: HouseSystem | None = Field(
        default=None,
        description=(
            "House system. Defaults to the engine calculation profile "
            "(western-modern-v1 → placidus). No silent fallback between systems."
        ),
    )
    fold: Literal[0, 1] | None = Field(
        default=None,
        description=(
            "Optional PEP 495 fold for ambiguous local times. Do not invent a fold; "
            "omit and surface AMBIGUOUS_LOCAL_TIME when unresolved."
        ),
    )

    @field_validator("local_date")
    @classmethod
    def validate_local_date(cls, value: str) -> str:
        raw = value.strip()
        if len(raw) != 10 or raw[4] != "-" or raw[7] != "-":
            raise ValueError("local_date must be YYYY-MM-DD.")
        # Validate via fromisoformat without importing datetime parsing elsewhere.
        from datetime import date

        try:
            date.fromisoformat(raw)
        except ValueError as exc:
            raise ValueError("local_date must be a valid calendar date.") from exc
        return raw

    @field_validator("local_time")
    @classmethod
    def validate_local_time(cls, value: str | None) -> str | None:
        if value is None:
            return None
        raw = value.strip()
        parts = raw.split(":")
        if len(parts) not in (2, 3):
            raise ValueError("local_time must be HH:MM or HH:MM:SS.")
        try:
            hour = int(parts[0])
            minute = int(parts[1])
            second = int(parts[2]) if len(parts) == 3 else 0
        except ValueError as exc:
            raise ValueError("local_time must be HH:MM or HH:MM:SS.") from exc
        if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            raise ValueError("local_time is out of range.")
        if len(parts) == 2:
            return f"{hour:02d}:{minute:02d}"
        return f"{hour:02d}:{minute:02d}:{second:02d}"

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        if not -90.0 <= value <= 90.0:
            raise ValueError("latitude must be between -90 and 90.")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        if not -180.0 <= value <= 180.0:
            raise ValueError("longitude must be between -180 and 180.")
        return value

    @model_validator(mode="after")
    def validate_time_consistency(self) -> NatalChartRequest:
        if self.unknown_time:
            if self.local_time is not None:
                raise ValueError(
                    "local_time must be null when unknown_time is true; "
                    "do not send a placeholder clock time."
                )
        elif self.local_time is None:
            raise ValueError("local_time is required when unknown_time is false.")
        return self

    def to_engine_local_datetime(self) -> str:
        """Map HTTP fields to AstrologyEngine.natal(local_datetime=...)."""

        if self.unknown_time:
            return self.local_date
        assert self.local_time is not None
        time_part = self.local_time if self.local_time.count(":") == 2 else f"{self.local_time}:00"
        return f"{self.local_date}T{time_part}"


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    engine: str
    engine_version: str
    schema_version: str
    api_version: str


class ReadinessResponse(BaseModel):
    """Whether the service can actually calculate, not merely whether it is up.

    `/health` answering `ok` says the process is alive. It says nothing about
    whether ephemeris data was provisioned, and a container missing that data
    starts happily and then fails every chart request. This endpoint runs a real
    calculation so a deploy fails at the readiness probe instead of in front of
    users.
    """

    status: Literal["ready", "degraded", "not_ready"]
    engine: str
    engine_version: str
    api_version: str
    provider: str | None = None
    provider_version: str | None = None
    ephemeris_path: str | None = None
    unavailable_capabilities: list[str] = Field(default_factory=list)
    missing_required_data: list[str] = Field(default_factory=list)
    detail: str | None = None


class ApiErrorBody(BaseModel):
    code: str
    message: str
    field: str | None = None
    details: dict[str, object] = Field(default_factory=dict)


class ApiErrorEnvelope(BaseModel):
    error: ApiErrorBody


class RelationshipRequest(BaseModel):
    """Two natal subjects for a synastry or composite chart.

    Each side carries the same fields as a natal request, so historical
    timezone and DST interpretation stay with the engine on both sides.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "chart_a": {
                        "local_date": "1992-11-03",
                        "local_time": "14:35",
                        "timezone": "Asia/Ho_Chi_Minh",
                        "latitude": 21.0285,
                        "longitude": 105.8542,
                    },
                    "chart_b": {
                        "local_date": "1990-06-21",
                        "local_time": "08:20",
                        "timezone": "Europe/Berlin",
                        "latitude": 52.52,
                        "longitude": 13.405,
                    },
                }
            ]
        },
    )

    chart_a: NatalChartRequest = Field(..., description="First subject.")
    chart_b: NatalChartRequest = Field(..., description="Second subject.")


class TransitRequest(BaseModel):
    """A natal subject plus the instant to read the sky at."""

    model_config = ConfigDict(extra="forbid")

    natal: NatalChartRequest = Field(..., description="The natal subject.")
    target_instant: str = Field(
        ...,
        description="UTC instant to calculate transits for, ISO 8601.",
        json_schema_extra={"examples": ["2026-08-08T12:00:00Z"]},
    )
    include_natal_chart: bool = Field(
        default=False, description="Embed the full natal chart in the response."
    )
    top: int | None = Field(
        default=None,
        ge=0,
        le=50,
        description="How many ranked transits to return in topAspects. Defaults to 3.",
    )


class ReturnRequest(BaseModel):
    """A natal subject, a body, and the window to search for its returns."""

    model_config = ConfigDict(extra="forbid")

    natal: NatalChartRequest = Field(..., description="The natal subject.")
    body: str = Field(
        ...,
        description="Body whose return to find, for example 'sun' or 'saturn'.",
        json_schema_extra={"examples": ["sun", "moon", "saturn"]},
    )
    window_start: str = Field(..., description="Window start, UTC ISO 8601.")
    window_end: str = Field(..., description="Window end, UTC ISO 8601.")
    include_charts: bool = Field(
        default=False, description="Cast a chart for each exact return."
    )


class EventSearchRequest(BaseModel):
    """A numerical event search over a time window."""

    model_config = ConfigDict(extra="forbid")

    event_type: Literal["sign_ingress", "station", "exact_longitude", "exact_aspect"] = Field(
        ..., description="Which kind of event to locate."
    )
    body: str = Field(..., json_schema_extra={"examples": ["mercury", "sun"]})
    start: str = Field(..., description="Window start, UTC ISO 8601.")
    end: str = Field(..., description="Window end, UTC ISO 8601.")
    target_longitude: float | None = Field(
        default=None,
        description="Required for exact_longitude and exact_aspect.",
    )
    aspect_angle: float | None = Field(
        default=None, description="Required for exact_aspect, in degrees."
    )
