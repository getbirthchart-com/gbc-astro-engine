# Relocation and astrocartography

Two ways of asking the same question. Relocation asks what one other place
looked like; astrocartography asks which places looked a particular way. Neither
moves a planet.

## Relocation

Recasts the same birth moment for a different place. Body longitudes are
geocentric and carried over untouched — the planets were where they were — so
**aspects are unchanged by construction**. Only the angles, the cusps and the
house placements differ.

```python
london = engine.relocate(natal, 51.5074, -0.1278)
```

| | Natal (Hanoi) | London | New York | Sydney |
|---|---|---|---|---|
| ASC | Pisces 20.11 | Scorpio 16.59 | Virgo 24.10 | Taurus 1.69 |
| MC | Sagittarius | Virgo | Gemini | Aquarius |
| Sun house | 8 | 12 | 2 | 7 |

Relocating to the birthplace returns the identical chart — asserted, not assumed.

Positions stay **geocentric**. A topocentric chart would shift the Moon by up to
about a degree, but that is a different calculation and mixing the two would
leave a reader unable to tell which effect they were seeing.

An unknown birth time is refused: relocation changes only the angles and houses,
and such a chart has neither, so nothing would be relocated.

## Astrocartography

Every place on Earth where, at one fixed instant, a body sits on an angle. The
instant never changes and only the observer moves, so the body's right ascension
and declination are constants and **every line has a closed form**. No root
finding is involved.

```
MC line    longitude = RA − GST                        (a meridian)
IC line    the same meridian, half a turn away
ASC line   H = −acos(−tan(lat)·tan(dec)); lon = RA + H − GST
DSC line   the same with +acos
```

```python
result = engine.astrocartography(natal, bodies=("sun", "moon", "jupiter"))
```

MC and IC lines are **meridians**: one longitude, valid at every latitude. ASC
and DSC lines are **curves**, sampled per latitude.

Where a body is circumpolar or never rises, it has no rising line at that
latitude, and the latitude is **omitted** — never clamped to the nearest one that
happens to work. `detail.omittedLatitudes` counts them.

### In mundo, not zodiacal

A line marks where the body **actually crosses** the meridian or horizon: right
ascension equals local sidereal time, or altitude equals zero. This is the
convention astrocartography has used since Jim Lewis, and it is what the code
computes.

It is not the same as "the body's longitude equals the Midheaven's longitude".
For a body with ecliptic latitude the two differ, and not slightly:

| Body | Ecliptic latitude | Difference in geographic longitude |
|---|---:|---:|
| Sun | 0.00° | 0.2″ |
| Jupiter | 1.12° | 0.48° |
| Moon | 4.43° | **52°** |

Fifty-two degrees of longitude is the width of the Atlantic. The distinction is
not academic, and this module states which side of it the answer is on.

### Validation

Self-consistency, checked against definitions rather than against another
implementation:

| Check | Result |
|---|---|
| On an MC line, RA equals local sidereal time | **0.000000″** |
| On a horizon line, altitude equals zero | **0.000000″** |
| MC line is one longitude at every latitude | exact |
| IC line is 180° from the MC line | exact |
| Relocating to the birthplace reproduces the chart | exact |
| Relocated aspects equal natal aspects | exact |
| The Midheaven ignores latitude | exact |

The first validation attempt compared body *longitude* against MC *longitude*
and produced errors of 0.2″, 1740″ and 187170″ for Sun, Jupiter and Moon. That
pattern — proportional to ecliptic latitude — is what identified the mistake as
mixing the two conventions rather than a defect in the lines.

## Limitations

- Paran lines (latitude crossings of two bodies' angular lines) are not
  implemented.
- Local space lines are not implemented.
- Astrocartography returns a dictionary rather than a canonical dataclass; it is
  a primitive for a map layer, not a chart.
