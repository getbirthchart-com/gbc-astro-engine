# 01 — Master Requirements

## 1. Scope

Build a reusable Python astrology calculation package named `gbc_astro`.

The package must support deterministic chart calculation and derived astrology primitives. It must not contain generative AI, marketing copy, SEO content or user-facing prose interpretation.

## 2. Supported inputs

A chart calculation may originate from:

- exact UTC datetime;
- local datetime + IANA timezone;
- local date/time + coordinates + explicitly resolved timezone;
- unknown birth time mode.

### Required exact-time fields

```python
ChartInput(
    local_datetime: datetime,
    timezone: str,              # IANA ID
    latitude: float,
    longitude: float,
    altitude_m: float | None = None,
)
```

### Validation

- latitude: `[-90, 90]`
- longitude: `[-180, 180]`
- timezone must resolve through configured TZ database
- invalid/nonexistent local DST time must produce structured error
- ambiguous DST time must require explicit fold/resolution
- unsupported ephemeris date range must produce structured error
- unknown birth time must never fabricate ASC/MC/houses

## 3. Time provenance

Every result must record:

- local datetime supplied
- timezone ID
- UTC datetime
- Julian Day used internally
- timezone data version if available
- calendar mode
- provider-specific timescale metadata if relevant

Do not store only a numeric UTC offset.

## 4. Supported celestial bodies

### v0.1 required

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
- True Node
- Mean Node
- Chiron

### Optional/provider-dependent

- Mean Lilith
- True/Osculating Lilith
- Ceres
- Pallas
- Juno
- Vesta
- arbitrary asteroid IDs

The provider layer must expose capability metadata rather than making unsupported bodies fail unpredictably.

## 5. Required position fields

For each body:

```text
body_id
ecliptic_longitude_deg
ecliptic_latitude_deg
distance
longitude_speed_deg_per_day
retrograde
zodiac_sign
degree_in_sign
house_number | null
```

Keep full numerical precision internally.

## 6. Zodiac

### Required
- Tropical

### Architecture-ready
- Sidereal
- configurable ayanamsa profile

Zodiac mapping must be a pure deterministic module independent of provider.

## 7. Angles

Required when exact birth time exists:

- Ascendant
- Midheaven
- Descendant
- Imum Coeli

Architecture-ready:

- Vertex
- Anti-Vertex
- East Point

## 8. Houses

### v0.1
- Whole Sign
- Equal
- Placidus

### v1.0 target
- Koch
- Porphyry
- Campanus
- Regiomontanus
- Alcabitius
- Morinus
- Meridian
- Topocentric

High-latitude and mathematically undefined cases must return explicit warnings/errors according to calculation profile.

No silent fallback unless a profile explicitly enables fallback behavior, and the fallback used must be recorded in result metadata.

## 9. Aspects

### v0.1 major
- conjunction
- sextile
- square
- trine
- opposition

### extended
- semisextile
- semisquare
- sesquiquadrate
- quincunx
- quintile
- biquintile

Aspect rules must be profile-driven.

Required fields:

```text
body_a
body_b
aspect_type
exact_angle
actual_angle
orb
applying | separating | exact | indeterminate
```

## 10. Derived natal calculations

Required:

- Big Three
- Moon phase
- element distribution
- modality distribution
- polarity distribution
- hemisphere counts
- quadrant counts

Architecture-ready:

- angularity
- dominant planets/signs
- stellium detection
- major chart-pattern detection

Dominance and pattern rules must be versioned because schools differ.

## 11. Relationship calculations

### Synastry
- natal A
- natal B
- cross aspects
- A planets in B houses
- B planets in A houses
- angle interactions

### Composite
- shortest-arc midpoint for circular longitude
- correct `359° + 1° => 0°`, not `180°`
- midpoint positions
- configurable house/angle methodology
- provenance

### Architecture-ready
- Davison relationship chart

## 12. Forecast calculations

### Transits
- current/transit positions
- transit-to-natal aspects
- transit planet through natal house
- exact orb
- applying/separating

### Event search
- exact transit hits
- sign ingress
- stations retrograde/direct
- exact longitude crossings
- world aspects between two moving bodies

Search routines must use bracketing/root finding/refinement, not merely day-by-day nearest samples.

## 13. Returns

Required roadmap:

- Solar Return
- Lunar Return
- generic planetary return
- Saturn Return helper
- Jupiter Return helper

A return is the exact return to natal ecliptic longitude according to the configured calculation profile.

Handle multiple exact hits caused by retrograde motion.

## 14. Advanced charts

v1.0 roadmap:

- secondary progressions
- solar arc directions
- relocation
- draconic
- harmonics
- astrocartography primitives

Each method must be isolated in its own module and calculation profile.

## 15. Determinism and versioning

Every result includes:

```text
schema_version
engine_version
ephemeris_provider
ephemeris_data_version
timezone_data_version
calculation_profile_id
house_algorithm_version
aspect_profile_version
```

Same input + same values above must reproduce the same deterministic result.

## 16. Performance targets

Initial targets, measured on a normal production CPU:

- natal chart calculation excluding geocoding: P95 < 100 ms where provider permits
- cached natal: P95 < 20 ms
- 10,000-chart batch calculation: practical offline batch execution with bounded memory
- event search must expose progress/limits for large date intervals

Correctness beats premature optimization.

## 17. Security / robustness

- no eval/exec of user formulas
- strict enum/profile validation
- bounded date ranges
- bounded asteroid/body queries
- structured exceptions
- no untrusted file path accepted for ephemeris data
- API layer rate limiting is outside core library
