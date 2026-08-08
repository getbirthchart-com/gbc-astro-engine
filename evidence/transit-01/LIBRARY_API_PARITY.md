# Library / API Parity

Section 31. The same input through the library and through HTTP must produce the
same document after legitimate serialisation only.

## Method

Call `AstrologyEngine.transits(...)` directly and `POST /v1/forecast/transits`
with equivalent input, then compare the full dictionaries.

## Result

```
known-time     identical: True  (aspects 12, top 3)
unknown-time   identical: True  (aspects 14, top 3)
top=1          identical: True  (aspects 12, top 1)
```

PASS. Covered continuously by
`tests/api/test_forecast_api.py::ForecastRouteTests::test_http_matches_the_library_result`.

The HTTP layer holds no calculation. The route resolves the instant, calls
`engine.natal(...)` then `engine.transits(...)`, and serialises. Section 10 is
satisfied: nothing astrological lives in a FastAPI route.
