Status: PASS

Implemented:
- Tropical zodiac mapping
- Sign boundary handling for all 12 signs
- Degree-in-sign output

Tests:
- All 12 exact 30-degree boundaries
- 359.999 and 360.0 wraparound cases

Differential evidence:
- Not applicable for deterministic sign mapping.

Known limitations:
- Sidereal and ayanamsa profiles remain out of v0.1 scope.

Files changed:
- `src/gbc_astro/zodiac/tropical.py`
- `tests/unit/test_zodiac.py`

