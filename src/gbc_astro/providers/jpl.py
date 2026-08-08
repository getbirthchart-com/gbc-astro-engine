"""JPL ephemeris provider scaffold."""

from __future__ import annotations

from datetime import datetime

from gbc_astro.constants import BODY_IDS
from gbc_astro.errors import ProviderDependencyError, UnsupportedBodyError
from gbc_astro.models.position import RawBodyPosition
from gbc_astro.providers.base import ProviderCapabilities


class JplEphemerisProvider:
    """Interface-only scaffold for a future JPL DE-series provider."""

    id = "jpl"
    data_version = "unconfigured"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_bodies=BODY_IDS,
            date_range=("unconfigured", "unconfigured"),
            supports_speed=False,
            supports_latitude=False,
            supports_distance=False,
        )

    def supports_body(self, body: str) -> bool:
        return body in BODY_IDS

    def position(self, body: str, instant_utc: datetime) -> RawBodyPosition:
        if not self.supports_body(body):
            raise UnsupportedBodyError(
                "The configured provider does not support this body.",
                {"provider": self.id, "body": body},
            )
        raise ProviderDependencyError(
            "JPL provider is a scaffold only; configure a validated JPL ephemeris backend first.",
            {"provider": self.id, "instantUtc": instant_utc.isoformat()},
        )

