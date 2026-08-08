Status: PASS

Implemented:
- Aspect profile model
- Major aspect classification
- Orb calculation
- Applying/separating/exact/indeterminate phase derivation from relative motion

Tests:
- Aspect classification, outside-orb, exact and missing-speed phase tests passed.

Differential evidence:
- Swiss golden sample emits configured major aspects; large aspect parity corpus remains pending.

Known limitations:
- Minor aspects are model-ready but not enabled in the default v0.1 profile.

Files changed:
- `src/gbc_astro/aspects/**`
- `src/gbc_astro/profiles/**`
- `tests/unit/test_aspects.py`

