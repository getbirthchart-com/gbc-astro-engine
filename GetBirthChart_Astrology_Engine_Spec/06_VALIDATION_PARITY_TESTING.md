# 06 — Validation, Parity & Testing

## 1. Correctness philosophy

A chart engine is not production-ready because several manually checked charts “look right”.

Validation must be:
- numerical
- automated
- randomized
- reproducible
- edge-case heavy
- regression-protected

## 2. Test pyramid

### Unit
Pure math:
- longitude normalization
- sign boundaries
- circular distance
- circular midpoint
- aspect classification
- house assignment
- balance calculations

### Golden
Curated birth/event inputs with frozen expected results.

### Differential
Compare GBC output against a trusted reference implementation.

### Edge case
DST, historical timezone, high latitude, 0/360 boundaries, stations, retrograde loops.

### Regression
Every discovered bug creates a permanent regression case.

## 3. Differential corpus

Minimum before production v0.1:

**10,000 randomized exact-time charts**

Prefer eventually 100,000 offline cases.

Distribution must vary:

### Years
- 1900–2026 heavily
- earlier/later supported dates sampled separately

### Locations
- North America
- South America
- Europe
- Africa
- Asia
- Oceania
- near equator
- high northern latitude
- high southern latitude
- near International Date Line

### Time
- all hours
- DST transitions
- midnight boundaries
- leap days

## 4. Compare numerically

For every case compare:

- Sun longitude
- Moon longitude
- Mercury–Pluto longitude
- node/chiron where comparable
- body speeds
- retrograde flags
- ASC
- MC
- house cusps
- house assignments
- major aspects

Do not compare only zodiac sign names.

## 5. Tolerance policy

Do not invent tolerances casually.

Create a `ToleranceProfile` and calibrate against:
- provider/reference numerical characteristics
- expected float precision
- differences in named conventions

Example shape:

```python
ToleranceProfile(
    body_longitude_deg=...,
    moon_longitude_deg=...,
    angle_longitude_deg=...,
    house_cusp_deg=...,
)
```

Any tolerance chosen must be documented with rationale.

## 6. Mismatch classification

Every differential failure must be classified:

- implementation bug
- timezone mismatch
- calendar mismatch
- provider convention mismatch
- node convention mismatch
- house-system convention mismatch
- known numerical tolerance
- unresolved

No unexplained production mismatch should be waved away.

## 7. Critical edge cases

### Zodiac boundaries
- 29°59'59.999"
- exactly 30°
- 359.999...
- exactly normalized 0°

### Circular midpoint
- 359° & 1°
- 350° & 10°
- opposite points

### DST
- nonexistent spring-forward local time
- repeated fall-back local time
- historical rule changes

### Latitude
- equator
- Arctic/Antarctic circle vicinity
- Placidus-invalid scenarios

### Retrograde
- speed close to zero
- station before/after
- repeated sign ingress

### Moon
- near sign boundary
- phase boundaries

### Houses
- body exactly at cusp
- cusp crossing 0° Aries

### Returns
- multiple return hits in retrograde cycle

## 8. External application spot checks

Use Astro.com / Astro-Seek outputs as human-facing sanity references for selected cases, while treating numerical/library reference tests as the primary automated oracle.

When external sites differ:
- verify selected house system
- zodiac type
- node type
- timezone
- coordinates
- aspect orb settings

Do not tune engine to screenshots without understanding configuration differences.

## 9. Test commands

Desired:

```bash
pytest
pytest tests/unit
pytest tests/edge_cases
pytest tests/differential
gbc benchmark --cases 10000 --seed 42
```

## 10. Benchmark report

Generate machine-readable + human-readable reports:

```text
provider
cases
seed
max_delta by body
p50/p95/p99 delta
ASC max delta
MC max delta
house cusp max delta
mismatch count
mismatch classifications
runtime
```

## 11. CI

Every PR:
- formatting/lint
- type checking
- unit
- golden
- regression
- selected fast differential subset

Nightly/weekly:
- large randomized differential corpus
- performance benchmark
