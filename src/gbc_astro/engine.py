"""High-level public calculation engine."""

from __future__ import annotations

from datetime import date, datetime

from gbc_astro.aspects.engine import calculate_aspects
from gbc_astro.astronomy.time import isoformat_z, normalize_local_datetime
from gbc_astro.constants import BODY_IDS, ENGINE_NAME, ENGINE_VERSION, SCHEMA_VERSION
from gbc_astro.derived.balances import (
    element_counts,
    hemisphere_counts,
    modality_counts,
    polarity_counts,
    quadrant_counts,
)
from gbc_astro.derived.moon_phase import calculate_moon_phase
from gbc_astro.errors import InvalidCalculationProfileError, UnsupportedBodyError
from gbc_astro.houses.base import HouseCalculation, HouseCalculator, assign_house
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.models.chart import (
    ChartMeta,
    ChartSubject,
    DerivedNatal,
    NatalChart,
    WarningMessage,
)
from gbc_astro.models.input import ChartInput
from gbc_astro.models.position import BodyPosition
from gbc_astro.profiles.defaults import WESTERN_MODERN_V1
from gbc_astro.profiles.model import CalculationProfile
from gbc_astro.providers.base import EphemerisProvider
from gbc_astro.providers.normalization import normalize_body_position
from gbc_astro.providers.swiss import SwissEphemerisProvider


class AstrologyEngine:
    """Versioned deterministic astrology engine."""

    def __init__(
        self,
        provider: EphemerisProvider | None = None,
        profile: CalculationProfile = WESTERN_MODERN_V1,
        house_calculator: HouseCalculator | None = None,
    ) -> None:
        self._provider = provider
        self.profile = profile
        self._house_calculator = house_calculator
        self._validate_profile(profile)

    @property
    def provider_id(self) -> str:
        return self._get_provider().id

    def natal(
        self,
        local_datetime: str | datetime | date,
        timezone: str,
        latitude: float,
        longitude: float,
        altitude_m: float | None = None,
        house_system: str | None = None,
        unknown_time: bool = False,
        fold: int | None = None,
    ) -> NatalChart:
        chart_input = ChartInput.from_public(
            local_datetime=local_datetime,
            timezone=timezone,
            latitude=latitude,
            longitude=longitude,
            altitude_m=altitude_m,
            birth_time_known=not unknown_time,
            fold=fold,
        )
        time_norm = normalize_local_datetime(
            chart_input.local_datetime,
            chart_input.timezone,
            fold=chart_input.fold,
        )
        current_house_system = (house_system or self.profile.house_system).lower()
        if current_house_system not in {"whole_sign", "equal", "placidus"}:
            raise InvalidCalculationProfileError(
                "Unsupported house system.",
                {"houseSystem": current_house_system},
            )

        warnings: list[WarningMessage] = []
        if not chart_input.birth_time_known:
            warnings.append(
                WarningMessage(
                    code="UNKNOWN_BIRTH_TIME",
                    severity="warning",
                    message=(
                        "Time-sensitive chart fields were omitted. Body positions use "
                        "the explicit profile policy for local-date-start approximation."
                    ),
                    fields_affected=("angles", "houses", "houseAssignments"),
                )
            )

        provider = self._get_provider()
        bodies = self._calculate_bodies(provider, time_norm.utc_datetime)

        house_calculation: HouseCalculation | None = None
        if chart_input.birth_time_known:
            house_calculation = self._get_house_calculator().calculate(
                julian_day=time_norm.julian_day,
                latitude=chart_input.latitude,
                longitude=chart_input.longitude,
                house_system=current_house_system,
            )
            bodies = {
                body_id: _replace_house(
                    body,
                    assign_house(body.longitude, house_calculation.houses),
                )
                for body_id, body in bodies.items()
            }

        derived = self._calculate_derived(bodies, house_calculation)
        aspects = calculate_aspects(bodies, self.profile.aspect_profile)
        meta = ChartMeta(
            schema_version=SCHEMA_VERSION,
            engine=ENGINE_NAME,
            engine_version=ENGINE_VERSION,
            ephemeris_provider=provider.id,
            ephemeris_data_version=provider.data_version,
            timezone_data_version=time_norm.timezone_data_version,
            calculation_profile=self.profile.id,
            house_system=current_house_system if chart_input.birth_time_known else None,
            aspect_profile=self.profile.aspect_profile.id,
            zodiac=self.profile.zodiac,
            house_algorithm_version=(
                house_calculation.algorithm_version if house_calculation else None
            ),
        )
        subject = ChartSubject(
            local_datetime=chart_input.local_datetime.isoformat(),
            timezone=chart_input.timezone,
            utc_datetime=isoformat_z(time_norm.utc_datetime),
            julian_day=time_norm.julian_day,
            latitude=chart_input.latitude,
            longitude=chart_input.longitude,
            altitude_m=chart_input.altitude_m,
            birth_time_known=chart_input.birth_time_known,
        )
        return NatalChart(
            schema_version=SCHEMA_VERSION,
            meta=meta,
            subject=subject,
            angles=house_calculation.angles if house_calculation else {},
            bodies=bodies,
            houses=house_calculation.houses if house_calculation else (),
            aspects=aspects,
            derived=derived,
            warnings=tuple(warnings),
        )

    def _get_provider(self) -> EphemerisProvider:
        if self._provider is None:
            self._provider = SwissEphemerisProvider()
        return self._provider

    def _get_house_calculator(self) -> HouseCalculator:
        if self._house_calculator is None:
            self._house_calculator = SwissHouseCalculator()
        return self._house_calculator

    def _calculate_bodies(
        self,
        provider: EphemerisProvider,
        utc_datetime: datetime,
    ) -> dict[str, BodyPosition]:
        bodies: dict[str, BodyPosition] = {}
        for body_id in BODY_IDS:
            if not provider.supports_body(body_id):
                raise UnsupportedBodyError(
                    "The configured provider does not support a required v0.1 body.",
                    {"provider": provider.id, "body": body_id},
                )
            raw = provider.position(body_id, utc_datetime)
            bodies[body_id] = normalize_body_position(body_id, raw)
        return bodies

    def _calculate_derived(
        self,
        bodies: dict[str, BodyPosition],
        house_calculation: HouseCalculation | None,
    ) -> DerivedNatal:
        rising = house_calculation.angles["ascendant"].sign if house_calculation else None
        moon_phase = None
        if "sun" in bodies and "moon" in bodies:
            moon_phase = calculate_moon_phase(bodies["sun"], bodies["moon"])
        sun = bodies.get("sun")
        moon = bodies.get("moon")
        return DerivedNatal(
            big_three={
                "sun": sun.sign if sun else None,
                "moon": moon.sign if moon else None,
                "rising": rising,
            },
            moon_phase=moon_phase,
            elements=element_counts(bodies, self.profile.balance_bodies),
            modalities=modality_counts(bodies, self.profile.balance_bodies),
            polarities=polarity_counts(bodies, self.profile.balance_bodies),
            hemispheres=hemisphere_counts(bodies, self.profile.balance_bodies),
            quadrants=quadrant_counts(bodies, self.profile.balance_bodies),
        )

    @staticmethod
    def _validate_profile(profile: CalculationProfile) -> None:
        if profile.zodiac != "tropical":
            raise InvalidCalculationProfileError(
                "Only tropical zodiac is implemented in the current release boundary.",
                {"zodiac": profile.zodiac},
            )


def _replace_house(body: BodyPosition, house: int) -> BodyPosition:
    return BodyPosition(
        body_id=body.body_id,
        longitude=body.longitude,
        latitude=body.latitude,
        distance=body.distance,
        speed_longitude=body.speed_longitude,
        retrograde=body.retrograde,
        sign=body.sign,
        degree_in_sign=body.degree_in_sign,
        house=house,
    )
