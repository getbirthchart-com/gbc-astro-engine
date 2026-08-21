# GetBirthChart Astrology HTTP API

Thin FastAPI adapter over the existing `AstrologyEngine`. No astrology math,
geocoding, persistence, or interpretation lives in this layer.

## Installation

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[api]" --config-settings editable_mode=compat
```

For development (tests + HTTP client):

```bash
python -m pip install -e ".[dev,api]" --config-settings editable_mode=compat
```

Library-only consumers do **not** need the `api` extra.

Optional ephemeris data:

```bash
export GBC_SWISS_EPHE_PATH=/path/to/swisseph
```

## Start server

```bash
uvicorn gbc_astro.api.app:app --host 127.0.0.1 --port 8000
```

Optional explicit CORS (off by default — Next.js server should call this API):

```bash
export GBC_API_CORS_ORIGINS=http://127.0.0.1:3000
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + engine/API versions (no natal calc) |
| POST | `/v1/charts/natal` | Calculate natal chart via `AstrologyEngine.natal` |
| GET | `/docs` | Swagger UI |
| GET | `/openapi.json` | Live OpenAPI schema |

## Known-time request

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

Maps to:

```python
engine.natal(
    local_datetime="1996-06-14T04:12:00",
    timezone="Europe/Lisbon",
    latitude=38.7223,
    longitude=-9.1393,
    unknown_time=False,
)
```

## Unknown-time request

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

Rules:

- `unknown_time=true` requires `local_time=null` (rejected otherwise)
- `unknown_time=false` requires `local_time`
- No noon/midnight placeholder is invented by the API

## Optional fields

| Field | Notes |
|---|---|
| `altitude_m` | Optional meters |
| `house_system` | `placidus` \| `whole_sign` \| `equal` (default: profile placidus) |
| `fold` | `0` \| `1` for PEP 495 ambiguous local times only |

## Response

`POST /v1/charts/natal` returns the **canonical** `NatalChart.to_dict()` object
directly (not wrapped in `{ "chart": ... }`).

## Error envelope

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

Stable domain codes come from `gbc_astro.errors` (e.g. `AMBIGUOUS_LOCAL_TIME`,
`NONEXISTENT_LOCAL_TIME`, `UNKNOWN_TIMEZONE`, `INVALID_COORDINATE`,
`HOUSE_CALCULATION_UNAVAILABLE`, `PROVIDER_DEPENDENCY_MISSING`).

## OpenAPI snapshot

```bash
python -m gbc_astro.api.export_openapi
```

Writes `openapi/gbc-astro-v1.json` for frontend type generation without a live server.
