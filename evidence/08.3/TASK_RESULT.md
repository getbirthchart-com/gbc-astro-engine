Status: PASS

Implemented:
- Versioned `ToleranceProfile`
- Natal chart numerical comparison helper
- Mismatch report with path, expected, actual, delta, tolerance and classification
- Max-delta aggregation by compared path

Tests:
- Matching chart comparison passes.
- Deliberate body-longitude mismatch is reported as `unresolved`.
- Full lint/type/test suite passed.

Differential evidence:
- Harness is implemented and tested with fixture charts.
- Actual 10K external-reference differential corpus remains pending.

Known limitations:
- Mismatch classifications are initialized as `unresolved`; automated classification rules for timezone/provider/house-convention buckets are not implemented yet.

Files changed:
- `src/gbc_astro/validation/**`
- `tests/differential/test_compare_natal.py`

