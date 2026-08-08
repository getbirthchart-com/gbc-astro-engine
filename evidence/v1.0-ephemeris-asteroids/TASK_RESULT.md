Status: PASS

v1.0 modules 8 and 9 of 11 — Ephemeris generator and optional asteroid support.

These complete the v1.0 module list in `05_RELEASE_PLAN.md`.

## v1.0 DoD

| Requirement | Where |
|---|---|
| Explicit methodology | `docs/EPHEMERIS_AND_ASTEROIDS.md` |
| Versioned profile | `EPHEMERIS_VERSION`, capability model |
| Test oracle | a generated row against a single-instant call |
| Unit tests | identifier parsing, range and step validation |
| Edge cases | unprovisioned asteroid, unknown body, oversized request |
| Tolerances | exact equality; a row either matches a direct call or does not |
| Provenance | provider, data version, range, step |
| Documented limitations | asteroid positions are not independently validated |

## Optional bodies

Ceres, Pallas, Juno, Vesta and both lunar apogees are carried by `seas_18.se1`,
the same file that carries Chiron. Numbered asteroids each need their own file.

Section 4 of the master requirements asks the provider layer to "expose
capability metadata rather than making unsupported bodies fail unpredictably",
and that requirement shapes the whole module. `available_optional_bodies()`
**probes** rather than guessing — the only reliable way to know whether a data
file is present is to ask for a position — and reports both availability and the
reason for absence.

Measured on this installation: all six standard bodies available;
`asteroid_433` and `asteroid_2060` unavailable with the reason naming the
missing file.

A test asserts Ceres has non-trivial ecliptic latitude, because a latitude of
exactly zero would be the signature of a stub rather than a calculation.

## Ephemeris generator

One claim, asserted directly: a generated row is exactly what a single-instant
call returns, compared field by field.

Rows are yielded lazily so memory stays bounded over any range, which is what
section 16 asks for. `generate_ephemeris` materialises them when a whole table
is wanted.

Oversized requests are refused rather than attempted. A step of seconds over a
range of centuries is almost always a mistake; a caller who means it raises
`max_rows` deliberately. Unsupported bodies are rejected before any calculation
begins rather than discovered part-way through a long run.

## Quality gates

ruff PASS · mypy strict PASS (92 files) · pytest PASS

## Not in these modules

Asteroid positions are not independently validated. Chiron is, against JPL
Horizons; extending `tools/fetch_chiron_horizons.py` to Ceres and the others is
open work and the method generalises directly. The generator emits positions
only: houses need a place as well as a time.

## v1.0 module status

All eleven modules are now implemented:

| Module | Status |
|---|---|
| Sidereal + ayanamsa | done |
| Extended house systems | done |
| Draconic | done |
| Harmonic | done |
| Secondary progressions | done |
| Solar arc | done |
| Advanced patterns | done |
| Relocation | done |
| Astrocartography primitives | done |
| Ephemeris generator | done |
| Optional asteroid support | done |
