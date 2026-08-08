Status: PASS

Implemented:
- Provider body-position normalization into canonical `BodyPosition`
- Retrograde derivation from longitude speed
- Tropical zodiac mapping isolated from provider output

Tests:
- Provider normalization unit tests cover longitude wrap and unknown speed.
- Full pytest suite passed.

Differential evidence:
- Covered indirectly by Swiss golden sample; large differential corpus remains pending.

Known limitations:
- No tolerance profile or mismatch classifier yet.

Files changed:
- `src/gbc_astro/providers/normalization.py`
- `tests/unit/test_provider_normalization.py`

