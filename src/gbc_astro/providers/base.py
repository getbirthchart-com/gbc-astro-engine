"""Provider protocols."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from gbc_astro.models.position import RawBodyPosition


@dataclass(frozen=True)
class ProviderCapabilities:
    supported_bodies: tuple[str, ...]
    date_range: tuple[str, str]
    supports_speed: bool
    supports_latitude: bool
    supports_distance: bool


class EphemerisProvider(Protocol):
    @property
    def id(self) -> str:
        ...

    @property
    def data_version(self) -> str:
        ...

    @property
    def capabilities(self) -> ProviderCapabilities:
        ...

    def supports_body(self, body: str) -> bool:
        ...

    def position(self, body: str, instant_utc: datetime) -> RawBodyPosition:
        ...

