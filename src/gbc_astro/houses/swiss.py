"""House and angle calculations backed by Swiss Ephemeris."""

from __future__ import annotations

import os
from importlib import import_module
from types import ModuleType

from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.errors import HouseCalculationUnavailableError, ProviderDependencyError
from gbc_astro.houses.base import HouseCalculation, build_house_cusps
from gbc_astro.houses.equal import equal_cusp_longitudes
from gbc_astro.houses.whole_sign import whole_sign_cusp_longitudes
from gbc_astro.models.position import AnglePosition
from gbc_astro.zodiac.tropical import longitude_to_tropical


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
        system = house_system.lower()
        if system not in {"whole_sign", "equal", "placidus"}:
            raise HouseCalculationUnavailableError(
                "Unsupported house system.",
                {"houseSystem": house_system},
            )

        reference_system = "P" if system == "placidus" else "E"
        try:
            cusps_raw, ascmc = self._swe.houses_ex(
                julian_day,
                latitude,
                longitude,
                reference_system.encode("ascii"),
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
        if system == "whole_sign":
            cusp_longitudes = whole_sign_cusp_longitudes(asc)
        elif system == "equal":
            cusp_longitudes = equal_cusp_longitudes(asc)
        else:
            cusp_longitudes = tuple(normalize_longitude(float(value)) for value in cusps_raw[:12])

        angles = {
            "ascendant": _angle(asc),
            "mc": _angle(mc),
            "descendant": _angle(asc + 180.0),
            "ic": _angle(mc + 180.0),
        }
        return HouseCalculation(
            angles=angles,
            houses=build_house_cusps(cusp_longitudes),
            algorithm_version=f"swisseph:{_version(self._swe)}:{system}",
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
        system = house_system.lower()
        if system not in {"whole_sign", "equal", "placidus"}:
            raise HouseCalculationUnavailableError(
                "Unsupported house system.",
                {"houseSystem": house_system},
            )

        reference_system = "P" if system == "placidus" else "E"
        try:
            cusps_raw, ascmc = self._swe.houses_armc(
                normalize_longitude(armc),
                latitude,
                obliquity,
                reference_system.encode("ascii"),
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
        if system == "whole_sign":
            cusp_longitudes = whole_sign_cusp_longitudes(asc)
        elif system == "equal":
            cusp_longitudes = equal_cusp_longitudes(asc)
        else:
            cusp_longitudes = tuple(normalize_longitude(float(value)) for value in cusps_raw[:12])

        return HouseCalculation(
            angles={
                "ascendant": _angle(asc),
                "mc": _angle(mc),
                "descendant": _angle(asc + 180.0),
                "ic": _angle(mc + 180.0),
            },
            houses=build_house_cusps(cusp_longitudes),
            algorithm_version=f"swisseph:{_version(self._swe)}:{system}:armc",
        )


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
