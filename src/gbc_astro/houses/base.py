"""House calculation models and common assignment logic."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.models.position import AnglePosition, HouseCusp
from gbc_astro.zodiac.tropical import longitude_to_tropical


@dataclass(frozen=True)
class HouseCalculation:
    angles: dict[str, AnglePosition]
    houses: tuple[HouseCusp, ...]
    algorithm_version: str


class HouseCalculator(Protocol):
    @property
    def id(self) -> str:
        ...

    def calculate(
        self,
        julian_day: float,
        latitude: float,
        longitude: float,
        house_system: str,
    ) -> HouseCalculation:
        ...


class ArmcHouseCalculator(Protocol):
    """Houses from ARMC rather than from an instant.

    Kept separate from `HouseCalculator` because only constructions that have no
    time of their own -- the composite chart -- need it, and the validation
    fixtures implement the time-based protocol only.
    """

    @property
    def id(self) -> str:
        ...

    def obliquity(self, julian_day: float) -> float:
        ...

    def calculate_from_armc(
        self,
        armc: float,
        latitude: float,
        obliquity: float,
        house_system: str,
    ) -> HouseCalculation:
        ...


def build_house_cusps(cusp_longitudes: tuple[float, ...]) -> tuple[HouseCusp, ...]:
    if len(cusp_longitudes) != 12:
        raise ValueError("A house calculation must contain exactly 12 cusps.")
    cusps = []
    for index, longitude in enumerate(cusp_longitudes, start=1):
        zpos = longitude_to_tropical(longitude)
        cusps.append(
            HouseCusp(
                number=index,
                cusp_longitude=zpos.longitude,
                sign=zpos.sign,
                degree_in_sign=zpos.degree_in_sign,
            )
        )
    return tuple(cusps)


def assign_house(
    longitude: float,
    houses: tuple[HouseCusp, ...],
    exact_epsilon_deg: float = 1e-9,
) -> int:
    """Assign a longitude to a house.

    Cusp policy: a body exactly on cusp N belongs to house N.
    """

    if len(houses) != 12:
        raise ValueError("House assignment requires exactly 12 houses.")
    lon = normalize_longitude(longitude)
    cusp_values = [house.cusp_longitude for house in houses]

    for index, cusp in enumerate(cusp_values):
        if math.isclose(lon, cusp, abs_tol=exact_epsilon_deg):
            return index + 1

    for index, start in enumerate(cusp_values):
        end = cusp_values[(index + 1) % 12]
        house_number = index + 1
        if start < end and start < lon < end:
            return house_number
        if start > end and (lon > start or lon < end):
            return house_number
    return 12

