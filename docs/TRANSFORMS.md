# Chart transforms: draconic and harmonic

Both map a finished natal chart through a documented function of ecliptic
longitude. Neither recalculates anything astronomical, so the validated natal
path runs untouched.

They differ in one way that matters: **draconic is a rotation, harmonic is not.**
A rotation preserves the angles between bodies, so aspects and orbs survive it
unchanged. Multiplication does not, and destroying the old aspect pattern to
reveal a new one is precisely what a harmonic chart is for.

## Draconic

Re-zeroes the zodiac on the Moon's north node instead of the vernal equinox.
Every longitude has the node's longitude subtracted, so **the node lands on
exactly 0° Aries** — the definition of the transform, and therefore asserted
exactly rather than to a tolerance.

```python
draconic = engine.draconic(natal)
draconic.bodies["true_node"].longitude   # 0.0
```

Which node is used comes from the profile's `node_type`: `true` or `mean`. Both
give different charts, and `meta.nodeBody` records which one.

Aspects and orbs are identical to the natal chart. Only sign and degree labels
move.

**No houses.** The rotation is of the zodiac, not of the sky. The houses of the
moment are unchanged and belong to the natal chart, so this one carries none.

## Harmonic

Multiplies every longitude by *n* and takes the result modulo 360.

```python
h5 = engine.harmonic(natal, 5)
```

| Property | Behaviour |
|---|---|
| Longitude | × n, mod 360 |
| Speed | × n — it is the derivative of the longitude |
| Retrograde | unchanged; n is positive and cannot flip a sign |
| Latitude, distance | untouched; the transform is defined on longitude only |
| Aspects | **recomputed**, not carried over |
| Houses | none |

Two bodies exactly 360/n apart become conjunct. A trine is a conjunction in H3,
a square is a conjunction in H4. That collapse is the whole technique.

The transform composes exactly: **H3 of H2 is H6**, which is asserted in the
tests and is the strongest available evidence that it does what it claims.

**No houses.** A harmonic chart is not the chart of any instant or place, so it
has no right ascension of the Midheaven to derive cusps from, and none is
substituted.

**Error is amplified by n.** An arcminute of doubt in a birth time becomes n
arcminutes here. At n = 60 that is a whole degree; at n = 180, three signs. The
chart carries `HARMONIC_ERROR_AMPLIFIED` saying so, and n is capped at 180
because beyond that the output is arithmetic rather than astrology.

## CLI

```bash
gbc draconic --date 1992-11-03 --time 14:35 --timezone Asia/Ho_Chi_Minh \
  --lat 21.0285 --lng 105.8542 --json

gbc harmonic --n 5 --date 1992-11-03 --time 14:35 --timezone Asia/Ho_Chi_Minh \
  --lat 21.0285 --lng 105.8542 --json
```

## Validation

These are exact arithmetic, so they are validated by their defining properties
rather than against an external reference:

| Property | Holds |
|---|---|
| Draconic node at 0° Aries | exactly |
| Draconic aspects and orbs unchanged | exactly |
| H1 equals the natal chart | exactly |
| H3 ∘ H2 = H6 | exactly |
| Trine becomes conjunction in H3 | exactly, on a planted pair |
| Harmonic speed = n × natal speed | exactly |

Both work on sidereal charts as well as tropical; `meta.zodiac` records which
the source used.

## Limitations

- Neither produces houses, for the reasons above.
- Harmonic angles are produced because an angle is an ecliptic longitude and the
  transform is well defined on it. Whether a harmonic Ascendant means anything
  is a question for the reader, not the engine.
- Davison and composite charts are not accepted as sources; both transforms take
  a natal chart.
