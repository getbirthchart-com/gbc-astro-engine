# 10 — Definition of Done

## v0.1 Natal Core DoD

### Functional
- [ ] exact local birth datetime + timezone + coords supported
- [ ] unknown-time mode supported
- [ ] Sun through Pluto
- [ ] True/Mean Node
- [ ] Chiron
- [ ] longitude/latitude/speed
- [ ] retrograde
- [ ] tropical zodiac
- [ ] ASC/MC/DSC/IC
- [ ] Whole Sign
- [ ] Equal
- [ ] Placidus
- [ ] 12 house cusps
- [ ] body house assignments
- [ ] 5 major aspects
- [ ] configurable orbs
- [ ] applying/separating
- [ ] Big Three
- [ ] Moon phase
- [ ] elements/modalities
- [ ] hemispheres/quadrants
- [ ] canonical JSON
- [ ] Python API
- [ ] CLI

### Correctness
- [ ] 10K randomized differential corpus executed
- [ ] mismatch report generated
- [ ] no unexplained material mismatches
- [ ] sign boundaries covered
- [ ] DST ambiguity/nonexistent-time covered
- [ ] high-latitude behavior covered
- [ ] 0/360 boundaries covered
- [ ] cusp boundaries covered
- [ ] station/retrograde boundary covered

### Engineering
- [ ] deterministic tests
- [ ] Ruff pass
- [ ] typecheck pass
- [ ] pytest pass
- [ ] canonical schema versioned
- [ ] engine/provider/profile versions returned
- [ ] no LLM dependency
- [ ] no FastAPI dependency in core

### Documentation
- [ ] README usage
- [ ] profile defaults documented
- [ ] house behavior documented
- [ ] aspect defaults documented
- [ ] unknown-time behavior documented
- [ ] known limitations documented

A release cannot be called production-ready until every required box is checked or explicitly waived with a written rationale.

---

## v0.2 Relationship DoD

- [x] synastry cross aspects
- [x] house overlays both directions
- [x] angle interactions
- [x] composite shortest-arc midpoint correctness
- [x] 0/360 composite regression cases
- [x] schemas versioned
- [x] tests/golden references

Evidence: `evidence/v0.2-relationship/TASK_RESULT.md`.

Beyond the required list: composite houses and angles derived from the
midpoint Midheaven, and Davison relationship charts.

---

## v0.3 Forecast/Return DoD

- [x] transit snapshot
- [x] exact event solver
- [x] ingress search
- [x] station search
- [x] exact transit search
- [x] Solar Return
- [x] Lunar Return
- [x] planetary return
- [x] retrograde multi-hit support
- [x] solver precision documented
- [x] no daily-sampling masquerading as exact search
- [x] reference validation

Evidence: `evidence/v0.3-forecast/TASK_RESULT.md`.

---

## v1.0 Professional DoD

Every advanced module has:
- [x] explicit methodology
- [x] immutable versioned calculation profile
- [x] reference implementation/data
- [x] unit tests
- [x] golden tests
- [x] edge-case tests
- [x] schema integration
- [x] provenance
- [x] documented limitations

All eleven modules implemented, each behind its own acceptance spec as Phase 13
requires. Evidence per module:

| Module | Evidence |
|---|---|
| Sidereal + ayanamsa | `evidence/v1.0-sidereal/` |
| Extended house systems | `evidence/v1.0-house-systems/` |
| Draconic, harmonic | `evidence/v1.0-transforms/` |
| Progressions, solar arc | `evidence/v1.0-progressions/` |
| Advanced patterns | `evidence/v1.0-patterns/` |
| Relocation, astrocartography | `evidence/v1.0-relocation-acg/` |
| Ephemeris generator, asteroids | `evidence/v1.0-ephemeris-asteroids/` |
