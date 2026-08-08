Status: PASS

Implemented:
- Swiss-backed ASC/MC/DSC/IC
- Whole Sign cusps derived from Ascendant sign
- Equal cusps derived from Ascendant degree
- Placidus delegated to Swiss Ephemeris
- House assignment with explicit exact-cusp policy
- High-latitude Placidus failure returns structured `HOUSE_CALCULATION_UNAVAILABLE`

Tests:
- Unit tests cover Whole Sign, Equal, wraparound assignment and cusp policy.
- Swiss golden test covers Placidus cusps and high-latitude explicit error.

Differential evidence:
- Provider-backed golden smoke only; full house-cusp differential corpus remains pending.

Known limitations:
- No silent fallback is implemented. Undefined Placidus cases error by design.

Files changed:
- `src/gbc_astro/houses/**`
- `tests/unit/test_houses.py`
- `tests/golden/test_swiss_natal.py`

