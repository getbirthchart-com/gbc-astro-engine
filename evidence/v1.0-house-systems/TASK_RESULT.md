Status: PASS

v1.0 module 2 of 11 — Extended house systems.

Adds Koch, Porphyry, Campanus, Regiomontanus, Alcabitius, Morinus, Meridian and
Topocentric to the existing Placidus, Whole Sign and Equal. That completes the
v1.0 target list in `01_MASTER_REQUIREMENTS.md` section 8.

## v1.0 DoD, per module

| Requirement | Where |
|---|---|
| Explicit methodology | `docs/HOUSE_SYSTEMS.md`, `houses/systems.py` |
| Immutable versioned profile | `HOUSE_SYSTEMS` registry, one entry per system |
| Reference implementation | Porphyry and Meridian derived independently |
| Unit tests | registry properties, invariants |
| Golden tests | independent parity, five systems |
| Edge-case tests | polar refusal, polar inversion, sidereal cross-product |
| Schema integration | `meta.houseSystem`, `houseAlgorithmVersion` |
| Provenance | system id and Swiss version recorded per chart |
| Documented limitations | six systems are structural-only |

## Two strengths, stated rather than blurred

Porphyry and Meridian were derived from their definitions and compared to Swiss
Ephemeris once, without tuning:

| System | Max delta |
|---|---:|
| Placidus | 0.0058 arcsec |
| Porphyry | 0.0058 arcsec |
| Meridian | 0.0019 arcsec |
| Whole Sign / Equal | 0.0000 arcsec |

Koch, Campanus, Regiomontanus, Alcabitius, Topocentric and Morinus have no
independent reference. They are held to invariants instead, and the report says
so rather than counting them as validated.

## What the gate found

The invariant sweep failed on first run: Campanus, Regiomontanus and Topocentric
violated monotonic cusp ordering at 69.65 N and -77.84 S.

Investigation showed this is real, not a defect. Beyond the polar circles those
systems **invert** — measured cusps at 69.65 N stepped 221, 356, 358 degrees,
meaning the houses run backwards. Placidus and Koch refuse outright; these three
return a mathematically defined and astrologically meaningless chart.

The engine was returning it **silently**, which `01_MASTER_REQUIREMENTS.md`
section 8 forbids: "High-latitude and mathematically undefined cases must return
explicit warnings/errors."

Fixed: `is_sequence_degenerate` detects the inversion and the chart carries
`HOUSE_SEQUENCE_DEGENERATE`. The gate now treats flagged inversion beyond the
polar circles as a recorded condition, and unflagged inversion, or any
inversion inside the polar circles, as a failure. There are none of either.

Whole Sign and Equal remain well-formed at every latitude, which is one
practical reason Whole Sign is the sidereal profile's default.

## Results

96 cases across equatorial, mid, high and polar latitudes, every hour of the day.

- Independent parity: 0 outside tolerance across all five systems
- Invariant violations: 0
- House assignment failures: 0
- Polar refusals: placidus 15, koch 15
- Flagged degeneracy: campanus 4, regiomontanus 4, topocentric 5
- Unexpected degeneracy inside the polar circles: 0

## Quality gates

ruff PASS · mypy strict PASS (80 files) · pytest PASS ·
`gbc validate house-systems` exit 0

## Not in this module

Gauquelin sectors, Vehlow, APC. Independent references for the six
structural-only systems remain open work; the structural gate is a floor.
