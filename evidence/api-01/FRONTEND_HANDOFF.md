# Frontend Handoff Summary — API-01

Canonical document: [`docs/FRONTEND_API_HANDOFF.md`](../../docs/FRONTEND_API_HANDOFF.md)

## Quick facts for getbirthchart-web Phase 04

- Base URL (local): `http://127.0.0.1:8000`
- Natal: `POST /v1/charts/natal`
- Response: canonical chart JSON **directly**
- OpenAPI snapshot: `openapi/gbc-astro-v1.json`
- Map frontend `birthDate`/`birthTime`/`unknownBirthTime` → `local_date`/`local_time`/`unknown_time`
- Do not convert local birth time to UTC in the browser
- Switch on `error.code` (preserve engine names: `INVALID_COORDINATE`, `UNKNOWN_TIMEZONE`, …)

## Known-time

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

## Unknown-time

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
