# House systems

Eleven systems. Which one you choose changes where every planet sits without
changing where any planet is.

| id | Name | Quadrant | All latitudes | Validation |
|---|---|---|---|---|
| `placidus` | Placidus | yes | **no** | independent |
| `koch` | Koch | yes | **no** | structural |
| `porphyry` | Porphyry | yes | yes | independent |
| `campanus` | Campanus | yes | yes | structural |
| `regiomontanus` | Regiomontanus | yes | yes | structural |
| `alcabitius` | Alcabitius | yes | yes | structural |
| `topocentric` | Topocentric (Polich-Page) | yes | yes | structural |
| `morinus` | Morinus | no | yes | structural |
| `meridian` | Meridian (axial rotation) | no | yes | independent |
| `whole_sign` | Whole Sign | no | yes | independent |
| `equal` | Equal | yes | yes | independent |

*Quadrant* means cusp 1 is the Ascendant and cusp 10 the Midheaven. Morinus and
Meridian ignore the horizon, so neither holds.

```python
chart = engine.natal(..., house_system="regiomontanus")
```

The angles are identical across all eleven — only the cusps between them move.

## Two strengths of validation

**Independent.** Placidus, Porphyry and Meridian are re-derived from their
definitions without Swiss Ephemeris and compared numerically. Whole Sign and
Equal are derived by the engine itself from the Ascendant.

| System | Definition used | Max delta |
|---|---|---:|
| Placidus | thirds of the semi-diurnal and semi-nocturnal arcs | 0.0058″ |
| Porphyry | trisected ecliptic arcs between the angles | 0.0058″ |
| Meridian | ecliptic points at RAMC + 30k in right ascension | 0.0019″ |
| Whole Sign / Equal | derived from the Ascendant | 0.0000″ |

**Structural.** Koch, Campanus, Regiomontanus, Alcabitius, Topocentric and
Morinus have no independent reference here. Calling them validated because Swiss
Ephemeris produced them would be validating a thing against itself. They are
held to the properties any house system must satisfy:

- twelve cusps, advancing in zodiacal order, closing the circle
- cusp 1 on the Ascendant and cusp 10 on the Midheaven, for quadrant systems
- cusp k + 6 exactly opposite cusp k
- every longitude landing in exactly one house

That catches a wrong code, a swapped array, an off-by-one or a silent fallback.
It does not catch a subtly wrong cusp formula inside Swiss Ephemeris, and this
documentation does not pretend otherwise.

```bash
gbc validate house-systems
```

## Beyond the polar circles

Three different behaviours, and the difference matters:

**Placidus and Koch refuse.** The arcs they divide do not exist there. The engine
raises `HOUSE_CALCULATION_UNAVAILABLE` rather than substituting a system that
happens to be defined.

**Campanus, Regiomontanus and Topocentric invert.** They return cusps that run
*backwards* — cusp 2 falls behind cusp 1, and a house can span more than half the
zodiac. Measured at 69.65 N, Campanus produced cusps stepping 221°, 356°, 358°.
The result is mathematically defined and astrologically meaningless.

The engine returns it with a `HOUSE_SEQUENCE_DEGENERATE` warning rather than
presenting it as an ordinary chart. Do not rely on house assignments when that
warning is present.

**Whole Sign and Equal are unaffected.** Neither depends on the horizon geometry
that breaks down, which is one practical reason Whole Sign is the default for
the sidereal profile.

Degeneracy *inside* the polar circles would be a defect and fails the validation
gate. None occurs.

## Limitations

- Six of the eleven have no independent numerical reference. Adding one means
  deriving the system from its definition, as was done for Porphyry and
  Meridian; the structural gate is a floor, not a ceiling.
- Gauquelin sectors, Vehlow, and APC houses are not implemented.
