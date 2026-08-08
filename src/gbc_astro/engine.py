"""High-level public calculation engine."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from typing import Any

from gbc_astro.aspects.engine import calculate_aspects
from gbc_astro.astronomy.circular import normalize_longitude
from gbc_astro.astronomy.time import (
    datetime_to_julian_day,
    isoformat_z,
    normalize_local_datetime,
)
from gbc_astro.charts.astrocartography import (
    DEFAULT_LATITUDE_RANGE,
    DEFAULT_LATITUDE_STEP,
    calculate_astrocartography,
)
from gbc_astro.charts.ephemeris import DEFAULT_MAX_ROWS, generate_ephemeris
from gbc_astro.constants import (
    BODY_IDS,
    ENGINE_NAME,
    ENGINE_VERSION,
    EVENT_SCHEMA_VERSION,
    SCHEMA_VERSION,
)
from gbc_astro.derived.balances import (
    element_counts,
    hemisphere_counts,
    modality_counts,
    polarity_counts,
    quadrant_counts,
)
from gbc_astro.derived.moon_phase import calculate_moon_phase
from gbc_astro.derived.patterns import ChartPattern, find_patterns
from gbc_astro.derived.rulership import (
    chart_ruler,
    dignities,
    dispositor_chains,
    dominant_planets,
    final_dispositors,
    house_rulers,
    mutual_receptions,
)
from gbc_astro.errors import (
    InvalidCalculationProfileError,
    UnknownBirthTimeError,
    UnsupportedBodyError,
)
from gbc_astro.forecast.returns import calculate_returns
from gbc_astro.forecast.transits import calculate_transits
from gbc_astro.houses.base import (
    ArmcHouseCalculator,
    HouseCalculation,
    HouseCalculator,
    assign_house,
    build_house_cusps,
    is_sequence_degenerate,
)
from gbc_astro.houses.swiss import SwissHouseCalculator
from gbc_astro.houses.systems import (
    HOUSE_SYSTEMS,
    SIGN_ANCHORED,
    SUPPORTED_HOUSE_SYSTEMS,
)
from gbc_astro.houses.whole_sign import whole_sign_cusp_longitudes
from gbc_astro.models.aspect import Aspect
from gbc_astro.models.chart import (
    ChartMeta,
    ChartSubject,
    DerivedNatal,
    NatalChart,
    WarningMessage,
)
from gbc_astro.models.forecast import EventSearchResult, ReturnSearchResult, TransitChart
from gbc_astro.models.input import ChartInput
from gbc_astro.models.position import AnglePosition, BodyPosition
from gbc_astro.models.relationship import (
    CompositeChart,
    DavisonChart,
    RelationshipScore,
    SynastryChart,
)
from gbc_astro.models.transform import TransformedChart
from gbc_astro.profiles.defaults import RELATIONSHIP_WESTERN_V1, WESTERN_MODERN_V1
from gbc_astro.profiles.model import CalculationProfile, RelationshipProfile
from gbc_astro.profiles.pattern import PATTERN_PROFILE_V1, PatternProfile
from gbc_astro.profiles.progression import (
    SECONDARY_PROGRESSION_V1,
    SOLAR_ARC_V1,
    ProgressionProfile,
)
from gbc_astro.profiles.rulership import (
    DOMINANT_WESTERN_V1,
    DominantProfile,
    resolve_rulership_profile,
)
from gbc_astro.profiles.scoring import SYNASTRY_SCORING_V1, ScoringProfile
from gbc_astro.profiles.transit import TRANSIT_PROFILE_V1, TransitProfile
from gbc_astro.providers.asteroids import (
    BodyCapability,
    available_optional_bodies,
)
from gbc_astro.providers.base import EphemerisProvider
from gbc_astro.providers.normalization import normalize_body_position
from gbc_astro.providers.swiss import SwissEphemerisProvider
from gbc_astro.relationship.composite import calculate_composite
from gbc_astro.relationship.davison import calculate_davison
from gbc_astro.relationship.scoring import calculate_relationship_score
from gbc_astro.relationship.synastry import calculate_synastry
from gbc_astro.search.events import (
    find_aspect_events,
    find_longitude_crossings,
    find_sign_ingresses,
    find_stations,
)
from gbc_astro.transforms.draconic import calculate_draconic
from gbc_astro.transforms.harmonic import calculate_harmonic
from gbc_astro.transforms.progressions import (
    calculate_secondary_progressions,
    calculate_solar_arc,
)
from gbc_astro.transforms.relocation import calculate_relocation
from gbc_astro.zodiac.sidereal import (
    AyanamsaCalculator,
    longitude_to_sidereal,
    resolve_ayanamsa_profile,
)


class AstrologyEngine:
    """Versioned deterministic astrology engine."""

    def __init__(
        self,
        provider: EphemerisProvider | None = None,
        profile: CalculationProfile = WESTERN_MODERN_V1,
        house_calculator: HouseCalculator | None = None,
        relationship_profile: RelationshipProfile = RELATIONSHIP_WESTERN_V1,
        scoring_profile: ScoringProfile = SYNASTRY_SCORING_V1,
        transit_profile: TransitProfile = TRANSIT_PROFILE_V1,
        progression_profile: ProgressionProfile = SECONDARY_PROGRESSION_V1,
        solar_arc_profile: ProgressionProfile = SOLAR_ARC_V1,
        pattern_profile: PatternProfile = PATTERN_PROFILE_V1,
        dominant_profile: DominantProfile = DOMINANT_WESTERN_V1,
    ) -> None:
        self._provider = provider
        self.profile = profile
        self.relationship_profile = relationship_profile
        self.scoring_profile = scoring_profile
        self.transit_profile = transit_profile
        self.progression_profile = progression_profile
        self.solar_arc_profile = solar_arc_profile
        self.pattern_profile = pattern_profile
        self.dominant_profile = dominant_profile
        self._house_calculator = house_calculator
        self._ayanamsa_calculator: AyanamsaCalculator | None = None
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
        if current_house_system not in HOUSE_SYSTEMS:
            raise InvalidCalculationProfileError(
                "Unsupported house system.",
                {
                    "houseSystem": current_house_system,
                    "supported": list(SUPPORTED_HOUSE_SYSTEMS),
                },
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

        ayanamsa_profile = None
        ayanamsa_degrees = None
        if self.profile.zodiac == "sidereal":
            ayanamsa_profile = resolve_ayanamsa_profile(self.profile.ayanamsa or "")
            ayanamsa_degrees = self._get_ayanamsa_calculator().value(
                time_norm.julian_day, ayanamsa_profile
            )
            bodies = {
                body_id: _to_sidereal_body(body, ayanamsa_degrees)
                for body_id, body in bodies.items()
            }
            if house_calculation is not None:
                house_calculation = _to_sidereal_geometry(
                    house_calculation, ayanamsa_degrees, current_house_system
                )
                bodies = {
                    body_id: _replace_house(
                        body, assign_house(body.longitude, house_calculation.houses)
                    )
                    for body_id, body in bodies.items()
                }

        if house_calculation is not None and house_calculation.sequence_degenerate:
            warnings.append(
                WarningMessage(
                    code="HOUSE_SEQUENCE_DEGENERATE",
                    severity="warning",
                    message=(
                        f"The {current_house_system} cusps do not advance in zodiacal "
                        "order at this latitude. Beyond the polar circles quadrant "
                        "systems invert, and the result is mathematically defined but "
                        "astrologically meaningless. House assignments should not be "
                        "relied on. Whole Sign and Equal remain well-formed here."
                    ),
                    fields_affected=("houses", "bodies.*.house"),
                )
            )

        # Aspects first: the dominance score inside `derived` weighs how much of
        # the chart each planet aspects, so it needs them already calculated.
        aspects = calculate_aspects(bodies, self.profile.aspect_profile)
        derived = self._calculate_derived(bodies, house_calculation, aspects)
        meta = ChartMeta(
            schema_version=SCHEMA_VERSION,
            engine=ENGINE_NAME,
            engine_version=ENGINE_VERSION,
            ephemeris_provider=provider.id,
            ephemeris_data_version=provider.data_version,
            timezone_data_version=time_norm.timezone_data_version,
            calculation_profile=self.profile.id,
            rulership_profile=resolve_rulership_profile(self.profile.rulership).id,
            rulership_profile_version=resolve_rulership_profile(
                self.profile.rulership
            ).version,
            dominant_profile=self.dominant_profile.id,
            dominant_profile_version=self.dominant_profile.version,
            house_system=current_house_system if chart_input.birth_time_known else None,
            aspect_profile=self.profile.aspect_profile.id,
            zodiac=self.profile.zodiac,
            house_algorithm_version=(
                house_calculation.algorithm_version if house_calculation else None
            ),
            ayanamsa=ayanamsa_profile.id if ayanamsa_profile else None,
            ayanamsa_version=ayanamsa_profile.version if ayanamsa_profile else None,
            ayanamsa_degrees=ayanamsa_degrees,
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

    def synastry(self, chart_a: NatalChart, chart_b: NatalChart) -> SynastryChart:
        """Cross aspects, two-way house overlays and angle interactions.

        Takes charts rather than birth data so both sides are known to have been
        built under the same semantics; mixing zodiacs or schema versions is
        refused rather than silently averaged.
        """
        return calculate_synastry(chart_a, chart_b, self.relationship_profile)

    def composite(self, chart_a: NatalChart, chart_b: NatalChart) -> CompositeChart:
        """Shortest-arc midpoint composite, with angles and houses derived from the MC."""
        return calculate_composite(
            chart_a,
            chart_b,
            self.relationship_profile,
            self._get_armc_house_calculator(),
        )

    def davison(self, chart_a: NatalChart, chart_b: NatalChart) -> DavisonChart:
        """A real chart for the midpoint moment and midpoint place of two births.

        Unlike a composite this is an actual instant, so its speeds, houses and
        applying/separating phases are genuine rather than constructed.
        """
        return calculate_davison(chart_a, chart_b, self.relationship_profile, self.natal)

    def compatibility(self, chart_a: NatalChart, chart_b: NatalChart) -> RelationshipScore:
        """Score a pair under the configured scoring profile.

        The only calculation in this engine with no independent reference: the
        weights are an editorial opinion, not a measurement. Reported as three
        totals rather than a percentage, and every contact that fed them is
        listed so the figure can be shown rather than asserted.
        """
        return calculate_relationship_score(
            self.synastry(chart_a, chart_b),
            self.relationship_profile,
            self.scoring_profile,
        )

    def transits(
        self,
        natal_chart: NatalChart,
        target_instant: datetime,
        top_count: int | None = None,
        include_natal_chart: bool = False,
    ) -> TransitChart:
        """Sky positions at an instant, aspected and housed against a natal chart.

        Applying and separating are real here: the transiting bodies move while
        the natal points do not, so there is a shared timeline, which is exactly
        what synastry lacks.
        """
        return calculate_transits(
            natal_chart=natal_chart,
            target_instant=target_instant,
            provider=self._get_provider(),
            profile=self.profile,
            transit_profile=self.transit_profile,
            top_count=top_count,
            include_natal_chart=include_natal_chart,
            zodiac_offset=self._zodiac_offset(
                datetime_to_julian_day(target_instant.astimezone(timezone.utc))
            ),
        )

    def returns(
        self,
        natal_chart: NatalChart,
        body: str,
        window_start: datetime,
        window_end: datetime,
        include_charts: bool = False,
    ) -> ReturnSearchResult:
        """Every exact return of a body to its natal longitude inside a window.

        All hits, not the first: a body stationing near its natal degree returns
        three times, and a Saturn return usually does.
        """
        return calculate_returns(
            natal_chart=natal_chart,
            body=body,
            window_start=window_start,
            window_end=window_end,
            provider=self._get_provider(),
            chart_builder=(self._return_chart_builder(natal_chart) if include_charts else None),
            zodiac_offset=self._zodiac_offset_or_none(),
        )

    def _return_chart_builder(self, natal_chart: NatalChart) -> Callable[[datetime], NatalChart]:
        """Cast each return chart at the natal location, as convention requires."""

        def build(instant: datetime) -> NatalChart:
            return self.natal(
                local_datetime=instant.astimezone(timezone.utc).replace(tzinfo=None),
                timezone="UTC",
                latitude=natal_chart.subject.latitude,
                longitude=natal_chart.subject.longitude,
            )

        return build

    def search_events(
        self,
        event_type: str,
        body: str,
        start: datetime,
        end: datetime,
        target_longitude: float | None = None,
        aspect_angle: float | None = None,
    ) -> EventSearchResult:
        """Locate ingresses, stations, exact longitudes or exact aspects."""
        provider = self._get_provider()
        offset = self._zodiac_offset_or_none()
        if event_type == "sign_ingress":
            events: tuple[Any, ...] = find_sign_ingresses(
                provider, body, start, end, zodiac_offset=offset
            )
        elif event_type == "station":
            events = find_stations(provider, body, start, end, zodiac_offset=offset)
        elif event_type == "exact_longitude":
            if target_longitude is None:
                raise InvalidCalculationProfileError(
                    "exact_longitude search requires target_longitude.",
                    {"eventType": event_type},
                )
            events = find_longitude_crossings(
                provider, body, target_longitude, start, end, zodiac_offset=offset
            )
        elif event_type == "exact_aspect":
            if target_longitude is None or aspect_angle is None:
                raise InvalidCalculationProfileError(
                    "exact_aspect search requires target_longitude and aspect_angle.",
                    {"eventType": event_type},
                )
            events = find_aspect_events(
                provider,
                body,
                target_longitude,
                aspect_angle,
                start,
                end,
                zodiac_offset=offset,
            )
        else:
            raise InvalidCalculationProfileError(
                "Unsupported event type.",
                {"eventType": event_type},
            )

        return EventSearchResult(
            schema_version=EVENT_SCHEMA_VERSION,
            meta={
                "engine": ENGINE_NAME,
                "engineVersion": ENGINE_VERSION,
                "ephemerisProvider": provider.id,
                "ephemerisDataVersion": provider.data_version,
                "method": "coarse_bracket_then_bisection",
                "zodiac": self.profile.zodiac,
                "ayanamsa": self.profile.ayanamsa,
            },
            query={
                "type": event_type,
                "body": body,
                "from": start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "to": end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "targetLongitude": target_longitude,
                "aspectAngle": aspect_angle,
            },
            events=events,
        )

    def draconic(self, chart: NatalChart) -> TransformedChart:
        """Re-zero the zodiac on the lunar node.

        The node lands at exactly 0 Aries by construction, which is the
        definition of the transform and therefore assertable exactly.
        """
        return calculate_draconic(chart, self.profile)

    def harmonic(self, chart: NatalChart, harmonic: int) -> TransformedChart:
        """The harmonic-n chart: every longitude multiplied by n, modulo 360.

        Not a rotation. Aspects are deliberately not preserved -- collapsing one
        aspect family onto conjunctions is what a harmonic chart is for.
        """
        return calculate_harmonic(chart, harmonic, self.profile)

    def progressions(self, chart: NatalChart, target: datetime) -> TransformedChart:
        """The secondary-progressed chart for an instant: one day per year of life."""
        return calculate_secondary_progressions(
            chart, target, self.profile, self.progression_profile, self.natal
        )

    def solar_arc(self, chart: NatalChart, target: datetime) -> TransformedChart:
        """Direct every natal point by the progressed Sun's travel."""
        return calculate_solar_arc(
            chart, target, self.profile, self.solar_arc_profile, self.natal
        )

    def patterns(self, chart: NatalChart) -> tuple[ChartPattern, ...]:
        """Named configurations in a chart, under the versioned pattern profile.

        Detection is geometric, not heuristic: a grand trine is three bodies
        mutually trine within the profile's orb, or it is not reported.
        """
        return find_patterns(chart.bodies, self.pattern_profile)

    def relocate(
        self,
        chart: NatalChart,
        latitude: float,
        longitude: float,
        house_system: str | None = None,
        altitude_m: float | None = None,
    ) -> NatalChart:
        """Recast the same birth moment for a different place.

        The sky is unchanged, so body longitudes and every aspect are carried
        over untouched. Only the angles, cusps and house placements differ.
        """
        return calculate_relocation(
            chart,
            latitude,
            longitude,
            self.profile,
            self._get_house_calculator(),
            house_system=house_system,
            altitude_m=altitude_m,
        )

    def astrocartography(
        self,
        chart: NatalChart,
        bodies: tuple[str, ...] | None = None,
        latitude_range: tuple[float, float] = DEFAULT_LATITUDE_RANGE,
        latitude_step: float = DEFAULT_LATITUDE_STEP,
    ) -> dict[str, Any]:
        """Where on Earth each body sits on an angle, for this chart's instant.

        The instant is fixed and only the observer moves, so every line is
        closed form.
        """
        if not chart.subject.birth_time_known:
            # An unknown-time chart is stamped with local midnight so its bodies
            # can still be calculated, and for a planet that placeholder costs a
            # fraction of a degree. Here it costs everything: these lines are the
            # angles drawn as a function of place, and the angles turn a full
            # circle every day. A birth time unknown within the day puts the
            # lines anywhere on Earth -- measured at up to 141 degrees of
            # geographic longitude, most of an ocean -- so there is no degraded
            # answer to give, only a wrong one.
            raise UnknownBirthTimeError(
                "Astrocartography lines are the chart's angles drawn across the "
                "map, and a chart without a birth time has no angles. The lines "
                "would move most of the way round the world with the unknown "
                "hour. No substitute time was used.",
                {"birthTimeKnown": False},
            )

        calculator = self._get_armc_house_calculator()
        obliquity = calculator.obliquity(chart.subject.julian_day)
        sidereal_time = SwissHouseCalculator(
            ephemeris_path=getattr(calculator, "ephemeris_path", None)
        ).sidereal_time_degrees(chart.subject.julian_day)

        swiss = SwissHouseCalculator(
            ephemeris_path=getattr(calculator, "ephemeris_path", None)
        )
        # Where a body is angular on Earth is a physical fact and cannot depend
        # on which zodiac the chart labels its positions with. A sidereal chart
        # has already had its longitudes rotated, so the rotation is undone
        # before converting to equatorial -- otherwise every line lands about
        # 2,500 km from where the body actually is.
        offset = (
            chart.meta.ayanamsa_degrees
            if chart.meta.zodiac == "sidereal" and chart.meta.ayanamsa_degrees is not None
            else 0.0
        )
        equatorial = {
            body_id: swiss.to_equatorial(
                normalize_longitude(body.longitude + offset), body.latitude, obliquity
            )
            for body_id, body in chart.bodies.items()
        }
        result = calculate_astrocartography(
            equatorial,
            sidereal_time,
            bodies=bodies,
            latitude_range=latitude_range,
            latitude_step=latitude_step,
        )
        result["chartInstant"] = chart.subject.utc_datetime
        result["obliquity"] = obliquity
        return result

    def optional_bodies(self, extra: tuple[str, ...] = ()) -> tuple[BodyCapability, ...]:
        """Which optional bodies this installation can actually calculate.

        Probed, not guessed: a numbered asteroid works only when its data file
        was provisioned, and asking is the only reliable way to know.
        """
        calculator = self._get_house_calculator()
        return available_optional_bodies(
            ephemeris_path=getattr(calculator, "ephemeris_path", None), extra=extra
        )

    def ephemeris(
        self,
        bodies: tuple[str, ...],
        start: datetime,
        end: datetime,
        step: timedelta,
        max_rows: int = DEFAULT_MAX_ROWS,
    ) -> dict[str, Any]:
        """A table of positions over a range, at a fixed step."""
        return generate_ephemeris(
            self._get_provider(),
            bodies,
            start,
            end,
            step,
            max_rows,
            zodiac=self.profile.zodiac,
            ayanamsa=self.profile.ayanamsa,
            zodiac_offset=self._zodiac_offset_or_none(),
        )

    def _zodiac_offset(self, julian_day: float) -> float:
        """Degrees to subtract from a tropical longitude for this engine's zodiac.

        Internal: this is a frame conversion, not a capability. The value it
        returns is published in the `meta` of every result that depends on it,
        so a caller never has to ask for it separately.

        Zero for tropical. Providers always answer tropically, so every path
        that reaches a provider directly -- transits, returns, event search,
        the ephemeris table -- has to apply this or it will quietly mix frames
        with a chart that has already been rotated.
        """
        if self.profile.zodiac != "sidereal":
            return 0.0
        profile = resolve_ayanamsa_profile(self.profile.ayanamsa or "")
        return self._get_ayanamsa_calculator().value(julian_day, profile)

    def _zodiac_offset_or_none(self) -> Callable[[float], float] | None:
        return None if self.profile.zodiac != "sidereal" else self._zodiac_offset

    def _get_ayanamsa_calculator(self) -> AyanamsaCalculator:
        if self._ayanamsa_calculator is None:
            self._ayanamsa_calculator = AyanamsaCalculator()
        return self._ayanamsa_calculator

    def _get_armc_house_calculator(self) -> ArmcHouseCalculator:
        """Reuse the configured Swiss calculator so composite shares its ephemeris path."""
        calculator = self._get_house_calculator()
        if isinstance(calculator, SwissHouseCalculator):
            return calculator
        return SwissHouseCalculator()

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
        aspects: tuple[Aspect, ...] = (),
    ) -> DerivedNatal:
        rising = house_calculation.angles["ascendant"].sign if house_calculation else None
        moon_phase = None
        if "sun" in bodies and "moon" in bodies:
            moon_phase = calculate_moon_phase(bodies["sun"], bodies["moon"])
        sun = bodies.get("sun")
        moon = bodies.get("moon")

        # Rulership needs no ephemeris, only the signs above and the table the
        # profile names. It is resolved per chart rather than cached on the
        # engine so that a profile swap cannot leave a stale table behind.
        rulership = resolve_rulership_profile(self.profile.rulership)
        angles = house_calculation.angles if house_calculation else {}
        houses = house_calculation.houses if house_calculation else ()
        ruler = chart_ruler(angles, bodies, rulership)
        body_dignities = dignities(bodies, rulership)
        chains = dispositor_chains(bodies, rulership)

        return DerivedNatal(
            chart_ruler=ruler,
            house_rulers=house_rulers(houses, bodies, rulership),
            dignities=body_dignities,
            dispositors=chains,
            final_dispositors=final_dispositors(chains),
            mutual_receptions=mutual_receptions(bodies, rulership),
            dominant_planets=dominant_planets(
                bodies,
                aspects,
                {dignity.body_id: dignity.state for dignity in body_dignities},
                ruler.body_id if ruler else None,
                self.dominant_profile,
            ),
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
        if profile.zodiac not in {"tropical", "sidereal"}:
            raise InvalidCalculationProfileError(
                "Unsupported zodiac.",
                {"zodiac": profile.zodiac, "supported": ["tropical", "sidereal"]},
            )
        if profile.zodiac == "sidereal":
            # Resolving here means an unusable profile fails at construction
            # rather than on the first chart.
            resolve_ayanamsa_profile(profile.ayanamsa or "")


def _to_sidereal_body(body: BodyPosition, ayanamsa: float) -> BodyPosition:
    """Rotate one body into the sidereal zodiac.

    Longitude, sign and degree change; latitude, distance, speed, retrograde and
    house do not. A house number is a relationship between two longitudes that
    both shift by the same amount, so it is invariant under the rotation.
    """
    zodiac = longitude_to_sidereal(body.longitude, ayanamsa)
    return BodyPosition(
        body_id=body.body_id,
        longitude=zodiac.longitude,
        latitude=body.latitude,
        distance=body.distance,
        speed_longitude=body.speed_longitude,
        retrograde=body.retrograde,
        sign=zodiac.sign,
        degree_in_sign=zodiac.degree_in_sign,
        house=body.house,
    )


def _to_sidereal_geometry(
    calculation: HouseCalculation,
    ayanamsa: float,
    house_system: str,
) -> HouseCalculation:
    """Move angles and cusps into the sidereal zodiac.

    Angles rotate, because an angle is a longitude. Cusps mostly rotate too --
    but not the sign-anchored ones. Whole Sign cusps are defined as the starts
    of signs, and sign boundaries do not rotate with the zodiac: rotating them
    by an ayanamsa puts every cusp at an arbitrary degree instead of at 0 of a
    sign. Those are rebuilt from the rotated Ascendant instead.
    """
    angles = {
        name: _to_sidereal_angle(angle, ayanamsa)
        for name, angle in calculation.angles.items()
    }

    if house_system in SIGN_ANCHORED:
        cusps = build_house_cusps(
            whole_sign_cusp_longitudes(angles["ascendant"].longitude)
        )
    else:
        cusps = build_house_cusps(
            tuple(
                longitude_to_sidereal(cusp.cusp_longitude, ayanamsa).longitude
                for cusp in calculation.houses
            )
        )

    return HouseCalculation(
        angles=angles,
        houses=cusps,
        algorithm_version=f"{calculation.algorithm_version}:sidereal",
        sequence_degenerate=is_sequence_degenerate(cusps),
    )


def _to_sidereal_angle(angle: AnglePosition, ayanamsa: float) -> AnglePosition:
    zodiac = longitude_to_sidereal(angle.longitude, ayanamsa)
    return AnglePosition(
        longitude=zodiac.longitude,
        sign=zodiac.sign,
        degree_in_sign=zodiac.degree_in_sign,
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
