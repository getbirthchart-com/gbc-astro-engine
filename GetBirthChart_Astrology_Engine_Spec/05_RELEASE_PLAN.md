# 05 — Release Plan

## Rule

Do not proceed to a later release because “features seem to work”.
Proceed only when the acceptance gate of the current release passes.

---

# v0.1 — Natal Core

## Features

### Input/time
- exact birth local datetime
- IANA timezone normalization
- coordinates
- DST ambiguity handling
- unknown birth-time mode

### Astronomy
- provider abstraction
- Sun through Pluto
- True Node
- Mean Node
- Chiron
- longitude/latitude/speed
- retrograde

### Zodiac
- tropical
- exact degree-in-sign

### Angles/Houses
- ASC, MC, DSC, IC
- Whole Sign
- Equal
- Placidus
- body-house assignment

### Aspects
- conjunction
- sextile
- square
- trine
- opposition
- configurable orbs
- applying/separating

### Derived
- Big Three
- Moon phase
- elements
- modalities
- hemispheres
- quadrants

### Interfaces
- Python API
- CLI
- canonical JSON

### Testing gate
- unit tests
- edge-case tests
- >= 10,000 randomized differential cases against selected reference provider
- no unexplained material longitude/angle mismatches
- known DST/high-latitude cases documented
- regression corpus committed

**Only after this gate may GetBirthChart depend on v0.1 in production.**

---

# v0.2 — Relationship

## Features
- synastry
- cross aspects
- house overlays
- angle interactions
- composite chart
- circular midpoint tests

## Gate
- synastry cross-aspect corpus
- 0/360 midpoint tests
- house overlay reference tests
- compatibility with v0.1 schema/profile

---

# v0.3 — Forecast & Returns

## Features
- transit snapshot
- transit-to-natal aspects
- transit house placements
- exact transit event search
- ingress search
- station search
- exact-longitude search
- solar return
- lunar return
- generic planetary returns

## Gate
- numerical solver stress tests
- known retrograde multi-hit cases
- exact-return tests vs reference
- no duplicate/omitted roots in benchmark ranges

---

# v1.0 — Professional

## Features
- secondary progressions
- solar arc
- relocation
- sidereal + ayanamsa profiles
- extended houses
- advanced patterns
- draconic
- harmonic
- astrocartography primitives
- ephemeris generator
- optional asteroid support

## Gate
Each module must define:
- reference methodology
- calculation profile
- test oracle/reference
- edge cases
- tolerances
- provenance/version fields
