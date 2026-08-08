# API Contract — API-01

**API version:** `v1`  
**Engine version:** `0.1.0`  
**Schema version:** `1.0.0`  
**Application:** `gbc_astro.api.app:app`

## Endpoints

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | none | Liveness; no natal calculation |
| POST | `/v1/charts/natal` | none | Calls `AstrologyEngine.natal(...)` |
| GET | `/openapi.json` | none | Live OpenAPI |
| GET | `/docs` | none | Swagger UI |

## Request — `POST /v1/charts/natal`

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `local_date` | string | yes | — | `YYYY-MM-DD` |
| `local_time` | string \| null | conditional | null | `HH:MM` or `HH:MM:SS`; required if `unknown_time=false` |
| `unknown_time` | boolean | no | false | Must be consistent with `local_time` |
| `timezone` | string | yes | — | IANA |
| `latitude` | number | yes | — | −90…90 (also enforced by engine) |
| `longitude` | number | yes | — | −180…180 |
| `altitude_m` | number \| null | no | null | Optional |
| `house_system` | enum \| null | no | null → profile default `placidus` | `placidus` \| `whole_sign` \| `equal` |
| `fold` | 0 \| 1 \| null | no | null | PEP 495 ambiguous fold only |

### Consistency rules

- `unknown_time=false` + `local_time=null` → **422** `REQUEST_VALIDATION_ERROR`
- `unknown_time=true` + `local_time` set → **422** (reject placeholder times)

### Engine mapping

```text
local_datetime = local_date                         # unknown_time
local_datetime = f"{local_date}T{local_time}:00"   # known (seconds padded)
→ AstrologyEngine.natal(local_datetime=..., timezone=..., latitude=..., longitude=...,
                        altitude_m=..., house_system=..., unknown_time=..., fold=...)
```

## Unknown-time semantics

Matches engine:

- angles / houses omitted
- `meta.houseSystem` null
- `derived.bigThree.rising` null
- warning `UNKNOWN_BIRTH_TIME`
- no fabricated known birth clock time from the API

## Response

Canonical `NatalChart.to_dict()` **directly** (not wrapped).

Provenance under `meta`: engine, engineVersion, ephemerisProvider, ephemerisDataVersion,
timezoneDataVersion, calculationProfile, houseSystem, aspectProfile, zodiac,
houseAlgorithmVersion. Top-level `schemaVersion`.

## Errors

Stable envelope:

```json
{ "error": { "code": "...", "message": "...", "field": "...", "details": {} } }
```

See `ERROR_MAPPING.md`.
