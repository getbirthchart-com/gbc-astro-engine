Status: PASS

Phase 09 — v0.2 Relationship.

Implemented:
- `gbc_astro.relationship.synastry`: cross aspects, two-way house overlays,
  two-way angle interactions
- `gbc_astro.relationship.composite`: shortest-arc midpoint positions and angles
- `RelationshipProfile` (`relationship-western-v1`), versioned methodology
- Canonical JSON per `04_CANONICAL_JSON_CONTRACT.md` section 5
- Public API `AstrologyEngine.synastry(...)` / `.composite(...)`
- CLI `gbc synastry` / `gbc composite`
- HTTP `POST /v1/charts/synastry` / `POST /v1/charts/composite`

Schema versions:
- synastry `1.0.0`, composite `1.0.0`, engine `0.1.0`

Quality gates:
- ruff PASS
- mypy strict PASS (63 source files)
- pytest PASS (147 passed, 0 skipped, 29 subtests, with Swiss + JPL data present)

## Three decisions that refuse to invent numbers

**Cross-aspect phase is always `indeterminate`.** Applying and separating
describe two bodies converging along a shared timeline. Two natal charts are
frozen instants belonging to different people and share no such timeline.
Feeding the natal speeds into the v0.1 phase logic would have produced a
plausible-looking number with no physical meaning, so the field records that the
question does not apply, and a warning says so.

**No composite houses.** Deriving house cusps needs a reference time and place
that a composite chart does not have. `composite_house_method` is `None` in the
profile, nothing is emitted, `bodies.*.house` stays null, and a warning explains
why. The spec requires composite house methodology to be stated by profile, not
assumed.

**Composite angles are emitted but flagged.** They are the midpoints of each
chart's angles taken independently, which is the common convention and carries a
known defect: the resulting Ascendant and Midheaven need not hold the geometric
relationship real angles do, and the Descendant and IC are midpoints in their own
right rather than exact opposites. The defect is recorded in warnings rather than
hidden.

## Circular correctness

The defining failure mode of a composite chart is linear averaging: the mean of
359 and 1 is 180, the opposite side of the zodiac from the correct answer of 0.

Covered by `tests/unit/test_composite_midpoint.py`:
- explicit wrap cases including 359/1, 350/10, 300/60, 359.9/0.1
- Hypothesis properties: equidistance from both inputs, the midpoint lies on the
  shorter arc, output is always a valid longitude, order independence, and
  rotation equivariance (no privileged zero point)
- exact oppositions are flagged `ambiguous` rather than resolved silently: two
  points 180 degrees apart have two equally valid midpoints, and the discarded
  one is recorded as being 180 degrees from the chosen one

## Unknown birth time

A chart without a birth time has no houses and no angles. Overlays and angle
interactions against that chart are omitted with named warnings
(`SYNASTRY_HOUSE_OVERLAY_UNAVAILABLE`, `SYNASTRY_ANGLE_INTERACTIONS_PARTIAL`,
`COMPOSITE_ANGLES_UNAVAILABLE`). The other direction still runs. Nothing is
substituted.

## Refusals

Synastry and composite refuse two charts that differ in zodiac or schema
version, raising `INVALID_CALCULATION_PROFILE`. Cross aspects between a tropical
and a sidereal chart would be arithmetic on incompatible frames.

## Not in v0.2

- Davison relationship charts (architecture-ready, not implemented)
- composite house systems
- compatibility scoring: `03_CALCULATION_SPEC.md` forbids a percentage in the
  deterministic engine without a separately versioned scoring profile

## Contract change

`openapi/gbc-astro-v1.json` now publishes `/v1/charts/synastry` and
`/v1/charts/composite`. The frontend pins the contract by hash in
`.engine-version.json`, so it keeps building against v0.1.0 until it re-syncs
deliberately.
