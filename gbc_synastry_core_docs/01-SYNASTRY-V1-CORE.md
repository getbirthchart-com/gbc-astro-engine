# GetBirthChart Core — Synastry V1
## Cross Aspects, Angle Contacts, House Overlays, Strengths/Challenges, Basic Dimension Signals

Repository: `gbc-astro-engine/`

## Mission

Implement production-grade Synastry V1 using two canonical natal charts. Return deterministic relationship geometry plus basic ranked relationship signals. No UI. No LLM interpretation.

## Absolute rules

- Do not rewrite validated natal math unless a proven defect exists.
- Reuse canonical natal positions, aspects, houses, angles, points, provenance.
- Domain logic must not live in FastAPI routes.
- Do not generate relationship prose.
- Do not create an arbitrary overall percentage in V1.
- Unknown birth time must degrade safely.
- Results must be deterministic and versioned.

## 1. Audit existing core

Inspect natal models, aspect utilities, orb profiles, houses, angles, supported points, unknown-time behavior, provenance, API conventions, OpenAPI export, transit ranking/versioning patterns.

Create `evidence/synastry-v1/CURRENT_CORE_AUDIT.md` documenting reusable primitives, missing primitives, supported points, time-sensitive fields, and blockers.

## 2. Domain input

Preferred API:

```python
calculate_synastry(
    chart_a: NatalChart,
    chart_b: NatalChart,
    profile: SynastryProfile,
) -> SynastryResult
```

Prefer canonical charts over raw birth inputs when possible. FastAPI remains stateless and must not know frontend DB IDs.

## 3. Supported bodies

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

Stable natal points may be added only if already intentionally supported.

## 4. Cross-chart aspects

Support major cross aspects:
- conjunction
- opposition
- square
- trine
- sextile

Create `SYNASTRY_ASPECT_PROFILE_V1`. Do not reuse natal orbs blindly. Document final orb rules.

Each cross aspect includes:
- deterministic ID
- Person A body/point
- Person B body/point
- aspect
- exact angle
- angular separation
- orb
- applying/separating only if methodology is valid
- profile version

No prose.

## 5. Symmetry and deduplication

Preserve A/B identity while preventing duplicate geometric contacts. Stable sorting and tie-breakers are mandatory.

## 6. Angle contacts

When birth time permits, support contacts to:
- ASC
- DSC
- MC
- IC

Examples:
- A Venus conjunct B ASC
- A Saturn square B MC
- A ASC trine B Sun

Use explicit angle-orb policy if different. Unknown-time charts never expose unavailable angles.

## 7. House overlays

Calculate directional overlays:
- A planet/point in B house
- B planet/point in A house

Canonical overlay contains:
- source person
- source body/point
- target person
- target house
- source longitude where useful
- target house system/profile
- deterministic ID

Direction must never be flattened.

## 8. Asymmetric unknown-time behavior

If B time is unknown, A-in-B-house overlays are unavailable. If A houses are valid, B-in-A-house overlays may still be valid. Test all four known/unknown combinations.

## 9. Top strengths/challenges

Create `SYNASTRY_RANKING_PROFILE_V1`.

Classify source signals as:
- supportive
- challenging
- mixed/neutral

Ranking may consider:
- exactness/orb
- body pair relevance
- aspect family
- angle contacts
- house overlays

Return up to 5 top strengths and 5 top challenges, each referencing canonical evidence IDs.

Do not label challenging geometry as universally bad.

## 10. Basic dimension signals

Recommended dimensions:
- emotional
- communication
- attraction
- stability
- growth
- optional conflict

Create `SYNASTRY_DIMENSION_PROFILE_V1` mapping canonical signals into dimensions.

V1 returns signals, not a polished compatibility percentage.

Example conceptual output:

```json
{
  "dimension": "emotional",
  "supportiveSignal": 4.2,
  "challengingSignal": 2.1,
  "evidenceIds": []
}
```

Every signal is deterministic and evidence-backed.

## 11. Canonical result

Create explicit `SynastryResultV1` including:
- schemaVersion
- minimal references/provenance for chart A/B
- crossAspects
- angleContacts
- houseOverlays
- topStrengths
- topChallenges
- dimensions
- provenance

Avoid duplicating entire natal charts unless necessary.

## 12. Provenance

Include:
- engine version
- synastry schema version
- aspect profile
- ranking profile
- dimension profile
- natal calculation profile references
- house system as applicable
- ephemeris/provider provenance

## 13. FastAPI/OpenAPI

Add a clean endpoint such as `POST /v1/synastry` or repository-consistent equivalent.

Requirements:
- stable error envelope
- explicit response schema
- no `unknown` response body
- no frontend DB coupling
- additive/backward-compatible natal API

Possible errors only if needed:
- INVALID_CHART_A
- INVALID_CHART_B
- INCOMPATIBLE_CHART_SCHEMA
- SYNASTRY_CALCULATION_UNAVAILABLE

## 14. Required tests

Cross aspects:
- all five major aspects
- inside/outside orb
- exact boundary
- 0°/360° circular boundary
- duplicate prevention

Angles:
- known/known
- known/unknown
- unknown/known
- unknown/unknown

House overlays:
- A→B
- B→A
- asymmetric unknown-time
- cusp boundaries

Ranking:
- deterministic ordering
- stable tie-breakers
- orb behavior
- documented weights

Dimensions:
- evidence traceability
- deterministic signals
- no unknown evidence IDs

Regression:
- all natal tests remain green

## 15. Independent validation

Where feasible compare geometry to independent reputable astrology calculations for cross aspects, house overlays, and angle contacts. Validate geometry only, not copied interpretation.

## 16. Performance

Benchmark known/known, known/unknown, unknown/unknown. Record cross-pair counts and total/ranking latency.

## 17. Evidence

Create `evidence/synastry-v1/` with:
- TASK_RESULT.md
- TEST_OUTPUT.txt
- CURRENT_CORE_AUDIT.md
- CANONICAL_MODEL.md
- ASPECT_PROFILE.md
- ANGLE_CONTACTS.md
- HOUSE_OVERLAYS.md
- RANKING_PROFILE.md
- DIMENSION_PROFILE.md
- UNKNOWN_TIME_AUDIT.md
- VALIDATION.md
- API_PARITY.md
- OPENAPI_REPORT.md
- PERFORMANCE.md
- FRONTEND_HANDOFF.md

## 18. Quality gates

```bash
ruff check .
mypy src
pytest -q
```

Plus library smoke, HTTP smoke, OpenAPI export, all birth-time combinations, determinism, and natal regression.

## PASS criteria

PASS only if all V1 features, unknown-time degradation, deterministic IDs, explicit OpenAPI, library/API parity, regressions, quality gates, and evidence pass.

## Final response

Return:

### Synastry V1 Result
PASS | FAIL | BLOCKED

### Cross aspects
### Angle contacts
### House overlays
### Strengths/challenges
### Dimension signals
### Unknown-time behavior
### Canonical schema
### API/OpenAPI
### Validation
### Performance
### Quality gates
### Known limitations
### Next recommended phase
Synastry V1.5
