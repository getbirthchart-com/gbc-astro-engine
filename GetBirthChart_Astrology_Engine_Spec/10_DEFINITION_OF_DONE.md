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
- [ ] explicit methodology
- [ ] immutable versioned calculation profile
- [ ] reference implementation/data
- [ ] unit tests
- [ ] golden tests
- [ ] edge-case tests
- [ ] schema integration
- [ ] provenance
- [ ] documented limitations
