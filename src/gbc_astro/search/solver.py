"""Generic numerical event solver.

`03_CALCULATION_SPEC.md` section 12 is explicit about the required pattern and
about what is forbidden:

1. coarse stepping to detect candidate intervals
2. bracket the root
3. refine by bisection or a validated equivalent
4. stop on a time or angular tolerance
5. deduplicate adjacent detections

> Never implement exact-return/ingress/transit event search as "closest daily
> sample".

That prohibition is the reason this module exists. Sampling once per day and
picking the nearest sample gives an answer that is wrong by up to twelve hours
and silently misses every event that begins and ends between two samples, which
is exactly what happens to a fast body near a station. Everything in
`gbc_astro.search` and `gbc_astro.forecast` goes through `find_roots`.

Time is carried as Julian Day throughout: a continuous real line is what a root
finder needs, and calendars are not one.

Circular quantities
-------------------
A longitude residual jumps by 360 degrees when it wraps, which looks exactly
like a sign change to a bracketing scan. Callers working in angles pass
`discontinuity_threshold` so those jumps are rejected rather than reported as
events that never happened.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

SECONDS_PER_DAY = 86400.0

# One hundredth of a second. Far finer than any ephemeris is accurate, but the
# cost is a handful of extra bisection steps and it keeps the solver from being
# the limiting factor in any reported precision.
DEFAULT_TOLERANCE_DAYS = 1.0e-7

# Roots closer together than this are the same event found twice by adjacent
# brackets, not two events.
DEFAULT_DEDUPE_DAYS = 1.0e-4

MAX_BISECTION_ITERATIONS = 200


@dataclass(frozen=True)
class Root:
    """A located event, with enough detail to audit how it was found."""

    julian_day: float
    bracket_start: float
    bracket_end: float
    iterations: int
    residual: float
    precision_seconds: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "julianDay": self.julian_day,
            "bracketStart": self.bracket_start,
            "bracketEnd": self.bracket_end,
            "iterations": self.iterations,
            "residual": self.residual,
            "precisionSeconds": self.precision_seconds,
        }


def find_roots(
    function: Callable[[float], float],
    start_julian_day: float,
    end_julian_day: float,
    coarse_step_days: float,
    tolerance_days: float = DEFAULT_TOLERANCE_DAYS,
    discontinuity_threshold: float | None = None,
    dedupe_days: float = DEFAULT_DEDUPE_DAYS,
) -> tuple[Root, ...]:
    """Locate every sign change of `function` in the window.

    `coarse_step_days` decides what can be found at all: two roots inside one
    step cancel out and both are missed. Callers pick it from how fast the
    quantity moves, which is why `gbc_astro.search.events` keeps a per-body
    table rather than using one global default.

    `discontinuity_threshold` rejects jumps larger than the given magnitude as
    wraps rather than roots. Angular callers pass 180.
    """
    if end_julian_day <= start_julian_day:
        return ()
    if coarse_step_days <= 0.0:
        raise ValueError("coarse_step_days must be positive.")

    roots: list[Root] = []
    steps = max(1, int(math.ceil((end_julian_day - start_julian_day) / coarse_step_days)))

    previous_time = start_julian_day
    previous_value = function(previous_time)

    for index in range(1, steps + 1):
        current_time = min(start_julian_day + index * coarse_step_days, end_julian_day)
        current_value = function(current_time)

        if _is_bracket(previous_value, current_value, discontinuity_threshold):
            roots.append(
                _refine(function, previous_time, current_time, tolerance_days)
            )
        elif previous_value == 0.0:
            roots.append(
                Root(
                    julian_day=previous_time,
                    bracket_start=previous_time,
                    bracket_end=previous_time,
                    iterations=0,
                    residual=0.0,
                    precision_seconds=0.0,
                )
            )

        previous_time, previous_value = current_time, current_value
        if current_time >= end_julian_day:
            break

    return _deduplicate(roots, dedupe_days)


def _is_bracket(
    first: float,
    second: float,
    discontinuity_threshold: float | None,
) -> bool:
    if math.isnan(first) or math.isnan(second):
        return False
    if not (first < 0.0 < second or second < 0.0 < first):
        return False
    # A jump larger than the threshold is a wrap, not a crossing.
    return not (
        discontinuity_threshold is not None
        and abs(second - first) > discontinuity_threshold
    )


def _refine(
    function: Callable[[float], float],
    low: float,
    high: float,
    tolerance_days: float,
) -> Root:
    """Bisect a bracketed interval down to the time tolerance.

    Bisection rather than a faster method on purpose: it cannot diverge, and it
    keeps a guaranteed bracket at every step, so the reported precision is the
    real interval width rather than an estimate.
    """
    bracket_start, bracket_end = low, high
    low_value = function(low)
    iterations = 0

    while high - low > tolerance_days and iterations < MAX_BISECTION_ITERATIONS:
        middle = (low + high) / 2.0
        middle_value = function(middle)
        iterations += 1
        if middle_value == 0.0:
            low = high = middle
            low_value = 0.0
            break
        if (low_value < 0.0) != (middle_value < 0.0):
            high = middle
        else:
            low, low_value = middle, middle_value

    julian_day = (low + high) / 2.0
    return Root(
        julian_day=julian_day,
        bracket_start=bracket_start,
        bracket_end=bracket_end,
        iterations=iterations,
        residual=function(julian_day),
        precision_seconds=abs(high - low) * SECONDS_PER_DAY,
    )


def _deduplicate(roots: list[Root], dedupe_days: float) -> tuple[Root, ...]:
    """Merge detections that are the same event seen from adjacent brackets."""
    if not roots:
        return ()
    ordered = sorted(roots, key=lambda root: root.julian_day)
    kept = [ordered[0]]
    for root in ordered[1:]:
        if root.julian_day - kept[-1].julian_day > dedupe_days:
            kept.append(root)
        elif abs(root.residual) < abs(kept[-1].residual):
            kept[-1] = root
    return tuple(kept)
