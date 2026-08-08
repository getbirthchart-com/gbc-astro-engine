# GetBirthChart Astrology Engine — Engineering Spec Pack

## Purpose

This repository/spec pack defines a production-grade deterministic astrology calculation engine for GetBirthChart.

The engine must be able to support a consumer product at the level expected from serious astrology applications: natal charts, exact planetary positions, houses, angles, aspects, synastry, composite charts, transits, returns, progressions, relocation and ephemeris/event search.

The engine is **not** an AI interpretation engine.

> Astronomy/calculation owns facts.  
> Astrology-domain rules own deterministic derived facts.  
> LLMs may only interpret the final canonical chart JSON.

## Non-negotiable principles

1. **Deterministic** — same input + same engine/profile/data versions = same output.
2. **Provider abstraction** — astronomical ephemeris provider is replaceable.
3. **No LLM in calculation path.**
4. **No silent guessing** for unknown birth time, timezone ambiguity, unsupported house calculations or invalid coordinates.
5. **Version everything** needed to reproduce a chart.
6. **Differential testing is a first-class feature.**
7. **Ship by release boundary**. Do not implement every advanced chart type before natal-core parity is achieved.
8. **Internal precision must exceed presentation precision.**
9. **Public JSON contracts must remain stable and explicitly versioned.**
10. **Calculated facts and interpretive text are separate systems.**

## Recommended implementation order

### v0.1 — Natal Core
- Time normalization
- Ephemeris provider
- Tropical zodiac
- Sun through Pluto
- True/Mean Node support
- Chiron
- Retrograde / velocity
- ASC, MC, DSC, IC
- Whole Sign, Equal, Placidus
- House assignments
- Major aspects
- Applying/separating
- Big Three
- Moon phase
- Element/modality balance
- Unknown birth-time mode
- Canonical JSON
- CLI
- Golden + differential test suite

### v0.2 — Relationship
- Synastry
- Cross aspects
- House overlays
- Composite midpoint chart
- Relationship primitives suitable for an interpretation layer

### v0.3 — Forecast & Returns
- Transits
- Exact transit event search
- Ingress search
- Retrograde station search
- Solar Return
- Lunar Return
- Generic planetary returns
- Saturn/Jupiter return helpers

### v1.0 — Professional
- Secondary progressions
- Solar arc
- Relocation
- Draconic
- Harmonic
- Sidereal + ayanamsa profiles
- Extended house systems
- Advanced patterns
- Astrocartography primitives
- Ephemeris generator
- Arbitrary asteroid support where provider permits

## Suggested repository layout

```text
gbc-astro-engine/
├── src/gbc_astro/
│   ├── astronomy/
│   ├── providers/
│   ├── zodiac/
│   ├── houses/
│   ├── aspects/
│   ├── charts/
│   ├── forecasts/
│   ├── returns/
│   ├── search/
│   ├── derived/
│   ├── models/
│   ├── profiles/
│   └── engine.py
├── tests/
│   ├── unit/
│   ├── golden/
│   ├── differential/
│   ├── regression/
│   └── edge_cases/
├── benchmarks/
├── scripts/
├── api/
├── docs/
└── pyproject.toml
```

## Documents in this pack

- `01_MASTER_REQUIREMENTS.md` — product and correctness requirements
- `02_ARCHITECTURE.md` — module boundaries and dependency rules
- `03_CALCULATION_SPEC.md` — deterministic calculation behavior
- `04_CANONICAL_JSON_CONTRACT.md` — stable schemas
- `05_RELEASE_PLAN.md` — implementation phases and acceptance gates
- `06_VALIDATION_PARITY_TESTING.md` — golden, differential and edge-case testing
- `07_API_CLI_SPEC.md` — Python API, CLI and FastAPI adapter
- `08_AI_CODING_AGENT_RULES.md` — instructions for the coding agent
- `09_IMPLEMENTATION_TASKS.md` — executable task checklist
- `10_DEFINITION_OF_DONE.md` — release acceptance criteria

## Global definition of success

The project is successful when:

- v0.1 produces natal-chart facts matching the selected reference implementation within documented tolerances across a large randomized corpus;
- edge cases are handled explicitly rather than silently;
- every result declares its engine/profile/provider/timezone-data versions;
- GetBirthChart web/mobile/API clients can consume one canonical JSON format;
- advanced modules extend the same engine rather than creating parallel incompatible calculators.
