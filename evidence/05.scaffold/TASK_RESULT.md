Status: BLOCKED

Implemented:
- `AstrologyEngine.natal()`
- exact-time and unknown-time orchestration
- canonical JSON result assembly
- aspect calculation
- deterministic derived natal primitives
- explicit unknown-time warning and omission of angles/houses/house assignments
- Swiss-backed house calculator wrapper for Whole Sign, Equal and Placidus

Tests:
- Exact-time engine path passes with fixture provider and fixture house calculator.
- Unknown-time mode omits time-sensitive fields.
- Full unittest suite passed.

Differential evidence:
- Not run. v0.1 parity requires real Swiss/reference provider setup and a differential corpus.

Known limitations:
- Full natal-core DoD remains blocked until real ephemeris and Placidus calculations are validated with `pyswisseph` and differential tests.
- The default CLI cannot emit a real chart in this local environment because `pyswisseph` is not installed.

Files changed:
- `src/gbc_astro/engine.py`
- `src/gbc_astro/houses/**`
- `src/gbc_astro/aspects/**`
- `src/gbc_astro/derived/**`
- `tests/integration/test_engine_natal.py`

