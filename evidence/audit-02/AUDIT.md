# Audit 02 — correctness review of the remaining v1.0 modules

Seven bugs, one shape. Every one was a feature combination that worked in
isolation and had never been exercised together, so the suite stayed green
throughout while the engine returned wrong numbers. None was found by reading
code for suspicious lines; all seven came from deliberately crossing one axis
against every module.

The suite went from 452 to 466 tests. Fourteen of those are the tests that
would have caught these.

## Axis 1 — sidereal × every module

The zodiac was applied as a final rotation inside `natal()`. Every other path
called `provider.position()` directly, and providers always answer tropically.
So a sidereal chart was compared against tropical positions, silently.

| # | Module | What it did | Error |
|---|--------|-------------|-------|
| 1 | `forecast/transits` | Aspected tropical transits against a sidereal natal chart | every contact out by the whole ayanamsa, 24.23° |
| 2 | `forecast/returns` | Searched tropical longitudes for a sidereal target | found nothing, then reported `NO_RETURN_IN_WINDOW` as though that were an answer |
| 3 | `charts/astrocartography` | Converted already-rotated longitudes to equatorial | lines 22.69° of geographic longitude out, about 2,500 km |
| 4 | `search/events` | Located tropical sign boundaries on a sidereal engine | Sun into Aries reported 20 Mar instead of 14 Apr |
| 5 | `charts/ephemeris` | Ignored the engine's zodiac, declared no zodiac at all | tropical table from a sidereal engine, unlabelled |

Fixed by giving the engine a private `_zodiac_offset(julian_day)` and threading
it to every path that reaches a provider. The offset is published in the `meta`
of every result that depends on it, so a caller never has to ask.

Bug 2 is the one worth remembering: it did not produce a wrong number, it
produced a *plausible absence*. "This body does not return in this window" is a
legitimate answer for some inputs, so nothing looked broken.

Bug 3 is the invariant in the other direction. Where a planet is angular on
Earth is a physical fact; it cannot depend on which zodiac the chart labels its
positions with. Now asserted to nine decimal places.

### Two apparent bugs that were my checks being wrong, not the code

- **Draconic** looked zodiac-dependent and is not. Subtracting the node cancels
  the ayanamsa, because both carry it. Verified equal to 1e-6.
- **Progressions** showed a 4.7″ discrepancy I first read as a dropped rotation.
  It is the ayanamsa's own drift — 0.1377″/day over the 33.76 days between the
  natal and progressed instants. The progressed chart correctly uses the
  ayanamsa of *its own* moment. The code was right both times.

## Axis 2 — unknown birth time × every module

`davison`, `progressions`, `solar_arc` and `relocate` all refuse an unknown-time
chart, each naming its reason and stating that no substitute time was used.

| # | Module | What it did | Error |
|---|--------|-------------|-------|
| 6 | `charts/astrocartography` | Answered anyway, no warning | 141.25° of geographic longitude |

An unknown-time chart is stamped with local midnight so its bodies can still be
calculated; for a planet that placeholder costs a fraction of a degree. Here it
costs everything, because these lines *are* the angles drawn as a function of
place and the angles turn a full circle every day. There is no degraded answer
to give, only a wrong one, so it now refuses like its siblings.

## Axis 3 — non-default house system × derived charts

| # | Module | What it did | Error |
|---|--------|-------------|-------|
| 7 | `transforms/progressions` | Recast internally on the profile default | crash for polar births; wrong provenance everywhere |

`calculate_secondary_progressions` rebuilt the progressed chart through
`natal()` without passing a house system, so it always used the profile default
(Placidus) regardless of the source chart.

The angles themselves were unaffected — ASC, MC, DSC and IC are identical across
all eleven systems, verified — so no published number changes. What changed is
availability: a birth in Tromsø (69.65°N, a real city of 77,000) cast its natal
chart fine in whole sign and then **crashed** on progressions and solar arc, on
a house system the caller never chose. Fixed by carrying the source chart's own
system through.

## Not a bug, verified rather than assumed

`patterns` returned zero configurations for the test chart, which looked like a
dead detector. Run against 200 random charts it fires normally: 162 stellia, 65
T-squares, 51 yods, 12 grand trines, 6 kites, 2 grand crosses. That chart simply
has no patterns.

## Diagnosis quality

Placidus above the polar circle failed with "Swiss Ephemeris could not calculate
houses for this input" — accurate, and useless. The registry already records
`defined_at_all_latitudes` per system, so the refusal now says which system,
why, at what latitude, that nothing was substituted, and which nine systems are
defined there. Naming alternatives without choosing one; the silent fallback
stays forbidden.

## Verification

```
ruff  clean
mypy  clean, 93 source files
pytest 466 passed, 674 subtests, 0 skipped
```

API layer checked end to end: unknown-time astrocartography → 400
`UNKNOWN_BIRTH_TIME`, polar Placidus → 400 `HOUSE_CALCULATION_UNAVAILABLE` with
the full diagnosis, polar whole-sign progressions → 200 declaring `whole_sign`.

## What this says about the remaining risk

Seven bugs, one cause: the cross product is where the defects live, not the
individual modules. Each module was tested and correct on its own axis. The
tests added here pin the invariants themselves — what must rotate, what must
not, what must refuse — so a new module cannot quietly reintroduce the shape.
