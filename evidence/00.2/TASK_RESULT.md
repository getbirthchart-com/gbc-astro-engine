Status: PASS

Implemented:
- Typed structured errors with stable API codes
- Chart input validation
- Canonical chart, position, aspect, warning and metadata models
- JSON serialization through `NatalChart.to_dict()` and `NatalChart.to_json()`

Tests:
- Validation and serialization are covered through unit/integration tests.
- Full unittest suite passed.

Differential evidence:
- Not applicable for core models/errors.

Known limitations:
- Pydantic is intentionally not required in the core package; stdlib dataclasses are used to keep the calculation library dependency-light.

Files changed:
- `src/gbc_astro/errors.py`
- `src/gbc_astro/models/**`
- `tests/integration/test_engine_natal.py`

