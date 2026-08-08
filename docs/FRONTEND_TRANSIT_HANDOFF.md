# Frontend Transit Handoff

Contract for consuming personalized transits. Companion to
[`FRONTEND_API_HANDOFF.md`](FRONTEND_API_HANDOFF.md); the natal contract is
unchanged.

## Endpoint

```
POST /v1/forecast/transits
Content-Type: application/json
```

Deviation from the original brief, which suggested `POST /v1/charts/transits`
"or a similarly clean endpoint": transits live under `/v1/forecast/` with the
event and return searches, because they are the same domain and the grouping
keeps the surface legible. The chart routes stay chart routes.

## Request

| Field | Type | Required | Notes |
|---|---|---|---|
| `natal` | object | yes | Identical shape to `POST /v1/charts/natal` |
| `target_instant` | string | yes | UTC ISO 8601, e.g. `2026-08-08T12:00:00Z` |
| `top` | integer \| null | no | Size of `topAspects`. Defaults to 3, max 50 |
| `include_natal_chart` | boolean | no | Embed the full natal chart |

```json
{
  "natal": {
    "local_date": "1992-11-03",
    "local_time": "14:35",
    "unknown_time": false,
    "timezone": "Asia/Ho_Chi_Minh",
    "latitude": 21.0285,
    "longitude": 105.8542
  },
  "target_instant": "2026-08-08T12:00:00Z",
  "top": 3
}
```

Send birth input, not calculated positions. The engine is stateless: it holds no
chart IDs and queries no database, so it recalculates natal facts from the same
validated path every time.

Send a UTC instant for `target_instant`. Unlike a birth time it carries no
timezone or DST ambiguity — it is a moment, not a local clock reading.

## Response

Top-level keys:

```
schemaVersion  meta  targetInstant  transitBodies
transitToNatalAspects  topAspects  transitHousePlacements  warnings
```

`schemaVersion` is `1.1.0`.

### topAspects and transitToNatalAspects

`topAspects` is the head of `transitToNatalAspects`, which is already ranked.
The full list is always returned: the ranked subset is a convenience, not a
filter, so nothing is discarded.

```json
{
  "id": "transit.uranus.opposition.natal.mercury",
  "transitBody": "uranus",
  "natalTarget": "mercury",
  "natalTargetKind": "body",
  "type": "opposition",
  "exactAngle": 180.0,
  "actualAngle": 179.26,
  "orb": 0.74,
  "phase": "separating",
  "score": 0.4082,
  "rank": 1
}
```

`natalTargetKind` is `body` or `angle`. `phase` is one of `applying`,
`separating`, `exact`, `indeterminate`.

`natalBody` is present as a deprecated alias of `natalTarget`; prefer
`natalTarget`, which is accurate when the target is an angle.

### Evidence IDs

```
transit.<transiting body>.<aspect>.natal.<target>
```

Derived only from what the contact is, so it is stable across runs and engine
versions. Safe to key interpretation copy, caching or user state on. It carries
no prose and no numbers, and it is unique within a response.

### transitBodies

Keyed by body id, each carrying `longitude`, `sign`, `degreeInSign`, `latitude`,
`speedLongitude`, `retrograde`, `distance`, `house`. Do not derive the sign
yourself.

### Provenance

`meta` carries `engine`, `engineVersion`, `ephemerisProvider`,
`ephemerisDataVersion`, `calculationProfile`, `transitAspectProfile`,
`transitAspectProfileVersion`, `rankingProfile`, `rankingProfileVersion`,
`rankingProfileDetail`, `zodiac`, `natalHouseSystem`, `phaseBasis`, and
`natalAngleTargetsIncluded`.

`rankingProfileDetail` contains every weight, so a methodology page can display
the reasoning rather than assert it.

## Unknown birth time

When the natal chart has `unknown_time: true`:

- `meta.natalAngleTargetsIncluded` is `false`; no Ascendant or Midheaven targets
- `transitHousePlacements` is `[]`
- warning `TRANSIT_HOUSE_PLACEMENT_UNAVAILABLE` is present
- planet-to-planet aspects and ranking work normally

Check `natalAngleTargetsIncluded` rather than inferring from an empty list.

## Errors

Same envelope as every other route. Switch on `error.code`, never on message
text.

| code | HTTP | when |
|---|---:|---|
| `REQUEST_VALIDATION_ERROR` | 422 | malformed body, unknown field, `top` out of range |
| `INVALID_CALCULATION_PROFILE` | 400 | `target_instant` is not a valid ISO 8601 instant |
| `AMBIGUOUS_LOCAL_TIME` | 409 | the natal birth time falls in a DST fold |
| `NONEXISTENT_LOCAL_TIME` | 400 | the natal birth time does not exist |
| `UNKNOWN_TIMEZONE` / `INVALID_COORDINATE` | 400 | bad natal input |
| `PROVIDER_DEPENDENCY_MISSING` | 503 | ephemeris data not provisioned |

No transit-specific error codes were added: nothing about transits fails in a
way the existing model could not already express.

## OpenAPI

```
openapi/gbc-astro-v1.json
```

Generate TypeScript from the checked-in snapshot, not from a live fetch. The
transit routes are additive — every v0.1 and v0.2 path and schema is byte
identical, verified in CI.

Re-pin with `npm run contract:sync -- --tag <tag>` then `npm run api:generate`.

## What the frontend must not do

Interpretation only. Do not re-rank, re-filter by orb, or compute aspects
client-side: the engine owns transit facts, and a second implementation would
drift from the one that is tested.
