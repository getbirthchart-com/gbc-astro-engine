# House Systems

Status: PASS

Cases: 96
Tolerance: 1.0e-05 deg

## Supported systems

| id | Name | Swiss code | Quadrant | Defined at all latitudes |
|---|---|---|---|---|
| placidus | Placidus | P | yes | no |
| koch | Koch | K | yes | no |
| porphyry | Porphyry | O | yes | yes |
| campanus | Campanus | C | yes | yes |
| regiomontanus | Regiomontanus | R | yes | yes |
| alcabitius | Alcabitius | B | yes | yes |
| topocentric | Topocentric (Polich-Page) | T | yes | yes |
| morinus | Morinus | M | no | yes |
| meridian | Meridian (axial rotation) | X | no | yes |
| whole_sign | Whole Sign | W | no | yes |
| equal | Equal | E | yes | yes |

## Independently validated

Re-derived from their definitions without Swiss Ephemeris, then compared.

| System | Compared | Max delta (arcsec) | Outside tolerance |
|---|---:|---:|---:|
| placidus | 81 | 0.00580 | 0 |
| porphyry | 82 | 0.00580 | 0 |
| meridian | 82 | 0.00185 | 0 |
| whole_sign | 96 | 0.00000 | 0 |
| equal | 96 | 0.00000 | 0 |

## Structurally validated only

koch, campanus, regiomontanus, alcabitius, topocentric, morinus

No independent reference exists for these in this engine. Calling them
validated because Swiss Ephemeris produced them would be validating a
thing against itself, so they are held to invariants instead: twelve
cusps in zodiacal order closing the circle, cusp 1 on the Ascendant and
cusp 10 on the Midheaven for quadrant systems, axial symmetry, and every
longitude landing in exactly one house.

Invariant violations: 0

## Polar behaviour

Refusals (undefined beyond the polar circles): {'placidus': 15, 'koch': 15, 'porphyry': 0, 'campanus': 0, 'regiomontanus': 0, 'alcabitius': 0, 'topocentric': 0, 'morinus': 0, 'meridian': 0, 'whole_sign': 0, 'equal': 0}

Degenerate sequences, flagged: {'campanus': 4, 'regiomontanus': 4, 'topocentric': 5}

Unexpected degeneracy inside the polar circles: 0

Placidus and Koch have no solution beyond the polar circles and are
refused there. Campanus, Regiomontanus and Topocentric do not refuse --
they invert, returning cusps that run backwards. That is what the
geometry does, so the chart is returned with a HOUSE_SEQUENCE_DEGENERATE
warning rather than presented as ordinary. Degeneracy inside the polar
circles would be a defect and fails this gate.

## Notes

- Placidus, Porphyry and Meridian are re-derived from their definitions without Swiss Ephemeris and compared numerically. Whole Sign and Equal are derived by the engine from the Ascendant and checked against that derivation.
- Koch, Campanus, Regiomontanus, Alcabitius, Topocentric and Morinus have no independent reference here and are held to structural invariants only. Calling them validated because Swiss Ephemeris produced them would be validating a thing against itself.
- Placidus and Koch are undefined beyond the polar circles. The engine refuses them there; it never substitutes a system that happens to be defined.
- Campanus, Regiomontanus and Topocentric do not refuse beyond the polar circles; they invert, returning cusps that run backwards. That is what the geometry does, so the engine returns them with a HOUSE_SEQUENCE_DEGENERATE warning rather than pretending the chart is ordinary. Degeneracy inside the polar circles would be a defect and fails the gate.
