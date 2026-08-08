# GetBirthChart Core — Synastry V2.5+
## Relationship Transits, Composite Transits, Progressed Synastry, Progressed Composite

Repository: `gbc-astro-engine/`

Prerequisite: Synastry V2 / Full = PASS.

## Mission

Add the relationship timing layer answering:
- What is active between these people now?
- What transits are activating important relationship factors?
- How is the relationship evolving through progressions?

No UI, notifications, subscription logic, or LLM calculations.

## Absolute rules

- Reuse validated transit engine.
- Reuse validated Synastry and Composite results.
- Progression methodology must be explicit/versioned.
- Keep natal transits, relationship transits, Composite transits, progressed synastry, and progressed Composite semantically distinct.
- Target datetime is always explicit.
- Unknown-time degradation remains mandatory.

## 1. Current relationship transits

Relationship timing should build on valid natal transits plus activation of important Synastry evidence.

Potential categories:
- Transit → Person A natal
- Transit → Person B natal
- Transit activation of a key cross-chart contact

Example:

Existing relationship evidence:
`A Venus trine B Moon`

Current transit:
`Transit Jupiter conjunct A Venus`

The relationship layer may mark the key Synastry evidence as currently activated. This is deterministic evidence graphing, not prose inference.

## 2. RelationshipTransitResult

Conceptual:

```json
{
  "schemaVersion": "relationship-transit-v1",
  "targetDatetime": "...",
  "activeNatalTransitsA": [],
  "activeNatalTransitsB": [],
  "activatedSynastryEvidence": [],
  "topRelationshipActivations": [],
  "provenance": {}
}
```

## 3. Relationship transit ranking

Create `RELATIONSHIP_TRANSIT_RANKING_V1`.

Potential factors:
- transit orb
- transiting planet
- importance of activated natal/Synastry evidence
- relationship profile relevance
- applying/separating where supported

No LLM ranking.

## 4. Composite transits

Calculate current transiting planets against Composite Chart positions.

Support:
- major aspects to Composite bodies
- Composite angles only if core supports validated Composite angles
- orb
- applying/separating where supported
- deterministic IDs
- backend ranking

Canonical output: `CompositeTransitResult`.

IDs must be unambiguous, e.g.:
`composite_transit.saturn.square.composite.sun`

## 5. Progression methodology

Start with one explicit technique: secondary progressions.

Create `PROGRESSION_PROFILE_V1` documenting:
- day-for-year convention
- time-scale treatment
- target age/date mapping
- supported bodies
- progressed Moon handling
- houses/angles handling
- unknown-time behavior

Do not mix multiple progression schools under one profile.

## 6. Progressed positions

Calculate progressed charts for A and B, then support distinct categories:
- progressed A → natal B
- natal A → progressed B
- progressed A → progressed B

Never merge these without type labels.

## 7. ProgressedSynastryResult

Conceptual:

```json
{
  "schemaVersion": "progressed-synastry-v1",
  "targetDatetime": "...",
  "progressedChartA": {},
  "progressedChartB": {},
  "progressedAToNatalB": [],
  "natalAToProgressedB": [],
  "progressedAToProgressedB": [],
  "topSignals": [],
  "provenance": {}
}
```

Use compact representations where sensible.

## 8. Progressed Composite

Implement only after secondary progression primitives are independently validated.

Choose one documented methodology:
- progress each natal chart then recompute Composite
or
- progress existing Composite

Do not silently mix methodologies.

Canonical output: `ProgressedCompositeResult`.

## 9. Progressed Composite aspects

Return:
- progressed Composite positions
- internal progressed Composite aspects
- optional additional layers only if explicitly included in later profiles

Keep timing scopes separate.

## 10. Unknown-time behavior

Do not invent progressed angles/houses when source birth time is unknown. Omit time-sensitive results that cannot be validated.

## 11. Provenance

Every result includes:
- target datetime
- source chart versions/hashes where appropriate
- transit/profile versions
- progression profile
- ephemeris provider/version
- ranking/scoring versions

## 12. API design

Possible endpoints:
- `POST /v1/synastry/transits`
- `POST /v1/synastry/composite/transits`
- `POST /v1/synastry/progressed`
- `POST /v1/synastry/composite/progressed`

Prefer multiple explicit endpoints over an unreadable monolith.

## 13. Frontend cache handoff

Core remains stateless, but document deterministic cache identity using source chart hashes, target time bucket/date, and profile versions.

## 14. Required validation — relationship transits

Test:
- transit-to-A
- transit-to-B
- activation of existing Synastry evidence
- target datetime changes
- deterministic ranking

## 15. Required validation — Composite transits

Test:
- exact aspects
- orb boundaries
- applying/separating where supported
- deterministic IDs
- independent fixture comparisons

## 16. Required validation — secondary progressions

This is high sensitivity.

Required:
- independent reference fixtures
- multiple ages/dates
- fast progressed Moon checks
- circular 0°/360° boundaries
- calendar/leap handling where relevant
- deterministic target-date conversion
- unknown-time fixtures

Do not mark PASS without strong external numerical validation.

## 17. Required validation — progressed Synastry

Fixtures for:
- progressed A → natal B
- natal A → progressed B
- progressed A → progressed B

Verify classification, orb, IDs, and ordering.

## 18. Required validation — progressed Composite

Compare against independently calculated reference cases where possible. If reputable tools disagree due to methodology, document the chosen method and differences.

## 19. Performance

Benchmark:
- relationship transits
- Composite transits
- progressed Synastry
- progressed Composite

Must remain suitable for interactive web workloads.

## 20. Required docs

- `docs/RELATIONSHIP_TRANSITS.md`
- `docs/COMPOSITE_TRANSITS.md`
- `docs/SECONDARY_PROGRESSIONS.md`
- `docs/PROGRESSED_SYNASTRY.md`
- `docs/PROGRESSED_COMPOSITE.md`

## 21. Evidence

Create `evidence/synastry-v2.5/`:
- TASK_RESULT.md
- TEST_OUTPUT.txt
- RELATIONSHIP_TRANSIT_MODEL.md
- RELATIONSHIP_TRANSIT_RANKING.md
- COMPOSITE_TRANSIT_MODEL.md
- PROGRESSION_PROFILE.md
- PROGRESSED_SYNASTRY_MODEL.md
- PROGRESSED_COMPOSITE_MODEL.md
- UNKNOWN_TIME_AUDIT.md
- NUMERICAL_VALIDATION.md
- API_PARITY.md
- OPENAPI_REPORT.md
- PERFORMANCE.md
- FRONTEND_HANDOFF.md

## 22. Quality gates

```bash
ruff check .
mypy src
pytest -q
```

Plus relationship-transit smoke, Composite-transit smoke, progression numerical suite, progressed-Synastry smoke, progressed-Composite smoke, OpenAPI export, library/API parity, and all natal/transit/Synastry regressions.

## PASS criteria

PASS only if relationship transits, Synastry activation, Composite transits, secondary progressions, progressed Synastry, and progressed Composite work at documented scope; numerical validation is strong; unknown-time is safe; OpenAPI is explicit; no LLM calculations exist; and all regressions/evidence pass.

If progression numerics cannot be independently validated: `BLOCKED`.

## Final response

### Synastry V2.5+ Result
PASS | FAIL | BLOCKED

### Relationship transits
### Synastry activation model
### Composite transits
### Progression methodology
### Progressed synastry
### Progressed composite
### Unknown-time behavior
### Numerical validation
### API/OpenAPI
### Performance
### Quality gates
### Known limitations
### Next recommended action
Frontend/UI integration can begin after the required core milestone is PASS.
