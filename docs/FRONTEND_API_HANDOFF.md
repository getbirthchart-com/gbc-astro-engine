# Frontend API Handoff — gbc-astro HTTP

Contract for `getbirthchart-web` Phase 04 integration.

## API URL convention

Local:

```text
http://127.0.0.1:8000
```

Production URL is deployment-dependent. Configure frontend:

```env
ASTROLOGY_API_URL=http://127.0.0.1:8000
ASTROLOGY_API_VERSION=v1
```

Preferred call path:

```text
Browser → Next.js Server Action → gbc-astro HTTP API
```

Do not call this API from browser JS with wildcard CORS. CORS is disabled unless
`GBC_API_CORS_ORIGINS` is set explicitly.

## Endpoint

```text
POST /v1/charts/natal
Content-Type: application/json
```

Also:

- `GET /health`
- `GET /openapi.json`
- `GET /docs`

## Final request schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `local_date` | string | yes | `YYYY-MM-DD` local civil date |
| `local_time` | string \| null | conditional | `HH:MM` or `HH:MM:SS`; required unless `unknown_time` |
| `unknown_time` | boolean | no (default false) | Must be consistent with `local_time` |
| `timezone` | string | yes | IANA ID |
| `latitude` | number | yes | −90…90 |
| `longitude` | number | yes | −180…180 |
| `altitude_m` | number \| null | no | Optional |
| `house_system` | string \| null | no | `placidus` \| `whole_sign` \| `equal` |
| `fold` | 0 \| 1 \| null | no | Only to resolve ambiguous DST folds |

### Mapping from Phase 03 frontend payload

| Frontend (`BirthChartInput`) | API |
|---|---|
| `birthDate` | `local_date` |
| `birthTime` | `local_time` |
| `unknownBirthTime` | `unknown_time` |
| `timezone` | `timezone` |
| `latitude` | `latitude` |
| `longitude` | `longitude` |
| `placeLabel` | **not sent** (display only) |

## Known-time example

```json
{
  "local_date": "1996-06-14",
  "local_time": "04:12",
  "unknown_time": false,
  "timezone": "Europe/Lisbon",
  "latitude": 38.7223,
  "longitude": -9.1393
}
```

## Unknown-time example

```json
{
  "local_date": "1996-06-14",
  "local_time": null,
  "unknown_time": true,
  "timezone": "Europe/Lisbon",
  "latitude": 38.7223,
  "longitude": -9.1393
}
```

## Canonical response

Endpoint returns the engine canonical chart **directly**:

```json
{
  "schemaVersion": "1.0.0",
  "meta": { "...provenance..." },
  "subject": { "...": "..." },
  "angles": {},
  "bodies": {},
  "houses": [],
  "aspects": [],
  "derived": {},
  "warnings": []
}
```

Not:

```json
{ "chart": { "...": "..." } }
```

Provenance lives under `meta` (`engineVersion`, `ephemerisProvider`,
`ephemerisDataVersion`, `timezoneDataVersion`, `calculationProfile`,
`houseSystem`, `aspectProfile`, `zodiac`, `houseAlgorithmVersion`).

`schemaVersion` is top-level (and mirrored in chart construction).

## Stable errors

Envelope:

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

| code | typical HTTP |
|---|---:|
| `REQUEST_VALIDATION_ERROR` | 422 |
| `AMBIGUOUS_LOCAL_TIME` | 409 |
| `NONEXISTENT_LOCAL_TIME` | 400 |
| `UNKNOWN_TIMEZONE` | 400 |
| `INVALID_COORDINATE` | 400 |
| `UNKNOWN_BIRTH_TIME` | 400 |
| `INVALID_CALCULATION_PROFILE` | 400 |
| `HOUSE_CALCULATION_UNAVAILABLE` | 400 |
| `EPHEMERIS_OUT_OF_RANGE` | 400 |
| `PROVIDER_DEPENDENCY_MISSING` | 503 |
| `UNSUPPORTED_BODY` | 500 |
| `INTERNAL_ERROR` | 500 |

Switch on `error.code`, not English `message` text.

## OpenAPI snapshot

```text
openapi/gbc-astro-v1.json
```

Regenerate:

```bash
python -m gbc_astro.api.export_openapi
```

Frontend should generate TypeScript from this checked-in file (not a live fetch at build time).

## Unknown-time semantics

When `unknown_time=true`:

- Engine omits angles / houses / house assignments
- `meta.houseSystem` is null
- `derived.bigThree.rising` is null
- Warning `UNKNOWN_BIRTH_TIME` is present
- Body positions still returned using the engine’s documented local-date-start policy
- API never substitutes `12:00` / `00:00` as a known birth time

## Timezone semantics

Send local date + local clock + IANA timezone. Frontend must **not** convert to
UTC or resolve historical DST. Ambiguous / nonexistent local times return structured
errors; do not auto-pick a fold unless the user explicitly supplies `fold`.
