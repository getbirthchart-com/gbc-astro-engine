Status: PASS

v1.0 module 3 of 11 — Draconic and harmonic charts.

## v1.0 DoD, per module

| Requirement | Where |
|---|---|
| Explicit methodology | `docs/TRANSFORMS.md`, module docstrings |
| Immutable versioned profile | `DRACONIC_VERSION`, `HARMONIC_VERSION`, both 1.0.0 |
| Reference implementation | defining properties, asserted exactly |
| Unit tests | rotation and multiplication arithmetic |
| Golden tests | composition, H1 identity, node at zero |
| Edge-case tests | mean vs true node, out-of-range n, sidereal source |
| Schema integration | `TransformedChart`, schema 1.0.0 |
| Provenance | node used and its longitude; harmonic number; method string |
| Documented limitations | `docs/TRANSFORMS.md` |

## Design

Both map a finished natal chart through a function of ecliptic longitude, so no
astronomy is recalculated and the validated natal path is untouched — the same
approach taken for sidereal.

The two are not the same kind of thing, and the code says so. Draconic is a
rotation: every point shifts equally, so aspects and orbs survive unchanged.
Harmonic is a multiplication: it deliberately destroys the natal aspect pattern,
which is the entire technique. Aspects are therefore recomputed rather than
carried over.

## Validation by defining property

These are exact arithmetic. There is no external reference to compare against
and none is needed, because each transform has a property that holds exactly or
not at all:

| Property | Result |
|---|---|
| Draconic node at 0 Aries | exactly 0.0, not 1e-12 |
| Draconic aspects and orbs unchanged | identical multisets |
| H1 equals the natal chart | exact |
| H3 of H2 equals H6 | exact |
| A 120-degree pair becomes conjunct in H3 | exact, on a planted pair |
| Harmonic speed equals n times natal speed | exact |

The composition property is the strongest of these: it could not hold by
accident if the multiplication or the modular reduction were wrong.

## Refusals

- Harmonic n outside 1..180 is refused. Above 180 the output is arithmetic
  rather than astrology: positional error multiplies by n, so at n = 180 an
  arcminute of birth-time doubt spans three signs. The chart carries
  `HARMONIC_ERROR_AMPLIFIED` stating the factor.
- A profile naming an unsupported node type is refused rather than defaulted.
- Neither transform produces houses. Draconic rotates the zodiac, not the sky,
  so the houses of the moment belong to the natal chart. A harmonic chart is not
  the chart of any instant, so there is no RAMC to derive cusps from. Both say
  so in warnings rather than emitting something plausible.

## Quality gates

ruff PASS · mypy strict PASS (84 files) · pytest PASS

## Not in this module

Harmonic house systems, and whether a harmonic Ascendant means anything. Both
transforms take a natal chart; composite and Davison are not accepted as
sources.

Remaining v1.0 modules: progressions, solar arc, relocation, patterns,
astrocartography, ephemeris generator, asteroid support.
