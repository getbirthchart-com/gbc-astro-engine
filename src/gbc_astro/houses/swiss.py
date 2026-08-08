"""House and angle calculations backed by Swiss Ephemeris."""

from __future__ import annotations

import os
from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING, cast

from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.errors import HouseCalculationUnavailableError, ProviderDependencyError
from gbc_astro.houses.base import (
    HouseCalculation,
    build_house_cusps,
    is_sequence_degenerate,
)
from gbc_astro.houses.equal import equal_cusp_longitudes
from gbc_astro.houses.systems import HOUSE_SYSTEMS, LOCALLY_DERIVED
from gbc_astro.houses.whole_sign import whole_sign_cusp_longitudes
from gbc_astro.models.position import AnglePosition
from gbc_astro.zodiac.tropical import longitude_to_tropical

if TYPE_CHECKING:
    from gbc_astro.houses.systems import HouseSystemProfile


def _load_swisseph() -> ModuleType:
    try:
        return import_module("swisseph")
    except ImportError as exc:
        raise ProviderDependencyError(
            "Swiss house calculation requires the optional 'pyswisseph' dependency.",
            {"install": 'python -m pip install "gbc-astro[swiss]"'},
        ) from exc


class SwissHouseCalculator:
    id = "swiss-house"

    def __init__(self, ephemeris_path: str | None = None) -> None:
        self._swe = _load_swisseph()
        self.ephemeris_path = ephemeris_path or os.environ.get("GBC_SWISS_EPHE_PATH")
        if self.ephemeris_path:
            self._swe.set_ephe_path(self.ephemeris_path)

    def calculate(
        self,
        julian_day: float,
        latitude: float,
        longitude: float,
        house_system: str,
    ) -> HouseCalculation:
        system, profile = _resolve_system(house_system)
        try:
            cusps_raw, ascmc = self._swe.houses_ex(
                julian_day,
                latitude,
                longitude,
                _provider_code(system, profile).encode("ascii"),
            )
        except Exception as exc:
            raise HouseCalculationUnavailableError(
                "Swiss Ephemeris could not calculate houses for this input.",
                {
                    "houseSystem": system,
                    "latitude": latitude,
                    "longitude": longitude,
                    "provider": self.id,
                },
            ) from exc

        asc = normalize_longitude(float(ascmc[0]))
        mc = normalize_longitude(float(ascmc[1]))
        cusp_longitudes = _cusps_for(system, asc, cusps_raw)

        angles = {
            "ascendant": _angle(asc),
            "mc": _angle(mc),
            "descendant": _angle(asc + 180.0),
            "ic": _angle(mc + 180.0),
        }
        cusps = build_house_cusps(cusp_longitudes)
        return HouseCalculation(
            angles=angles,
            houses=cusps,
            algorithm_version=f"swisseph:{_version(self._swe)}:{system}",
            sequence_degenerate=is_sequence_degenerate(cusps),
        )


    def obliquity(self, julian_day: float) -> float:
        """True obliquity of the ecliptic, in degrees, for a Julian Day (UT)."""
        try:
            values, _flags = self._swe.calc_ut(julian_day, self._swe.ECL_NUT)
        except Exception as exc:
            raise HouseCalculationUnavailableError(
                "Swiss Ephemeris could not resolve the obliquity of the ecliptic.",
                {"julianDay": julian_day, "provider": self.id},
            ) from exc
        return float(values[0])

    def calculate_from_armc(
        self,
        armc: float,
        latitude: float,
        obliquity: float,
        house_system: str,
    ) -> HouseCalculation:
        """House cusps from right ascension of the Midheaven, with no instant.

        A composite chart has no time and no place, so it cannot go through
        `calculate`. It does have a Midheaven, and ARMC plus a reference latitude
        and obliquity is enough to place every cusp. Same refusal rules apply:
        beyond the polar circles Placidus has no solution and this raises rather
        than substituting another house system.
        """
        system, profile = _resolve_system(house_system)
        try:
            cusps_raw, ascmc = self._swe.houses_armc(
                normalize_longitude(armc),
                latitude,
                obliquity,
                _provider_code(system, profile).encode("ascii"),
            )
        except Exception as exc:
            raise HouseCalculationUnavailableError(
                "Swiss Ephemeris could not calculate houses from the supplied ARMC.",
                {
                    "houseSystem": system,
                    "armc": armc,
                    "latitude": latitude,
                    "provider": self.id,
                },
            ) from exc

        asc = normalize_longitude(float(ascmc[0]))
        mc = normalize_longitude(float(ascmc[1]))
        cusp_longitudes = _cusps_for(system, asc, cusps_raw)

        return HouseCalculation(
            angles={
                "ascendant": _angle(asc),
                "mc": _angle(mc),
                "descendant": _angle(asc + 180.0),
                "ic": _angle(mc + 180.0),
            },
            houses=build_house_cusps(cusp_longitudes),
            algorithm_version=f"swisseph:{_version(self._swe)}:{system}:armc",
            sequence_degenerate=is_sequence_degenerate(build_house_cusps(cusp_longitudes)),
        )


    def sidereal_time_degrees(self, julian_day: float) -> float:
        """Greenwich apparent sidereal time in degrees, for a Julian Day (UT)."""
        return normalize_longitude(float(self._swe.sidtime(julian_day)) * 15.0)

    def to_equatorial(
        self, longitude: float, latitude: float, obliquity: float
    ) -> tuple[float, float]:
        """Ecliptic longitude and latitude to right ascension and declination."""
        right_ascension, declination, _distance = self._swe.cotrans(
            (longitude, latitude, 1.0), -obliquity
        )
        return normalize_longitude(float(right_ascension)), float(declination)


def _resolve_system(house_system: str) -> tuple[str, HouseSystemProfile]:
    system = house_system.lower()
    profile = HOUSE_SYSTEMS.get(system)
    if profile is None:
        raise HouseCalculationUnavailableError(
            "Unsupported house system.",
            {"houseSystem": house_system, "supported": sorted(HOUSE_SYSTEMS)},
        )
    return system, profile


def _provider_code(system: str, profile: HouseSystemProfile) -> str:
    """Which code to hand Swiss Ephemeris.

    Whole Sign and Equal cusps are derived locally from the Ascendant, so the
    provider is only asked for the angles. Requesting Equal for both keeps that
    call identical and makes the derived-versus-provider boundary explicit.
    """
    if system in LOCALLY_DERIVED:
        return "E"
    return profile.swisseph_code


def _cusps_for(
    system: str, ascendant: float, provider_cusps: object
) -> tuple[float, ...]:
    if system == "whole_sign":
        return whole_sign_cusp_longitudes(ascendant)
    if system == "equal":
        return equal_cusp_longitudes(ascendant)
    values = cast("list[float]", provider_cusps)
    return tuple(normalize_longitude(float(value)) for value in values[:12])


def _angle(longitude: float) -> AnglePosition:
    zpos = longitude_to_tropical(longitude)
    return AnglePosition(
        longitude=zpos.longitude,
        sign=zpos.sign,
        degree_in_sign=zpos.degree_in_sign,
    )


def _version(swe: ModuleType) -> str:
    value = getattr(swe, "version", "unknown")
    return str(value() if callable(value) else value)
