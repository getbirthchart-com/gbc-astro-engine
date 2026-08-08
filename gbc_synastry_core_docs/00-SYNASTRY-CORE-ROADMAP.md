# GetBirthChart Core — Synastry Roadmap

Repository: `gbc-astro-engine/`

Scope: Python core only. UI/frontend comes later.

## Principles

1. `gbc-astro-engine` owns all astrology facts.
2. LLMs never calculate synastry geometry, overlays, composite positions, progressions, or relationship transits.
3. Scoring must be deterministic, versioned, auditable, and reproducible.
4. Unknown birth time must degrade safely.
5. Existing natal v1.0 behavior must remain backward-compatible.
6. Synastry work is additive and isolated from stable natal code.
7. Public contracts must use canonical Pydantic models and explicit OpenAPI schemas.
8. Every derived result must carry provenance/profile versions.
9. Frontend must never need to recreate astrology math.

## Version plan

### Synastry V1
- Cross-chart aspects
- Angle contacts
- House overlays
- Top strengths/challenges
- Basic dimension signals

Primary result: `SynastryResultV1`

### Synastry V1.5
- Deterministic scoring
- Relationship-type profiles
- Richer points/rulers
- Directional interpretation support

Primary result: `SynastryResultV1_5`

### Synastry V2 / Full
- Composite Chart
- Advanced relationship patterns
- Complete scoring methodology
- Machine-readable support for future Ask about us
- Machine-readable support for future Couple PDF

Important: Ask UI and PDF rendering remain frontend concerns. Core only exposes authoritative evidence/grouping.

Primary results:
- `SynastryResultV2`
- `CompositeChart`

### Synastry V2.5+
- Current relationship transits
- Composite transits
- Progressed synastry
- Progressed composite

Possible results:
- `RelationshipTransitResult`
- `CompositeTransitResult`
- `ProgressedSynastryResult`
- `ProgressedCompositeResult`

## Suggested package structure

```text
src/gbc_astro/
  synastry/
    models.py
    aspects.py
    overlays.py
    angles.py
    points.py
    rulers.py
    ranking.py
    dimensions.py
    scoring.py
    profiles.py
    patterns.py
    composite.py
    transits.py
    progressions.py
    service.py
    provenance.py
```

Adapt to repository conventions.

## Deterministic IDs

Examples:

```text
synastry.a.sun.trine.b.moon
synastry.a.venus.conjunction.b.mars
synastry.a.sun.in.b.house_7
synastry.a.mars.conjunction.b.asc
synastry.dimension.emotional
```

IDs contain no display prose.

## Unknown-time policy

Allowed:
- planet-to-planet cross aspects
- stable time-independent points

Unavailable as applicable:
- ASC/DSC/MC/IC
- house overlays into a chart whose houses are unknown
- house-ruler features dependent on unavailable cusps
- unsupported time-sensitive points

Never substitute noon-based houses or angles.

## Evidence rule

Every derived score/rank/theme must reference canonical evidence IDs. No opaque compatibility number may exist without decomposable contributing signals.

## Shared validation

Every version requires:
- deterministic fixtures
- symmetry/direction tests
- circular 0°/360° tests
- unknown-time tests
- malformed input rejection
- reproducibility
- performance benchmark
- library/API parity
- explicit OpenAPI snapshot
- natal regression protection

## Recommended profile versioning

```text
synastry-aspect-profile-v1
synastry-ranking-v1
synastry-dimensions-v1
synastry-scoring-v1
relationship-profile-romantic-v1
relationship-profile-friendship-v1
relationship-profile-family-v1
relationship-profile-work-v1
composite-profile-v1
relationship-transit-profile-v1
progression-profile-v1
```

Material methodology changes create new versions; never silently mutate old behavior.

## Non-goals for Python core

- React/Next.js
- payment logic
- PDF rendering
- SEO pages
- marketing copy
- LLM prose

The core may expose structured report/evidence models needed by downstream products.
