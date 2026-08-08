Status: PASS

Phases 10, 11 and 12 — v0.3 Forecast and Returns.

Quality gates:
- ruff PASS
- mypy strict PASS (74 source files)
- pytest PASS (236 passed, 0 skipped, with Swiss + JPL data present)

## The prohibition this release is built around

`03_CALCULATION_SPEC.md` section 12:

> Never implement exact-return/ingress/transit event search as "closest daily
> sample".

and the v0.3 Definition of Done repeats it: "no daily-sampling masquerading as
exact search".

A daily scan is wrong by up to twelve hours and misses outright any event that
begins and ends between two samples, which is exactly what happens to a fast
body near a station. Everything in `gbc_astro.search` and `gbc_astro.forecast`
therefore goes through one solver implementing the required pattern: coarse
stepping, bracketing, bisection refinement, tolerance stop, deduplication.

Time is carried as Julian Day because a root finder needs a continuous real
line and calendars are not one. `julian_day_to_datetime` was added as the
inverse of the existing conversion; measured round-trip error is under 0.02 ms
across 1582-2026.

## Solver precision

Tolerance is 1e-7 days. Achieved precision is reported per event from the real
bracket width rather than estimated, and measured across the corpus it is
**under 0.006 seconds**. Bisection was chosen over a faster method deliberately:
it cannot diverge and it maintains a guaranteed bracket at every step, so the
reported precision is a fact rather than a hope.

Two structural limitations are documented and tested rather than hidden:

- Two roots inside one coarse step cancel and both are missed. The step is
  therefore per body: the Moon covers thirteen degrees a day and gets 0.2 days,
  Pluto gets 5.
- A quantity that touches zero without crossing cannot be bracketed at all.
  This is why aspect search targets the two exact longitudes rather than the
  separation, which touches zero the same way.

## Reference validation

| Check | Expected | Found |
|---|---|---|
| March 2024 equinox | 2024-03-20 03:06 UTC | 2024-03-20T03:06:24Z |
| Sun ingresses in 2024 | 12, all direct | 12, all direct |
| Mercury retrograde periods 2024 | Apr, Aug, Nov | Apr 1, Aug 5, Nov 26 |
| Mars station direct 2025 | 23-24 Feb | 2025-02-24T01:59:48Z |

Stations are additionally checked structurally: speed before and after each one
must have opposite signs.

## Retrograde multi-hit

Not an edge case. Saturn's return for the committed natal chart:

```
natal longitude 312.1016
  #1  2021-04-11T04:20:13Z   direct
  #2  2021-07-05T18:00:35Z   retrograde
  #3  2022-01-02T19:50:06Z   direct
```

All three are exact returns and all three are reported, in order. Reducing them
to the first would discard most of what a Saturn return is. A test asserts the
count and the direction sequence, and another asserts that a Mercury retrograde
loop crosses the same degree three times in the order direct, retrograde,
direct — the case a nearest-daily-sample scan cannot represent at all.

Solar and lunar returns yield exactly one hit because neither body retrogrades,
which is asserted rather than assumed.

## Transits

Applying and separating are **real** here, unlike synastry. A transit chart has
a genuine shared timeline: the transiting body moves and the natal point does
not. `meta.phaseBasis` records this as
`transit_motion_against_fixed_natal_point`.

The labels are checked against the sky rather than trusted: a test recalculates
six hours later and asserts every aspect marked applying really is tighter,
excluding the Moon, which can pass exactness inside that window.

A natal chart without a birth time has no houses, so transit house placements
are omitted with a named warning while positions and aspects continue.

## Not in v0.3

Progressions, solar arc, relocation, sidereal, draconic, harmonics, extended
house systems, patterns and astrocartography are v1.0.

Schemas: transit `1.0.0`, event `1.0.0`, return `1.0.0`.
Surfaces: `engine.transits/returns/search_events`, `gbc transits|returns|events`,
`POST /v1/forecast/{transits,returns,events}`.
