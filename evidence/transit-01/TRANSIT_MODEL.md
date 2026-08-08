# Transit Model

Schema version `1.1.0` (was `1.0.0` in v0.3; this release adds ranking, IDs,
angle targets and the tighter orb profile).

## TransitChart

| Field | Notes |
|---|---|
| `schemaVersion` | `1.1.0` |
| `meta` | provenance, both profile versions, full ranking weights |
| `targetInstant` | UTC ISO 8601 |
| `transitBodies` | ten planets, each with longitude, sign, degree, retrograde, speed |
| `transitToNatalAspects` | all detected contacts, already ranked |
| `topAspects` | head of the above, default 3 |
| `transitHousePlacements` | transiting bodies in natal houses; empty without a birth time |
| `warnings` | structured, never prose |

`topAspects` is a convenience, not a filter: the full list is always returned,
per section 17.

## TransitAspect

| Field | Notes |
|---|---|
| `id` | `transit.<body>.<aspect>.natal.<target>` |
| `transitBody` | transiting body id |
| `natalTarget` | natal body or angle id |
| `natalTargetKind` | `body` or `angle` |
| `natalBody` | deprecated alias of `natalTarget`, kept for compatibility |
| `type` | aspect id |
| `exactAngle`, `actualAngle`, `orb` | degrees |
| `phase` | `applying`, `separating`, `exact`, `indeterminate` |
| `score`, `rank` | from `transit-ranking-v1` |

The identifier is derived only from what the contact is, so it is stable across
runs and engine versions and carries neither prose nor numbers.

## Design choices

Positions are calculated by the engine and returned with sign and degree
already resolved, so no caller derives astrology facts.

The aspect list is ranked in place rather than duplicated, and `topAspects`
shares the same objects, so `topAspects[i].id == transitToNatalAspects[i].id`.

`natalBody` was kept alongside `natalTarget` so the v0.3 field does not vanish
from a schema that frontends may already read.
