# GetBirthChart Core — Synastry V1.5
## Deterministic Scoring, Relationship Profiles, Richer Points/Rulers, Directional Support

Repository: `gbc-astro-engine/`

Prerequisite: Synastry V1 = PASS.

## Mission

Turn V1 geometry/basic signals into a deterministic, versioned, explainable compatibility model suitable for future scoring and grounded relationship interpretation. No UI and no LLM scoring.

## Absolute rules

- V1 geometry remains authoritative.
- Every score must be deterministic and decomposable.
- Relationship type changes relevance/weighting, not astronomy facts.
- Directional meaning stays explicit.
- No score may depend on LLM output.
- V1 API behavior must remain reproducible under V1 profiles.

## 1. Deterministic scoring

Create `SYNASTRY_SCORING_PROFILE_V1`.

Recommended dimensions:
- emotional connection
- communication
- attraction/chemistry
- intimacy/trust
- stability
- conflict/friction
- growth
- values/lifestyle

Each dimension returns:
- score or normalized signal
- supportive contribution
- challenging contribution
- evidence IDs
- coverage/confidence where useful

## 2. Score range and semantics

Use a documented range such as 0–100, or internal normalized values with deterministic conversion.

Avoid fake precision such as 82.31%. If exposed as 0–100, use display-safe integer/rounded scoring plus full underlying contribution audit.

## 3. Contribution model

Every contribution should record:
- evidence ID
- dimension
- base weight
- orb modifier
- relationship-profile modifier
- direction modifier where relevant
- final contribution
- supportive/challenging/mixed class

The score must be reconstructable from these contributions.

## 4. Overall score

Implement only if all of the following are defensible:
- dimension weighting documented
- missing-data behavior defined
- unknown-time coverage normalized
- relationship-profile weighting defined
- score does not reward charts merely for having more available data

Otherwise explicitly defer the overall score while still completing dimension scores.

## 5. Relationship-type profiles

Create stable versioned profiles:
- romantic-v1
- friendship-v1
- family-v1
- work-v1

Examples of weighting intent:
- romantic: attraction/intimacy higher
- friendship: communication/growth/emotional higher
- work: communication/stability/conflict/goal dynamics higher
- family: emotional/stability/conflict/pattern persistence higher

Document all actual weights used.

## 6. Richer supported points

If natal v1.0 officially supports them, integrate appropriate contacts for:
- North Node
- South Node
- Chiron
- Vertex
- Part of Fortune
- Lilith

Each requires:
- explicit orb profile
- known/unknown-time validity policy
- scoring contribution or explicit no-scoring status

Do not expose experimental points merely because they exist internally.

## 7. Rulers/dispositors

If natal v1.0 supports house rulers/dispositors, add canonical relationship ruler interactions.

Potential structures:
- A house ruler contacting B planet/point
- A ruler falling into B house
- B planet activating A relationship-relevant ruler

Do not invent rulership logic outside the core.

## 8. Directional interpretation support

Represent A→B and B→A explicitly for:
- house overlays
- angle contacts
- ruler interactions
- directional point contacts

Create machine-readable directional themes such as:

```json
{
  "direction": "A_TO_B",
  "theme": "emotional_activation",
  "evidenceIds": []
}
```

No prose required.

## 9. Ranking upgrade

Upgrade ranking using:
- relationship profile
- directional salience
- score contributions
- richer points/rulers
- evidence diversity

Avoid returning five near-duplicate contacts when a diverse explanation is more useful.

## 10. Missing-data normalization

Handle:
- both times known
- one unknown
- both unknown

Rules:
- unavailable angles/houses are missing, not negative evidence
- do not inject zero contributions for unavailable data
- add coverage metric or equivalent normalization
- scores must remain comparable enough for product use

## 11. Canonical result extensions

Possible additions:
- relationshipProfile
- scores
- contributions
- directionalThemes
- pointContacts
- rulerInteractions
- coverage

Version schema appropriately.

## 12. Required tests

Scoring:
- deterministic
- within range
- no NaN/inf
- contribution sum/decomposition correct
- no duplicate contribution IDs
- all evidence IDs exist

Profiles:
- same geometry + different relationship profile produces documented weighting/ranking changes

Unknown-time:
- missing angles/houses do not catastrophically distort scores

Direction:
- swapping A/B preserves symmetric overall score if methodology says it should
- directional results swap correctly

Points/rulers:
- only canonical supported inputs used

## 13. Documentation

Create `docs/SYNASTRY_SCORING.md` covering dimensions, weights, orb modifiers, body-pair modifiers, relationship profiles, normalization, overall formula, caveats, and versioning.

## 14. Evidence

Create `evidence/synastry-v1.5/`:
- TASK_RESULT.md
- TEST_OUTPUT.txt
- SCORING_MODEL.md
- DIMENSION_MODEL.md
- RELATIONSHIP_PROFILES.md
- POINT_CONTACTS.md
- RULER_INTERACTIONS.md
- DIRECTIONAL_MODEL.md
- MISSING_DATA_NORMALIZATION.md
- SCORE_INVARIANTS.md
- API_PARITY.md
- OPENAPI_REPORT.md
- PERFORMANCE.md
- FRONTEND_HANDOFF.md

## 15. Quality gates

```bash
ruff check .
mypy src
pytest -q
```

Also run scoring fixtures, profile suite, unknown-time normalization, swap/direction suite, API parity, OpenAPI export, natal regression, and Synastry V1 regression.

## PASS criteria

PASS only if scoring is deterministic/decomposable, relationship profiles are versioned, missing-data normalization works, richer supported points/rulers are integrated at documented scope, directional structures exist, no LLM scoring exists, and all regression/quality/evidence gates pass.

## Final response

### Synastry V1.5 Result
PASS | FAIL | BLOCKED

### Scoring
### Overall score
Implemented | Deferred
### Dimensions
### Relationship profiles
### Points
### Rulers
### Directional model
### Missing-data normalization
### API/OpenAPI
### Validation
### Quality gates
### Known limitations
### Next recommended phase
Synastry V2 / Full
