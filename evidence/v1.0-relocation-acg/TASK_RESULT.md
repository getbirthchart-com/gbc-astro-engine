Status: PASS

v1.0 modules 6 and 7 of 11 — Relocation and astrocartography primitives.

Delivered together because they are the same geometry from opposite directions:
relocation fixes the place and asks for the angles, astrocartography fixes the
angle and asks for the places.

## v1.0 DoD

| Requirement | Where |
|---|---|
| Explicit methodology | `docs/RELOCATION_AND_ACG.md`, module docstrings |
| Versioned profile | `RELOCATION_VERSION`, `ASTROCARTOGRAPHY_VERSION` |
| Test oracle | definitional self-consistency |
| Unit tests | closed-form meridian and horizon helpers |
| Edge cases | unknown time, bad coordinate, circumpolar latitude, degenerate houses |
| Tolerances | exact where exact is achievable |
| Provenance | method string, sidereal time, obliquity, chart instant |
| Documented limitations | parans and local space not implemented |

## Relocation

Body longitudes are geocentric and carried over untouched, so aspects are
unchanged **by construction** rather than by coincidence. Only angles, cusps and
house placements differ. Relocating to the birthplace reproduces the chart
exactly, and a separate test asserts the angles *do* move elsewhere so the
invariance tests cannot pass vacuously.

The Midheaven is asserted to depend only on geographic longitude, which is a
meridian property and a genuine check on the underlying house calculation.

Degenerate high-latitude house sequences carry the same
`HOUSE_SEQUENCE_DEGENERATE` warning introduced with the extended house systems.

## Astrocartography

Every line is closed form. The instant is fixed and only the observer moves, so
right ascension and declination are constants of the moment.

A body that is circumpolar at a latitude has no rising line there; that latitude
is omitted and counted, never clamped to the nearest one that works.

## The mistake worth recording

The first self-consistency check compared each body's *ecliptic longitude*
against the *Midheaven's longitude* at points on the computed line. Results:

| Body | Ecliptic latitude | Reported error |
|---|---:|---:|
| Sun | 0.00° | 0.23″ |
| Jupiter | 1.12° | 1740″ |
| Moon | 4.43° | 187170″ |

The error being proportional to ecliptic latitude is what identified the cause:
the check was mixing two different definitions of "on the angle".

**In mundo** means the body actually crosses the meridian or horizon — right
ascension equals local sidereal time, altitude equals zero. **Zodiacal** means
its longitude equals the angle's longitude. For a body off the ecliptic these
differ by up to 52 degrees of geographic longitude, which is the width of the
Atlantic.

Astrocartography has used the in-mundo convention since Jim Lewis, and that is
what the module computes. The check was wrong, not the lines. Re-run against the
correct definition the agreement is **0.000000 arcseconds** on all twelve lines.

The distinction is now stated in the module docstring and the documentation with
the measured magnitudes, because a reader who assumes the other convention would
be looking at the wrong ocean.

## Quality gates

ruff PASS · mypy strict PASS (90 files) · pytest PASS

## Not in these modules

Paran lines, local space lines, topocentric positions.

Remaining v1.0 modules: ephemeris generator, asteroid support.
