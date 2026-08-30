"""Versions, bounds, and conservative speeds for unknown-time assessment.

The civil-day sampler is not an event search over years. It only has to see
what can happen inside one local date. Coarse samples are uniform in Julian
Day between independently converted endpoints so a 23-hour or 25-hour civil
day is just a shorter or longer JD span.

Conservative enclosure (not a Keplerian proof)
----------------------------------------------
Sampled endpoint speed is **not** a mathematical proof by itself. Between
adjacent samples ``dt`` days apart the engine uses tabulated safety ceilings:

* Travel: ``|Δλ| ≤ vmax · dt`` where
  ``vmax = max(table_speed, 1.25·|v_start|, 1.25·|v_end|)``.
* Speed change: ``|Δv| ≤ amax · dt`` from the acceleration table.

Those tables are empirical safety bounds for natal bodies over ~2-hour
segments, not a solar-system enclosure. If the bound cannot rule out a sign
crossing, station, orb entry/exit, or exact hit, the engine probes the
segment midpoint and/or bisects. If it still cannot prove the negative, the
property is ``uncertain`` with reason ``bound_unproven``.

The Moon table speed is 16.5°/day. Twelve JD intervals on a 24-hour day are
~2 hours; travel bound ~1.4°, so a 30° sign cannot be entered and left
between samples without the bound noticing.
"""

from __future__ import annotations

ASSESSMENT_VERSION = "v1"
SAMPLING_ALGORITHM_VERSION = "uniform-jd-v1.1"
ANCHOR = "start_of_local_day"

# Inclusive endpoints plus this many interior points. 12 intervals ≈ 2 hours
# on a 24-hour civil day, fewer on a 23-hour DST-spring day.
COARSE_INTERVALS = 12

# ~0.86 seconds. Finer than natal reporting; cheap relative to Swiss calls.
REFINEMENT_TOLERANCE_DAYS = 1.0e-5

# Speed below this (deg/day) is treated as stationary for classification.
STATION_SPEED_EPS = 1.0e-4

# Reject angular wraps when bracketing two-body exact hits.
ANGULAR_DISCONTINUITY = 180.0

# Hard cap on provider.position calls for one assessment, excluding the
# already-computed midnight natal snapshot. Coarse grid is 13 bodies × 12
# additional samples ≈ 156. Midpoint probes and refinement use the rest.
MAX_ASSESSMENT_EVALUATIONS = 768

CONSERVATIVE_SPEED_DEG_PER_DAY: dict[str, float] = {
    "sun": 1.1,
    "moon": 16.5,
    "mercury": 2.6,
    "venus": 1.4,
    "mars": 0.8,
    "jupiter": 0.25,
    "saturn": 0.15,
    "uranus": 0.08,
    "neptune": 0.05,
    "pluto": 0.05,
    "true_node": 0.15,
    "mean_node": 0.06,
    "chiron": 0.2,
    "mean_lilith": 0.6,
    "true_lilith": 4.0,
}
DEFAULT_CONSERVATIVE_SPEED = 2.0
OBSERVED_SPEED_MARGIN = 1.25

# Empirical |d²λ/dt²| ceilings in deg/day² for ~2-hour segments.
CONSERVATIVE_ACCEL_DEG_PER_DAY2: dict[str, float] = {
    "sun": 0.02,
    "moon": 2.0,
    "mercury": 4.0,
    "venus": 1.0,
    "mars": 0.3,
    "jupiter": 0.05,
    "saturn": 0.02,
    "uranus": 0.01,
    "neptune": 0.01,
    "pluto": 0.01,
    "true_node": 0.2,
    "mean_node": 0.01,
    "chiron": 0.05,
    "mean_lilith": 0.1,
    "true_lilith": 8.0,
}
DEFAULT_CONSERVATIVE_ACCEL = 1.0

PROPERTY_SIGN = "sign"
PROPERTY_MOTION = "motionDirection"
PROPERTY_LONGITUDE = "longitude"

REASON_EVALUATION_LIMIT = "evaluation_limit_reached"
REASON_BOUND_UNPROVEN = "bound_unproven"

UNAVAILABLE_WITHOUT_BIRTH_TIME: tuple[str, ...] = (
    "angles",
    "houses",
    "houseAssignments",
    "vertex",
    "antivertex",
    "partOfFortune",
    "chartRuler",
    "houseRulers",
    "synastryHouseOverlays",
    "angularity",
)


def conservative_speed(body_id: str, *observed_speeds: float | None) -> float:
    """Upper bound on |dλ/dt| in deg/day over a short segment.

    Uses the tabulated ceiling and a 25% margin on every supplied sample
    speed. Missing speeds do not shrink the bound.
    """

    table = CONSERVATIVE_SPEED_DEG_PER_DAY.get(body_id, DEFAULT_CONSERVATIVE_SPEED)
    observed = [abs(speed) for speed in observed_speeds if speed is not None]
    peaked = max(observed, default=0.0) * OBSERVED_SPEED_MARGIN
    return max(table, peaked, 0.01)


def conservative_accel(body_id: str) -> float:
    """Upper bound on |d²λ/dt²| in deg/day² for a short segment."""

    return CONSERVATIVE_ACCEL_DEG_PER_DAY2.get(body_id, DEFAULT_CONSERVATIVE_ACCEL)


def segment_may_station(
    body_id: str,
    speed_start: float | None,
    speed_end: float | None,
    timestep_days: float,
) -> bool:
    """Whether speed zero is possible between two samples under the accel bound.

    Same-sign endpoint speeds are not proof of no station.
    """

    if speed_start is None or speed_end is None:
        return True
    if abs(speed_start) <= STATION_SPEED_EPS or abs(speed_end) <= STATION_SPEED_EPS:
        return True
    if (speed_start > 0.0) != (speed_end > 0.0):
        return True
    max_dv = conservative_accel(body_id) * max(timestep_days, 0.0)
    return min(abs(speed_start), abs(speed_end)) <= max_dv + STATION_SPEED_EPS
