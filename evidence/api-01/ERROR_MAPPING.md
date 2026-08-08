# Error Mapping — API-01

| Engine error | HTTP status | API code | Client meaning | Retry? |
|---|---:|---|---|---|
| *(Pydantic request validation)* | 422 | `REQUEST_VALIDATION_ERROR` | Malformed/inconsistent request body | No |
| `AmbiguousLocalTimeError` | 409 | `AMBIGUOUS_LOCAL_TIME` | Local clock time occurred twice (DST fold); supply `fold` or correct time | No auto |
| `NonexistentLocalTimeError` | 400 | `NONEXISTENT_LOCAL_TIME` | Local clock time skipped by DST spring-forward | No |
| `InvalidCoordinateError` | 400 | `INVALID_COORDINATE` | Lat/lng outside physical range (engine) | No |
| `UnknownTimezoneError` | 400 | `UNKNOWN_TIMEZONE` | IANA timezone not recognized | No |
| `UnknownBirthTimeError` | 400 | `UNKNOWN_BIRTH_TIME` | Inconsistent unknown-time domain input | No |
| `InvalidCalculationProfileError` | 400 | `INVALID_CALCULATION_PROFILE` | Unsupported house system / profile | No |
| `HouseCalculationUnavailableError` | 400 | `HOUSE_CALCULATION_UNAVAILABLE` | Houses/angles cannot be computed (e.g. Placidus high latitude) — no silent fallback | No |
| `EphemerisOutOfRangeError` | 400 | `EPHEMERIS_OUT_OF_RANGE` | Date outside ephemeris coverage | No |
| `ProviderDependencyError` | 503 | `PROVIDER_DEPENDENCY_MISSING` | Swiss/provider dependency or data missing | Ops |
| `UnsupportedBodyError` | 500 | `UNSUPPORTED_BODY` | Provider missing a required body | Ops |
| *(unexpected Exception)* | 500 | `INTERNAL_ERROR` | Sanitized unexpected failure | Limited |
| *(Starlette HTTPException)* | *varies* | `HTTP_ERROR` | Generic HTTP error | Depends |

Envelope always:

```json
{
  "error": {
    "code": "AMBIGUOUS_LOCAL_TIME",
    "message": "...",
    "field": "local_time",
    "details": {}
  }
}
```

No stack traces, filesystem paths, or secrets in client payloads.
