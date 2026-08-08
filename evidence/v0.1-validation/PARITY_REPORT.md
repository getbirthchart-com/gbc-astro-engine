# v0.1 Parity Report

Status: PASS

Both independent tracks required by `05_RELEASE_PLAN.md` now have a reference
that does not reuse the implementation it validates.

## Astronomy

Reference: `jpl-de440` DE440S (Skyfield, independent of Swiss Ephemeris)

| Body | Max delta (deg) |
|---|---:|
| Sun | 0.0005211014954511484 |
| Moon | 0.00781827189609885 |
| Mercury | 0.0011122772832408145 |
| Venus | 0.000635463248954693 |
| Mars | 0.00040148718380805803 |
| Jupiter | 0.00011349375023428365 |
| Saturn | 5.9535635330121295e-05 |
| Uranus | 4.530587240481054e-05 |
| Neptune | 1.8919191049349138e-05 |
| Pluto | 1.1862479311730567e-05 |

Cases: 10000
Retrograde mismatches: 0
Outside tolerance: 0
Unresolved: 0

Command: `gbc validate astronomy-parity --reference jpl-de440 --cases 10000 --seed 42`

## Angles and Houses

Reference: `gbc-independent-geometry` 1.0.0
(`skyfield-gast+true-obliquity/numeric-placidus`)

The reference re-derives Ascendant, MC and the twelve Placidus cusps from the
defining spherical relations, taking only apparent sidereal time and true
obliquity from Skyfield. It shares no code with Swiss Ephemeris. See
`docs/HOUSE_REFERENCE_METHODOLOGY.md`.

| Metric | p95 (deg) | Max (deg) | Max (arcsec) | Tolerance (deg) | Outside |
|---|---:|---:|---:|---:|---:|
| Ascendant | 5.667e-07 | 1.925e-06 | 0.006929 | 1e-05 | 0 |
| MC | 4.167e-07 | 5.109e-07 | 0.001839 | 1e-05 | 0 |
| Placidus cusps | 4.435e-07 | 1.925e-06 | 0.006929 | 1e-05 | 0 |

Cases: 500 generated, 464 compared, 5568 individual cusp comparisons
House assignment mismatches: 0
Undefined Placidus, both sides agree (excluded): 33
Convention differences (engine stricter, safe direction): 3
Disagreements: 0

Command: `gbc validate geometry-parity --cases 500 --seed 42`

Detail: `ANGLE_PARITY.md`, `PLACIDUS_PARITY.md`, `geometry-parity.json`.

### Convention difference

Swiss Ephemeris declines Placidus categorically beyond the polar circles; the
independent reference declines per case and still solves 3 of them. Probed
directly at 69.65 N: `houses_ex(..., b"P")` raises while `b"O"` returns values,
so the engine refuses rather than substituting another house system. Refusing
more often than strictly necessary cannot produce a wrong chart, so this is
recorded as a safe-direction convention difference. The unsafe direction --
cusps emitted where Placidus has no solution -- is counted as a disagreement
and fails the gate. There were none.

## Internal Gates

- hostile corpus: PASS (100 cases)
- reproducibility: PASS (75 cases x 3 runs)
- benchmark: PASS (10,000 cases each for Whole Sign, Equal, Placidus)
- ruff: PASS
- mypy: PASS (strict, 57 source files)
- pytest: PASS (93 passed with Swiss data and skyfield present)
- golden Swiss: PASS
- compileall: PASS
- production ephemeris setup: PASS

## Scope of this PASS

This covers the v0.1 natal core only: tropical zodiac, Sun through Pluto plus
nodes and Chiron, ASC/MC/DSC/IC, Whole Sign / Equal / Placidus, the five major
aspects, and the derived natal primitives.

It does not cover v0.2 relationship, v0.3 forecast/returns, or v1.0
professional modules, none of which are implemented.
