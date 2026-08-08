# 03 — Calculation Specification

## 1. Time normalization

Input local datetime must be resolved through an IANA timezone.

Pipeline:

```text
local datetime + IANA timezone
→ validate ambiguity/nonexistence
→ UTC instant
→ provider time conversion as required
```

DST ambiguity must not be guessed.

## 2. Planetary positions

The provider returns at minimum:

```python
RawBodyPosition(
    longitude_deg: float,
    latitude_deg: float,
    distance: float | None,
    longitude_speed_deg_per_day: float | None,
)
```

Engine derives:

```python
retrograde = speed < 0
```

Stationary threshold, if exposed, must be profile-defined and not confused with retrograde boolean.

## 3. Zodiac mapping

For tropical zodiac:

| Longitude | Sign |
|---|---|
| [0,30) | Aries |
| [30,60) | Taurus |
| [60,90) | Gemini |
| [90,120) | Cancer |
| [120,150) | Leo |
| [150,180) | Virgo |
| [180,210) | Libra |
| [210,240) | Scorpio |
| [240,270) | Sagittarius |
| [270,300) | Capricorn |
| [300,330) | Aquarius |
| [330,360) | Pisces |

Boundary tests are mandatory.

## 4. Angles

Exact-time charts must calculate:

- ASC
- MC
- DSC = ASC + 180° normalized
- IC = MC + 180° normalized

Angles must be associated with zodiac position.

## 5. Houses

### Whole Sign
- house 1 begins at 0° of Ascendant sign
- each subsequent sign is next house

### Equal
- house 1 cusp begins at Ascendant degree
- each cusp +30°

### Placidus
- implement through a validated reference/provider or an independently verified algorithm
- do not copy an unverified internet formula
- explicitly handle high-latitude failure

### Planet house assignment

Assignment must account for wraparound near 0° Aries and exact cusp policy.

Cusp policy must be explicit:
- exact cusp belongs to following house, or
- configurable convention

Default convention must be documented and versioned.

## 6. Aspects

### Major default profile example

```text
conjunction: 0°, orb 8°
sextile: 60°, orb 5°
square: 90°, orb 7°
trine: 120°, orb 7°
opposition: 180°, orb 8°
```

These are defaults, not universal astrology truth. Keep profile-driven.

### Applying/separating

Determine from relative angular motion, not from simplistic longitude comparison.

Provide:
- `applying`
- `separating`
- `exact`
- `indeterminate` when velocities are unavailable

## 7. Moon phase

Use normalized elongation:

```text
Moon longitude - Sun longitude
```

Expose:
- phase angle
- phase name
- illumination estimate only if implemented and validated astronomically
- waxing/waning

Do not call an unvalidated rough label astronomically precise.

## 8. Balances

Element and modality calculations are deterministic astrology classifications over selected bodies.

Profile must define:
- which bodies count
- whether ASC/MC count
- optional weighting

Default simple profile should be transparent.

## 9. Synastry

Inputs are two natal charts generated under compatible coordinate/zodiac semantics.

Calculate:
- all configured A-to-B aspects
- A bodies in B houses
- B bodies in A houses
- body-to-angle interactions

Do not generate a compatibility percentage in deterministic engine unless a separately versioned scoring profile is explicitly defined.

## 10. Composite chart

For each pair of corresponding positions:
- compute shortest-arc midpoint
- preserve circular correctness
- derive composite zodiac positions

House/angle methodology must be explicitly defined by profile.

## 11. Transits

For target instant:
- calculate transit positions
- compare transit bodies with natal positions
- detect configured aspects
- assign transit bodies to natal houses
- emit applying/separating when possible

## 12. Exact event search

Use a shared numerical solver.

Required algorithmic pattern:

1. coarse stepping to detect candidate intervals
2. bracket root/event
3. refine using bisection/Brent-like method or validated equivalent
4. stop on time/angular tolerance
5. deduplicate adjacent detections

Never implement exact-return/ingress/transit event search as “closest daily sample”.

## 13. Sign ingress

Find roots of the body longitude crossing a sign boundary.

Handle:
- direct ingress
- retrograde ingress
- multiple entries into same sign

## 14. Stations

Find changes in longitude speed sign:
- positive → negative: station retrograde
- negative → positive: station direct

Refine zero-speed time.

## 15. Returns

For a body with natal longitude `L0`, find exact target times where moving longitude equals `L0` on a circular domain.

Return all hits within search window, not just first, because retrograde motion may create multiple exact returns.

## 16. Solar Return

Specialization of generic return for Sun.

Inputs:
- natal chart
- target year/search window
- return location

Output:
- exact UTC/local return instant
- full return chart
- metadata linking natal target longitude

## 17. Lunar Return

Same as Solar Return for Moon.

Search windows must be bounded appropriately.

## 18. Secondary progressions

Keep isolated under a versioned methodology profile.

Do not implement until natal/transit parity is complete.

## 19. Solar arc

Keep direction-key behavior profile-driven and versioned.

## 20. Relocation

At same exact instant:
- planetary positions remain tied to instant/reference conventions
- angles/houses are recalculated for relocation coordinates

## 21. Sidereal

Apply a versioned ayanamsa transformation only in the zodiac layer.

Do not silently mix tropical houses/positions with sidereal labels without explicit profile semantics.
