# 09 — Implementation Tasks

This is the executable task backlog for a coding agent.

---

## Phase 00 — Repository foundation

### 00.1 Initialize package
- src layout
- `pyproject.toml`
- Python 3.12+
- Ruff
- type checker
- pytest
- Hypothesis
- CLI entrypoint placeholder
- CI

Acceptance:
- import package
- lint/type/test commands pass

### 00.2 Core models/errors
Implement:
- enums
- input models
- chart models
- typed errors
- version metadata model

Acceptance:
- serialization tests
- validation tests

### 00.3 Circular math primitives
Implement:
- normalize longitude
- shortest angular distance
- directed circular delta
- shortest-arc midpoint

Acceptance:
- property tests
- 0/360 edge tests

---

## Phase 01 — Time

### 01.1 IANA timezone normalization
- local → UTC
- DST ambiguity detection
- nonexistent time detection

### 01.2 Julian/provider time adapter
Keep provider-specific conversion isolated.

Acceptance:
- known UTC conversions
- DST edge tests
- leap-day tests

---

## Phase 02 — Ephemeris provider

### 02.1 Provider protocol
Capabilities, version, date range.

### 02.2 Swiss/reference provider
Implement selected provider integration.

### 02.3 Body position normalization
Return common `RawBodyPosition`.

Acceptance:
- Sun/Moon/planets for curated instants
- speed/retrograde tests

### 02.4 JPL provider scaffold
Interface only initially unless explicitly prioritized.

---

## Phase 03 — Zodiac

### 03.1 Tropical mapping
- sign
- degree in sign

### 03.2 Boundary tests
All 12 boundaries.

Acceptance:
- full property/boundary suite

---

## Phase 04 — Angles & houses

### 04.1 Whole Sign
### 04.2 Equal
### 04.3 ASC/MC/DSC/IC
### 04.4 Placidus
### 04.5 Planet house assignment
### 04.6 High-latitude behavior

Acceptance:
- reference parity cases
- cusp boundary tests
- no silent fallback

---

## Phase 05 — Natal chart

### 05.1 Generic `calculate_chart`
### 05.2 `calculate_natal_chart`
### 05.3 Exact-time mode
### 05.4 Unknown-time mode
### 05.5 Canonical JSON serialization

Acceptance:
- complete v0.1 chart except aspects/derived
- provenance complete

---

## Phase 06 — Aspects

### 06.1 Aspect profile model
### 06.2 Major aspect classification
### 06.3 Orb calculation
### 06.4 Applying/separating
### 06.5 Minor aspect extensibility

Acceptance:
- angular boundary tests
- relative-motion tests

---

## Phase 07 — Derived natal

### 07.1 Big Three
### 07.2 Moon phase
### 07.3 Elements
### 07.4 Modalities
### 07.5 Polarity
### 07.6 Hemispheres/quadrants

Acceptance:
- deterministic profile-driven tests

---

## Phase 08 — v0.1 parity gate

### 08.1 Golden corpus
### 08.2 10K differential generator
### 08.3 Mismatch classifier/report
### 08.4 Benchmark CLI
### 08.5 Regression fixture generation

Acceptance:
- v0.1 Definition of Done PASS

STOP HERE before advanced features if v0.1 has unexplained mismatches.

---

## Phase 09 — Relationship v0.2

### 09.1 Synastry cross aspects
### 09.2 House overlays
### 09.3 Angle interactions
### 09.4 Composite midpoint positions
### 09.5 Composite chart profile

Acceptance:
- relationship DoD PASS

---

## Phase 10 — Transit snapshot

### 10.1 Transit positions
### 10.2 Transit-to-natal aspects
### 10.3 Transit through natal houses

---

## Phase 11 — Numerical search engine

### 11.1 Generic bracket/refine solver
### 11.2 Exact longitude search
### 11.3 Ingress search
### 11.4 Station search
### 11.5 Moving-body aspect search

Acceptance:
- synthetic numerical tests
- known astronomical event reference tests

---

## Phase 12 — Returns

### 12.1 Generic planetary return
### 12.2 Solar Return
### 12.3 Lunar Return
### 12.4 Saturn/Jupiter helpers
### 12.5 Multi-hit retrograde handling

---

## Phase 13 — Professional modules

Implement one by one, each behind its own acceptance spec:
- progressions
- solar arc
- relocation
- sidereal
- draconic
- harmonics
- additional house systems
- patterns
- astrocartography
- ephemeris generator
- asteroids

Do not bundle these into one giant task.
