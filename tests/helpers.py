from __future__ import annotations

from datetime import datetime

from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.constants import BODY_IDS
from gbc_astro.houses.base import HouseCalculation, build_house_cusps
from gbc_astro.houses.equal import equal_cusp_longitudes
from gbc_astro.models.position import AnglePosition, RawBodyPosition
from gbc_astro.providers.base import ProviderCapabilities
from gbc_astro.zodiac.tropical import longitude_to_tropical


class FixtureProvider:
    id = "fixture"
    data_version = "fixture-v1"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_bodies=BODY_IDS,
            date_range=("1900-01-01", "2100-01-01"),
            supports_speed=True,
            supports_latitude=True,
            supports_distance=True,
        )

    def supports_body(self, body: str) -> bool:
        return body in BODY_IDS

    def position(self, body: str, instant_utc: datetime) -> RawBodyPosition:
        index = BODY_IDS.index(body)
        longitude = normalize_longitude(10.0 + index * 27.5)
        if body == "moon":
            longitude = 69.0
        return RawBodyPosition(
            longitude_deg=longitude,
            latitude_deg=0.1 * index,
            distance=None,
            longitude_speed_deg_per_day=1.0 + index / 10.0,
        )


class FixtureHouseCalculator:
    id = "fixture-house"

    def calculate(
        self,
        julian_day: float,
        latitude: float,
        longitude: float,
        house_system: str,
    ) -> HouseCalculation:
        asc = 15.0
        mc = 270.0
        angles = {
            "ascendant": _angle(asc),
            "mc": _angle(mc),
            "descendant": _angle(asc + 180.0),
            "ic": _angle(mc + 180.0),
        }
        return HouseCalculation(
            angles=angles,
            houses=build_house_cusps(equal_cusp_longitudes(asc)),
            algorithm_version=f"fixture:{house_system}",
        )


def _angle(longitude: float) -> AnglePosition:
    zpos = longitude_to_tropical(longitude)
    return AnglePosition(
        longitude=zpos.longitude,
        sign=zpos.sign,
        degree_in_sign=zpos.degree_in_sign,
    )

