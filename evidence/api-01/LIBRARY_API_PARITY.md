# Library / API Parity — API-01

Strategy: inject the same `AstrologyEngine(provider=FixtureProvider(), house_calculator=FixtureHouseCalculator())`
into HTTP via FastAPI dependency override, then compare `response.json()` to
`engine.natal(...).to_dict()` for identical inputs.

## Results

| Case | Status |
|---|---|
| Known-time Lisbon `1996-06-14` `04:12` `Europe/Lisbon` | **PASS** (exact dict equality) |
| Unknown-time Lisbon `1996-06-14` | **PASS** (exact dict equality; angles/houses empty; warning `UNKNOWN_BIRTH_TIME`) |
| DST `AMBIGUOUS_LOCAL_TIME` (NY 2024-11-03 01:30) | **PASS** (HTTP 409, same domain code) |
| DST `NONEXISTENT_LOCAL_TIME` (NY 2024-03-10 02:30) | **PASS** (HTTP 400, same domain code) |
| House unavailable / no silent fallback | **PASS** (HTTP 400 `HOUSE_CALCULATION_UNAVAILABLE`) |

Tests: `tests/api/test_natal_api.py`

## Production HTTP smoke (Swiss)

With `GBC_SWISS_EPHE_PATH=/private/tmp/gbc_swisseph` and live uvicorn:

- Known-time Lisbon returned canonical chart (`schemaVersion` 1.0.0, houses present)
- Unknown-time Lisbon returned empty angles/houses, `UNKNOWN_BIRTH_TIME`, rising null

The adapter does not alter chart facts; it only validates/translates HTTP fields and serializes `NatalChart.to_dict()`.
