Status: PASS

v1.0 module 4 of 11 — Secondary progressions and solar arc directions.

## v1.0 DoD, per module

| Requirement | Where |
|---|---|
| Explicit methodology | `docs/PROGRESSIONS.md`, module docstrings |
| Immutable versioned profile | `SECONDARY_PROGRESSION_V1`, `SOLAR_ARC_V1` |
| Reference / test oracle | exact defining properties |
| Unit tests | the progressed-instant mapping, in isolation |
| Golden tests | age 0 reproduces the natal chart |
| Edge cases | unknown birth time, naive datetime, dates before birth |
| Tolerances | exact where exact is possible; 0.95–1.05°/yr on the arc rate |
| Provenance | both instants, elapsed years, arc, full profile |

## Design

The progressed chart is an ordinary chart cast for the progressed instant at the
birthplace, produced by the engine's own natal path. Nothing astronomical is
reimplemented; only the day-for-a-year mapping is added, and that is arithmetic
on two datetimes.

Solar arc is then defined on top: the arc the progressed Sun travelled, applied
to every natal point. That makes it a rotation, so directed points keep their
natal aspects exactly and only contacts to the natal chart mean anything. The
chart carries `SOLAR_ARC_IS_A_ROTATION` saying so.

## An error this module's own tests caught

The profile documentation claimed that choosing the tropical year over the
Julian year "diverges by a day of progressed motion every 128 years of life --
around a degree of progressed Sun".

The test written to demonstrate that claim failed. Measured:

| Life span | Divergence | Progressed Sun |
|---|---:|---:|
| 50 years | 1.54 min | 3.8 arcsec |
| 100 years | 3.08 min | 7.7 arcsec |
| 128 years | 3.94 min | 9.8 arcsec |

A full day of divergence would take about **47,000 years of life**. The original
claim was wrong by four orders of magnitude.

Corrected in the profile, the module docstring and the documentation, and the
test now asserts the true magnitude: the choice changes the answer, but only by
minutes per century, so it is declared for reproducibility rather than because
it matters to a reading.

## Refusals

- An unknown birth time is refused for progressions. A day of error in the
  progressed instant is a year of symbolic time; there is no defensible hour to
  assume.
- Naive datetimes are refused rather than assumed UTC.
- Directed charts carry no houses and no speeds. A directed point is a symbolic
  construction, not a moving body, and directing the natal houses by the same
  arc would be a separate convention this profile does not define.

## Quality gates

ruff PASS · mypy strict PASS (86 files) · pytest PASS

## Not in this module

Naibod and quotidian angle methods, tertiary and minor progressions, converse
directions. Remaining v1.0 modules: relocation, patterns, astrocartography,
ephemeris generator, asteroid support.
