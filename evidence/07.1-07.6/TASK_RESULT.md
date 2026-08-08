Status: PASS

Implemented:
- Big Three
- Moon phase
- Element counts
- Modality counts
- Polarity counts
- Hemisphere counts
- Quadrant counts

Tests:
- Derived primitive unit tests passed.
- Engine integration verifies unknown-time omits rising.

Differential evidence:
- Not applicable beyond deterministic rule tests; these are profile-driven classifications.

Known limitations:
- Dominance, angularity and pattern detection remain out of current release boundary.

Files changed:
- `src/gbc_astro/derived/**`
- `src/gbc_astro/engine.py`
- `tests/unit/test_derived.py`
- `tests/integration/test_engine_natal.py`

