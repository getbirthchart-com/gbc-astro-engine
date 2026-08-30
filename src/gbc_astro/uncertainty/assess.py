"""Build a versioned unknown-time uncertainty assessment.

Known-time callers must not invoke this module. The midnight natal snapshot
stays the compatibility anchor; this assessment is additive.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from itertools import combinations

from gbc_astro.astronomy.circular import (
    directed_circular_delta,
    normalize_longitude,
    shortest_angular_distance,
)
from gbc_astro.astronomy.time import isoformat_z, julian_day_to_datetime
from gbc_astro.constants import BODY_IDS
from gbc_astro.models.position import BodyPosition
from gbc_astro.models.uncertainty import (
    AspectUncertainty,
    BodyUncertainty,
    UnknownTimeAssessment,
)
from gbc_astro.profiles.additional import additional_body_ids
from gbc_astro.profiles.model import AspectProfile, CalculationProfile
from gbc_astro.providers.base import EphemerisProvider
from gbc_astro.search.solver import find_roots
from gbc_astro.uncertainty.constants import (
    ANCHOR,
    ANGULAR_DISCONTINUITY,
    ASSESSMENT_VERSION,
    COARSE_INTERVALS,
    MAX_ASSESSMENT_EVALUATIONS,
    PROPERTY_LONGITUDE,
    PROPERTY_MOTION,
    PROPERTY_SIGN,
    REASON_BOUND_UNPROVEN,
    REASON_EVALUATION_LIMIT,
    REFINEMENT_TOLERANCE_DAYS,
    SAMPLING_ALGORITHM_VERSION,
    STATION_SPEED_EPS,
    UNAVAILABLE_WITHOUT_BIRTH_TIME,
    conservative_speed,
    segment_may_station,
)
from gbc_astro.uncertainty.interval import (
    CivilDayInterval,
    sample_julian_days,
)
from gbc_astro.uncertainty.motion import (
    circular_range_deg,
    motion_label,
    signs_covering,
    unwrap_longitudes,
)


class _BudgetExhausted(Exception):
    """Internal: stop refining and classify remaining items as unproven."""


class PositionCache:
    """Memoised tropical-or-sidereal longitudes with a hard evaluation cap."""

    def __init__(
        self,
        provider: EphemerisProvider,
        ayanamsa_degrees: float | None,
        max_evaluations: int,
    ) -> None:
        self._provider = provider
        self._ayanamsa = 0.0 if ayanamsa_degrees is None else ayanamsa_degrees
        self.max_evaluations = max_evaluations
        self.evaluations = 0
        self.exhausted = False
        self._cache: dict[tuple[str, float], tuple[float, float | None]] = {}

    def seed(self, body_id: str, julian_day: float, longitude: float, speed: float | None) -> None:
        self._cache[(body_id, julian_day)] = (normalize_longitude(longitude), speed)

    def at(self, body_id: str, julian_day: float) -> tuple[float, float | None]:
        key = (body_id, julian_day)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        if self.evaluations >= self.max_evaluations:
            self.exhausted = True
            raise _BudgetExhausted
        raw = self._provider.position(body_id, julian_day_to_datetime(julian_day))
        self.evaluations += 1
        longitude = normalize_longitude(raw.longitude_deg - self._ayanamsa)
        value = (longitude, raw.longitude_speed_deg_per_day)
        self._cache[key] = value
        return value


def assess_unknown_time(
    *,
    provider: EphemerisProvider,
    profile: CalculationProfile,
    interval: CivilDayInterval,
    seed_bodies: dict[str, BodyPosition],
    seed_julian_day: float,
    ayanamsa_degrees: float | None = None,
    ayanamsa_version: str | None = None,
    max_evaluations: int | None = None,
) -> UnknownTimeAssessment:
    """Classify bodies and aspects over the civil-day interval.

    `seed_bodies` are the midnight-anchor positions already computed for the
    natal document. They are reused so the start sample does not cost a second
    ephemeris call. Hitting ``max_evaluations`` fail-closes: nothing stays
    ``stable``, ``assessmentComplete`` is false, and reasons include
    ``evaluation_limit_reached``.
    """

    budget = MAX_ASSESSMENT_EVALUATIONS if max_evaluations is None else max_evaluations
    body_ids = BODY_IDS + additional_body_ids(profile.additional_points)
    cache = PositionCache(provider, ayanamsa_degrees, budget)
    for body_id in body_ids:
        body = seed_bodies[body_id]
        cache.seed(body_id, seed_julian_day, body.longitude, body.speed_longitude)
        cache.seed(body_id, interval.start_jd, body.longitude, body.speed_longitude)

    grid = sample_julian_days(interval, COARSE_INTERVALS)
    samples: dict[str, list[tuple[float, float, float | None]]] = {
        body_id: [] for body_id in body_ids
    }
    try:
        for julian_day in grid:
            for body_id in body_ids:
                longitude, speed = cache.at(body_id, julian_day)
                samples[body_id].append((julian_day, longitude, speed))
    except _BudgetExhausted:
        pass

    bodies = {
        body_id: (
            _assess_body(body_id, samples[body_id], cache, interval, seed_bodies[body_id])
            if samples[body_id]
            else _unproven_body(body_id, seed_bodies[body_id])
        )
        for body_id in body_ids
    }
    aspects = _assess_aspects(
        profile.aspect_bodies,
        profile.aspect_profile,
        samples,
        cache,
        interval,
    )
    complete = not cache.exhausted
    if not complete:
        bodies = {
            body_id: _demote_body(body) for body_id, body in bodies.items()
        }
        aspects = {key: _demote_aspect(aspect) for key, aspect in aspects.items()}
    return UnknownTimeAssessment(
        version=ASSESSMENT_VERSION,
        algorithm_version=SAMPLING_ALGORITHM_VERSION,
        anchor=ANCHOR,
        interval=interval.to_dict(),
        bodies=bodies,
        aspects=aspects,
        unavailable=UNAVAILABLE_WITHOUT_BIRTH_TIME,
        ephemeris_evaluations=cache.evaluations,
        coarse_samples=len(grid),
        max_evaluations=budget,
        evaluation_budget_exhausted=cache.exhausted,
        assessment_complete=complete,
        zodiac=profile.zodiac,
        ayanamsa=profile.ayanamsa,
        ayanamsa_version=ayanamsa_version,
        ayanamsa_degrees=ayanamsa_degrees,
    )


def _merge_samples(
    samples: Sequence[tuple[float, float, float | None]],
    extra: Sequence[tuple[float, float, float | None]],
) -> list[tuple[float, float, float | None]]:
    merged = {(item[0], item[1], item[2]) for item in samples}
    merged.update(extra)
    return sorted(merged, key=lambda item: item[0])


def _property_lists(
    sign_status: str,
    motion_status: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    stable: list[str] = []
    uncertain = [PROPERTY_LONGITUDE]
    if sign_status == "stable":
        stable.append(PROPERTY_SIGN)
    else:
        uncertain.append(PROPERTY_SIGN)
    if motion_status == "stable":
        stable.append(PROPERTY_MOTION)
    else:
        uncertain.append(PROPERTY_MOTION)
    return tuple(stable), tuple(uncertain)


def _unproven_body(body_id: str, seed: BodyPosition) -> BodyUncertainty:
    unwrapped = unwrap_longitudes((seed.longitude,))
    possible = signs_covering(unwrapped)
    motion = motion_label(seed.speed_longitude)
    stable, uncertain = _property_lists("uncertain", "uncertain")
    return BodyUncertainty(
        body_id=body_id,
        anchor_longitude=seed.longitude,
        start_longitude=seed.longitude,
        end_longitude=seed.longitude,
        longitude_range=0.0,
        possible_signs=possible,
        sign_changed=False,
        motion_start=motion,
        motion_end=motion,
        motion_states=(motion,),
        station_in_interval=False,
        sign_status="uncertain",
        motion_status="uncertain",
        longitude_status="uncertain",
        stable_properties=stable,
        uncertain_properties=uncertain,
        classification="uncertain",
        reasons=(REASON_EVALUATION_LIMIT, REASON_BOUND_UNPROVEN),
    )


def _demote_body(body: BodyUncertainty) -> BodyUncertainty:
    reasons = (
        body.reasons
        if REASON_EVALUATION_LIMIT in body.reasons
        else (*body.reasons, REASON_EVALUATION_LIMIT)
    )
    stable, uncertain = _property_lists("uncertain", "uncertain")
    return replace(
        body,
        sign_status="uncertain",
        motion_status="uncertain",
        longitude_status="uncertain",
        stable_properties=stable,
        uncertain_properties=uncertain,
        classification="uncertain",
        reasons=reasons,
    )


def _demote_aspect(aspect: AspectUncertainty) -> AspectUncertainty:
    reasons = aspect.reasons
    if REASON_EVALUATION_LIMIT not in reasons:
        reasons = (*reasons, REASON_EVALUATION_LIMIT)
    return replace(aspect, classification="uncertain", reasons=reasons)


def _assess_body(
    body_id: str,
    samples: Sequence[tuple[float, float, float | None]],
    cache: PositionCache,
    interval: CivilDayInterval,
    seed: BodyPosition,
) -> BodyUncertainty:
    ordered = list(samples)
    may_station = _speed_may_cross_zero(body_id, ordered)
    if may_station:
        ordered = _merge_samples(ordered, _refine_speed_roots(body_id, cache, interval))
        ordered = _merge_samples(ordered, _probe_speed_midpoints(body_id, ordered, cache))

    unwrapped = list(unwrap_longitudes([item[1] for item in ordered]))
    speeds = [item[2] for item in ordered]
    extra_travel = _max_segment_travel(body_id, ordered)
    lo = min(unwrapped)
    hi = max(unwrapped)
    expanded_signs = signs_covering((lo - extra_travel, hi + extra_travel))
    sampled_signs = signs_covering(unwrapped)
    sign_bound_open = bool(set(expanded_signs) - set(sampled_signs))
    if sign_bound_open:
        ordered = _merge_samples(
            ordered, _refine_sign_boundaries(body_id, cache, interval, expanded_signs)
        )
        ordered = _merge_samples(ordered, _probe_longitude_midpoints(body_id, ordered, cache))
        unwrapped = list(unwrap_longitudes([item[1] for item in ordered]))
        speeds = [item[2] for item in ordered]
        extra_travel = _max_segment_travel(body_id, ordered)
        lo = min(unwrapped)
        hi = max(unwrapped)
        expanded_signs = signs_covering((lo - extra_travel, hi + extra_travel))
        sampled_signs = signs_covering(unwrapped)
        sign_bound_open = bool(set(expanded_signs) - set(sampled_signs))

    longitudes = [item[1] for item in ordered]
    possible = signs_covering(unwrapped)
    sign_changed = len(possible) > 1
    motion_states = tuple(dict.fromkeys(motion_label(speed) for speed in speeds))
    observed_station = _observed_station(ordered)
    bound_open_station = _speed_may_cross_zero(body_id, ordered)
    station_in_interval = observed_station
    reasons: list[str] = []
    reasons.append("sign_changed" if sign_changed else "sign_unchanged")
    reasons.append("station_in_interval" if station_in_interval else "motion_sign_stable")
    raw_span = abs(longitudes[-1] - longitudes[0])
    if raw_span > 180.0 and circular_range_deg(unwrapped) < 180.0:
        reasons.append("wrap_unwrapped")
    reasons.append("longitude_time_dependent")

    sign_proven = not sign_changed and not sign_bound_open
    motion_proven = not observed_station and not bound_open_station
    if sign_bound_open or (bound_open_station and not observed_station):
        reasons.append(REASON_BOUND_UNPROVEN)
    if cache.exhausted:
        reasons.append(REASON_EVALUATION_LIMIT)
        sign_status = "uncertain"
        motion_status = "uncertain"
        classification = "uncertain"
    else:
        sign_status = "stable" if sign_proven else "uncertain"
        motion_status = "stable" if motion_proven else "uncertain"
        if sign_proven:
            reasons.append("bound_cannot_change_sign")
        else:
            reasons.append("crossing_unproven")
        classification = "stable" if sign_proven and motion_proven else "uncertain"

    stable, uncertain = _property_lists(sign_status, motion_status)
    return BodyUncertainty(
        body_id=body_id,
        anchor_longitude=seed.longitude,
        start_longitude=longitudes[0],
        end_longitude=longitudes[-1],
        longitude_range=circular_range_deg(unwrapped),
        possible_signs=possible,
        sign_changed=sign_changed,
        motion_start=motion_label(speeds[0]),
        motion_end=motion_label(speeds[-1]),
        motion_states=motion_states,
        station_in_interval=station_in_interval,
        sign_status=sign_status,
        motion_status=motion_status,
        longitude_status="uncertain",
        stable_properties=stable,
        uncertain_properties=uncertain,
        classification=classification,
        reasons=tuple(reasons),
    )


def _max_segment_travel(
    body_id: str,
    samples: Sequence[tuple[float, float, float | None]],
) -> float:
    travel = 0.0
    for index in range(len(samples) - 1):
        dt = samples[index + 1][0] - samples[index][0]
        vmax = conservative_speed(body_id, samples[index][2], samples[index + 1][2])
        travel = max(travel, vmax * dt)
    return travel


def _observed_station(samples: Sequence[tuple[float, float, float | None]]) -> bool:
    speeds = [item[2] for item in samples]
    if any(speed is not None and abs(speed) <= STATION_SPEED_EPS for speed in speeds):
        return True
    for first, second in zip(speeds, speeds[1:], strict=False):
        if first is None or second is None:
            continue
        if (first > 0.0) != (second > 0.0):
            return True
    return False


def _speed_may_cross_zero(
    body_id: str,
    samples: Sequence[tuple[float, float, float | None]],
) -> bool:
    speeds = [item[2] for item in samples]
    if any(speed is not None and abs(speed) <= STATION_SPEED_EPS for speed in speeds):
        return True
    for index in range(len(samples) - 1):
        if segment_may_station(
            body_id,
            samples[index][2],
            samples[index + 1][2],
            samples[index + 1][0] - samples[index][0],
        ):
            return True
    return False


def _probe_speed_midpoints(
    body_id: str,
    samples: Sequence[tuple[float, float, float | None]],
    cache: PositionCache,
) -> tuple[tuple[float, float, float | None], ...]:
    points: list[tuple[float, float, float | None]] = []
    try:
        for index in range(len(samples) - 1):
            if not segment_may_station(
                body_id,
                samples[index][2],
                samples[index + 1][2],
                samples[index + 1][0] - samples[index][0],
            ):
                continue
            mid = (samples[index][0] + samples[index + 1][0]) / 2.0
            longitude, speed = cache.at(body_id, mid)
            points.append((mid, longitude, speed))
    except _BudgetExhausted:
        return tuple(points)
    return tuple(points)


def _probe_longitude_midpoints(
    body_id: str,
    samples: Sequence[tuple[float, float, float | None]],
    cache: PositionCache,
) -> tuple[tuple[float, float, float | None], ...]:
    points: list[tuple[float, float, float | None]] = []
    try:
        for index in range(len(samples) - 1):
            dt = samples[index + 1][0] - samples[index][0]
            vmax = conservative_speed(body_id, samples[index][2], samples[index + 1][2])
            delta = abs(
                directed_circular_delta(samples[index][1], samples[index + 1][1])
            )
            if vmax * dt <= delta + 1e-9:
                continue
            mid = (samples[index][0] + samples[index + 1][0]) / 2.0
            longitude, speed = cache.at(body_id, mid)
            points.append((mid, longitude, speed))
    except _BudgetExhausted:
        return tuple(points)
    return tuple(points)


def _refine_speed_roots(
    body_id: str,
    cache: PositionCache,
    interval: CivilDayInterval,
) -> tuple[tuple[float, float, float | None], ...]:
    step = max(interval.duration_days / COARSE_INTERVALS, 1e-6)

    def speed_fn(julian_day: float) -> float:
        speed = cache.at(body_id, julian_day)[1]
        return 0.0 if speed is None else speed

    try:
        roots = find_roots(
            speed_fn,
            interval.start_jd,
            interval.end_jd,
            step,
            tolerance_days=REFINEMENT_TOLERANCE_DAYS,
            discontinuity_threshold=10.0,
        )
    except _BudgetExhausted:
        return ()
    points: list[tuple[float, float, float | None]] = []
    for root in roots:
        try:
            longitude, speed = cache.at(body_id, root.julian_day)
        except _BudgetExhausted:
            break
        points.append((root.julian_day, longitude, speed))
    return tuple(points)


def _refine_sign_boundaries(
    body_id: str,
    cache: PositionCache,
    interval: CivilDayInterval,
    candidate_signs: Sequence[str],
) -> tuple[tuple[float, float, float | None], ...]:
    from gbc_astro.constants import SIGN_IDS

    boundaries = {SIGN_IDS.index(sign) * 30.0 for sign in candidate_signs}
    for sign in candidate_signs:
        boundaries.add(((SIGN_IDS.index(sign) + 1) % 12) * 30.0)
    step = max(interval.duration_days / COARSE_INTERVALS, 1e-6)
    points: list[tuple[float, float, float | None]] = []
    for boundary in sorted(boundaries):

        def residual(julian_day: float, target: float = boundary) -> float:
            return directed_circular_delta(target, cache.at(body_id, julian_day)[0])

        try:
            roots = find_roots(
                residual,
                interval.start_jd,
                interval.end_jd,
                step,
                tolerance_days=REFINEMENT_TOLERANCE_DAYS,
                discontinuity_threshold=ANGULAR_DISCONTINUITY,
            )
        except _BudgetExhausted:
            break
        for root in roots:
            try:
                longitude, speed = cache.at(body_id, root.julian_day)
            except _BudgetExhausted:
                return tuple(points)
            points.append((root.julian_day, longitude, speed))
    return tuple(points)


def _assess_aspects(
    aspect_bodies: tuple[str, ...],
    profile: AspectProfile,
    samples: dict[str, list[tuple[float, float, float | None]]],
    cache: PositionCache,
    interval: CivilDayInterval,
) -> dict[str, AspectUncertainty]:
    eligible = [body_id for body_id in aspect_bodies if samples.get(body_id)]
    results: dict[str, AspectUncertainty] = {}
    for body_a, body_b in combinations(eligible, 2):
        series_a = samples[body_a]
        series_b = samples[body_b]
        n = min(len(series_a), len(series_b))
        for rule in profile.rules:
            assessed = _assess_one_aspect(
                body_a,
                body_b,
                rule.aspect_type,
                rule.exact_angle,
                rule.orb,
                profile.exact_epsilon_deg,
                series_a[:n],
                series_b[:n],
                cache,
                interval,
            )
            if assessed is None:
                continue
            key = f"{body_a}|{body_b}|{rule.aspect_type}"
            results[key] = assessed
    return results


def _assess_one_aspect(
    body_a: str,
    body_b: str,
    aspect_type: str,
    exact_angle: float,
    orb: float,
    exact_epsilon: float,
    series_a: Sequence[tuple[float, float, float | None]],
    series_b: Sequence[tuple[float, float, float | None]],
    cache: PositionCache,
    interval: CivilDayInterval,
) -> AspectUncertainty | None:
    tightness: list[float] = []
    in_orb: list[bool] = []
    phases: list[str] = []
    for sample_a, sample_b in zip(series_a, series_b, strict=False):
        sep = shortest_angular_distance(sample_a[1], sample_b[1])
        delta = abs(sep - exact_angle)
        tightness.append(delta)
        inside = delta <= orb + 1e-12
        in_orb.append(inside)
        if inside:
            phases.append(
                _phase(
                    sample_a[1],
                    sample_a[2],
                    sample_b[1],
                    sample_b[2],
                    exact_angle,
                    delta,
                    exact_epsilon,
                )
            )

    might_enter = False
    might_leave = False
    might_exact = False
    for index in range(len(series_a) - 1):
        dt = series_a[index + 1][0] - series_a[index][0]
        rel = conservative_speed(
            body_a, series_a[index][2], series_a[index + 1][2]
        ) + conservative_speed(body_b, series_b[index][2], series_b[index + 1][2])
        max_dsep = rel * dt
        edge = tightness[index]
        if in_orb[index] and (orb - edge) < max_dsep:
            might_leave = True
        if not in_orb[index] and (edge - orb) < max_dsep:
            might_enter = True
        if edge < max_dsep:
            might_exact = True

    any_in = any(in_orb)
    all_in = bool(in_orb) and all(in_orb)
    if not any_in and not might_enter:
        return None

    enter_at = leave_at = exact_at = None
    exact_hit = any(delta <= exact_epsilon for delta in tightness)
    if might_enter or might_leave or (any_in and not all_in):
        crossings = _refine_orb_crossings(
            body_a, body_b, exact_angle, orb, cache, interval, series_a, series_b
        )
        enter_at, leave_at = crossings
    if might_exact or exact_hit:
        exact_at = _refine_exact(
            body_a, body_b, exact_angle, cache, interval, series_a
        )
        if exact_at is not None:
            exact_hit = True

    if all_in:
        presence = "all_day"
    elif any_in or enter_at is not None or leave_at is not None:
        presence = "partial"
    else:
        return None

    unique_phases = tuple(dict.fromkeys(phases))
    phase_stable = len(unique_phases) == 1 and not exact_hit
    reasons: list[str] = []
    if presence == "all_day":
        reasons.append("in_orb_entire_interval")
    else:
        reasons.append("in_orb_part_of_interval")
    if exact_hit:
        reasons.append("exact_hit")
    if phase_stable:
        reasons.append("phase_stable")
    else:
        reasons.append("phase_changed_or_mixed")
    if presence == "all_day" and might_leave:
        reasons.append(REASON_BOUND_UNPROVEN)
    if cache.exhausted:
        reasons.append(REASON_EVALUATION_LIMIT)

    proven_all_day = presence == "all_day" and not might_leave and not cache.exhausted
    classification = (
        "stable" if proven_all_day and phase_stable and not exact_hit else "uncertain"
    )

    return AspectUncertainty(
        body_a=body_a,
        body_b=body_b,
        aspect_type=aspect_type,
        exact_angle=exact_angle,
        presence=presence,
        min_orb=min(tightness) if tightness else orb,
        max_orb=max(tightness) if tightness else orb,
        exact_hit=exact_hit,
        phase_stable=phase_stable,
        phases=unique_phases,
        enter_at=enter_at,
        exact_at=exact_at,
        leave_at=leave_at,
        classification=classification,
        reasons=tuple(reasons),
    )


def _phase(
    lon_a: float,
    speed_a: float | None,
    lon_b: float,
    speed_b: float | None,
    exact_angle: float,
    current_orb: float,
    exact_epsilon: float,
) -> str:
    if current_orb <= exact_epsilon:
        return "exact"
    if speed_a is None or speed_b is None:
        return "indeterminate"
    timestep_days = 1e-3
    future_a = normalize_longitude(lon_a + speed_a * timestep_days)
    future_b = normalize_longitude(lon_b + speed_b * timestep_days)
    future_orb = abs(shortest_angular_distance(future_a, future_b) - exact_angle)
    if future_orb + exact_epsilon < current_orb:
        return "applying"
    if future_orb > current_orb + exact_epsilon:
        return "separating"
    return "indeterminate"


def _refine_orb_crossings(
    body_a: str,
    body_b: str,
    exact_angle: float,
    orb: float,
    cache: PositionCache,
    _interval: CivilDayInterval,
    series_a: Sequence[tuple[float, float, float | None]],
    _series_b: Sequence[tuple[float, float, float | None]],
) -> tuple[str | None, str | None]:
    def residual(julian_day: float) -> float:
        lon_a = cache.at(body_a, julian_day)[0]
        lon_b = cache.at(body_b, julian_day)[0]
        return abs(shortest_angular_distance(lon_a, lon_b) - exact_angle) - orb

    enter_at = leave_at = None
    try:
        for first, second in zip(series_a, series_a[1:], strict=False):
            t0, t1 = first[0], second[0]
            r0, r1 = residual(t0), residual(t1)
            if r0 == 0.0:
                stamp = isoformat_z(julian_day_to_datetime(t0))
                if enter_at is None:
                    enter_at = stamp
                continue
            if (r0 > 0.0) != (r1 > 0.0):
                root = _bisect(residual, t0, t1)
                stamp = isoformat_z(julian_day_to_datetime(root))
                if r0 > 0.0 > r1 and enter_at is None:
                    enter_at = stamp
                elif r0 < 0.0 < r1 and leave_at is None:
                    leave_at = stamp
                continue
            mid = (t0 + t1) / 2.0
            r_mid = residual(mid)
            if r0 > 0.0 and r_mid < 0.0:
                if enter_at is None:
                    enter_at = isoformat_z(
                        julian_day_to_datetime(_bisect(residual, t0, mid))
                    )
                if r1 > 0.0 and leave_at is None:
                    leave_at = isoformat_z(
                        julian_day_to_datetime(_bisect(residual, mid, t1))
                    )
            elif r0 < 0.0 and r_mid > 0.0:
                if leave_at is None:
                    leave_at = isoformat_z(
                        julian_day_to_datetime(_bisect(residual, t0, mid))
                    )
                if r1 < 0.0 and enter_at is None:
                    enter_at = isoformat_z(
                        julian_day_to_datetime(_bisect(residual, mid, t1))
                    )
    except _BudgetExhausted:
        return enter_at, leave_at
    return enter_at, leave_at


def _refine_exact(
    body_a: str,
    body_b: str,
    exact_angle: float,
    cache: PositionCache,
    _interval: CivilDayInterval,
    series_a: Sequence[tuple[float, float, float | None]],
) -> str | None:
    targets = {
        normalize_longitude(exact_angle),
        normalize_longitude(-exact_angle),
    }

    def make_fn(offset: float) -> Callable[[float], float]:
        def residual(julian_day: float) -> float:
            lon_a = cache.at(body_a, julian_day)[0]
            lon_b = cache.at(body_b, julian_day)[0]
            return directed_circular_delta(normalize_longitude(lon_a + offset), lon_b)

        return residual

    first: float | None = None
    try:
        for offset in sorted(targets):
            fn = make_fn(offset)
            for left, right in zip(series_a, series_a[1:], strict=False):
                t0, t1 = left[0], right[0]
                r0, r1 = fn(t0), fn(t1)
                if abs(r0 - r1) > ANGULAR_DISCONTINUITY:
                    continue
                if r0 == 0.0:
                    julian_day = t0
                elif (r0 > 0.0) != (r1 > 0.0):
                    julian_day = _bisect(fn, t0, t1)
                else:
                    continue
                if first is None or julian_day < first:
                    first = julian_day
    except _BudgetExhausted:
        pass
    if first is None:
        return None
    return isoformat_z(julian_day_to_datetime(first))


def _bisect(function: Callable[[float], float], low: float, high: float) -> float:
    for _ in range(40):
        if high - low <= REFINEMENT_TOLERANCE_DAYS:
            break
        middle = (low + high) / 2.0
        if function(low) == 0.0:
            return low
        if (function(low) > 0.0) != (function(middle) > 0.0):
            high = middle
        else:
            low = middle
    return (low + high) / 2.0
