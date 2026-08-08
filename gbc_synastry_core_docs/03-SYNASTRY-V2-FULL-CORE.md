# GetBirthChart Core — Synastry V2 / Full
## Composite Chart, Advanced Patterns, Complete Scoring, Ask/PDF-Ready Evidence

Repository: `gbc-astro-engine/`

Prerequisites:
- Synastry V1 PASS
- Synastry V1.5 PASS

## Mission

Complete the full relationship astrology core by adding Composite Chart, advanced relationship patterns, finalized scoring methodology, and structured evidence/grouping sufficient for future web features such as Ask about us and Couple PDF.

Python core does NOT implement chat UI or PDF rendering.

## Absolute rules

- Composite math belongs in Python core.
- Advanced pattern detection belongs in Python core.
- Scoring remains deterministic/versioned.
- LLM never generates astrology facts or scores.
- Existing V1/V1.5 outputs remain reproducible under their old profiles.
- No frontend logic in core.

## 1. Composite Chart

Implement dedicated `CompositeEngine`.

Input:
- canonical NatalChart A
- canonical NatalChart B
- composite profile

Output:
- `CompositeChart`

## 2. Composite midpoint methodology

Use documented circular midpoint math for ecliptic longitudes.

Critical test:
- midpoint of 359° and 1° must resolve around 0°, not 180°.

Do not use naive arithmetic mean.

## 3. Composite bodies

Minimum:
- Sun
- Moon
- Mercury
- Venus
- Mars
- Jupiter
- Saturn
- Uranus
- Neptune
- Pluto

Additional points only with explicit validated methodology.

## 4. Composite houses/angles

Treat this as a high-risk methodology area.

Do not casually midpoint house cusps/angles.

Choose and document a supported professional composite-house/angle method. If quality cannot be validated, support planetary Composite first and mark Composite houses/angles deferred.

Never fake unsupported angles/houses.

## 5. Composite aspects

Run canonical aspect detection over Composite positions with an explicit composite aspect profile if needed.

Return:
- aspects
- orbs
- patterns
- deterministic IDs
- provenance

## 6. Composite canonical model

Conceptually:

```json
{
  "schemaVersion": "composite-v1",
  "positions": [],
  "angles": [],
  "houses": [],
  "aspects": [],
  "patterns": [],
  "provenance": {}
}
```

## 7. Advanced relationship patterns

Implement only deterministic patterns with clear definitions.

Potential groups:
- repeated supportive themes
- repeated challenging themes
- mutual activation clusters
- personal-planet emphasis
- angular activation
- nodal emphasis
- Saturn emphasis
- Venus/Mars chemistry cluster
- Mercury communication cluster
- Moon emotional cluster

Do not force natal configuration labels onto relationship geometry unless definition is valid.

## 8. Cross-chart configurations

If implementing T-square-like/grand-trine-like cross-chart configurations, explicitly define:
- geometric requirements
- participating A/B bodies
- naming semantics
- evidence IDs

Otherwise defer them.

## 9. Finalized scoring methodology

Create `SYNASTRY_SCORING_PROFILE_FULL_V1` containing documented:
- dimensions
- base contribution rules
- orb scaling
- aspect weights
- body-pair weights
- angle/overlay weights
- point/ruler weights
- relationship-profile weights
- missing-data normalization
- confidence/coverage
- overall score formula if implemented
- deterministic rounding

Do not silently modify V1.5 scoring profile.

## 10. Calibration fixtures

Build curated fixtures for:
- highly supportive geometry
- highly challenging geometry
- mixed geometry
- sparse unknown-time geometry
- strong chemistry / weak stability
- strong communication / weak emotional
- strong Saturn emphasis
- nodal/angular emphasis if supported

These validate methodology consistency, not empirical prediction of relationship success.

## 11. Ask-about-us core support

Do NOT call an LLM.

Create a bounded evidence-context builder, conceptually:

```python
build_synastry_evidence_context(
    synastry_result,
    topic="communication",
)
```

Topics may include:
- overall
- emotional
- communication
- attraction
- conflict
- stability
- growth
- trust
- specific aspect
- specific overlay
- composite

Return:
- evidence IDs
- relevant contributions/scores
- directional facts
- profile/version metadata

This is the only core responsibility needed for future Ask about us.

## 12. Couple PDF core support

Do NOT render PDF.

Expose deterministic report structure suitable for frontend rendering/generation.

Suggested sections:
- relationship at a glance
- strongest connections
- main challenges
- emotional connection
- communication
- attraction
- trust/intimacy
- long-term stability
- growth
- directional dynamics
- house overlays
- Composite Chart
- technical reference

Create a report outline builder that returns section IDs, evidence IDs, score IDs, and priority. No natural-language report prose is required from core.

## 13. Canonical full result

Potential structure:

```text
SynastryResultV2
├── crossAspects
├── angleContacts
├── houseOverlays
├── pointContacts
├── rulerInteractions
├── directionalThemes
├── advancedPatterns
├── scores
├── strengths
├── challenges
├── evidenceBundles
├── reportOutline
├── composite
└── provenance
```

Avoid unnecessary payload duplication.

## 14. API/OpenAPI

Possible endpoints:
- `POST /v1/synastry`
- `POST /v1/synastry/composite`

Use repository conventions. Explicit schemas only; no `unknown` response bodies.

Frontend handoff must document stable IDs, scoring versions, evidence bundles, Composite support, and unknown-time limitations.

## 15. Required validation

Composite:
- circular midpoint boundaries
- deterministic fixtures
- independent reference comparisons
- aspect parity

Patterns:
- positive fixtures
- negative fixtures
- no duplicate IDs
- stable ordering

Full scoring:
- contribution decomposition
- normalization
- relationship-profile behavior
- range invariants

Evidence bundles:
- all IDs valid
- topic selections bounded
- no unsupported facts

Report outline:
- deterministic ordering
- no uncontrolled evidence duplication

## 16. Unknown-time

Document exact behavior for cross aspects, overlays, angles, directional data, Composite houses/angles, evidence bundles, and report outline.

Composite must not resurrect unsupported time-sensitive source data.

## 17. Performance

Benchmark:
- full Synastry V2
- Composite calculation
- advanced pattern detection
- evidence-context selection

Record p50/p95 where harness supports it.

## 18. Required docs

- `docs/SYNASTRY_FULL.md`
- `docs/COMPOSITE_CHART.md`
- `docs/SYNASTRY_SCORING_FULL.md`
- `docs/SYNASTRY_EVIDENCE_CONTEXT.md`
- `docs/SYNASTRY_REPORT_MODEL.md`

## 19. Evidence

Create `evidence/synastry-v2/`:
- TASK_RESULT.md
- TEST_OUTPUT.txt
- COMPOSITE_MODEL.md
- COMPOSITE_VALIDATION.md
- ADVANCED_PATTERNS.md
- FULL_SCORING_METHODOLOGY.md
- CALIBRATION_FIXTURES.md
- ASK_CONTEXT_MODEL.md
- COUPLE_REPORT_MODEL.md
- UNKNOWN_TIME_AUDIT.md
- API_PARITY.md
- OPENAPI_REPORT.md
- PERFORMANCE.md
- FRONTEND_HANDOFF.md

## 20. Quality gates

```bash
ruff check .
mypy src
pytest -q
```

Plus Composite fixtures, scoring invariants, evidence-context suite, report-outline suite, API parity, OpenAPI export, and all natal/transit/Synastry regressions.

## PASS criteria

PASS only if Composite works at documented scope, circular midpoint math is correct, advanced patterns are deterministic, full scoring is decomposable/versioned, Ask context/report models exist without UI or LLM, unknown-time is safe, OpenAPI is explicit, and regressions/evidence pass.

## Final response

### Synastry V2 / Full Result
PASS | FAIL | BLOCKED

### Composite Chart
### Composite houses/angles
Supported | Deferred
### Advanced patterns
### Full scoring
### Ask context support
### Couple report support
### Unknown-time behavior
### API/OpenAPI
### Validation
### Performance
### Quality gates
### Known limitations
### Next recommended phase
Synastry V2.5+
