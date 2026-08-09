# S6a — Vertex, Part of Fortune, south node

Natal-layer work, done before the synastry point contacts the roadmap asks for
at V1.5 section 6, because the engine had none of these points to contact.

## What other software does, and what that decided

The Part of Fortune is the only one of the three with a real dispute. By day it
is `Ascendant + Moon − Sun`; the argument is about night charts.

- The reversing convention swaps the luminaries below the horizon. Most
  contemporary software does this. **Astrodienst does it by default and exposes
  it as a setting**, documenting that astrologers differ.
- The non-reversing convention uses one formula always. Ptolemy defined the Lot
  as the horoskopos of the Moon and reversing breaks that reading; **Lilly
  followed him** and used the day formula throughout.

By day the two agree exactly. By night they give two points reflected about the
Ascendant — about half of all charts.

The answer to "what do others do" turned out to be the design: the serious
programs **make it configurable and declare which they used**. So the sect rule
is a versioned profile field with no silent default, published in every chart's
provenance, and a night chart additionally carries `alternativeLongitude` — the
longitude the other convention would give. A user comparing against another
program would otherwise read a documented choice as a defect.

## The vertex was already being calculated and discarded

`swe.houses_ex` returns eight values in `ascmc`. The engine used two.

```
ascmc[0] Ascendant   ascmc[4] Equatorial Asc
ascmc[1] MC          ascmc[5] Co-Asc (Koch)
ascmc[2] ARMC        ascmc[6] Co-Asc (Munkasey)
ascmc[3] Vertex      ascmc[7] Polar Asc (Munkasey)
```

Adding it cost one array index.

### Where it misbehaves is the opposite end of the Earth from the usual worry

Measured for one instant:

```
latitude    vertex
  1.0       357.50
  5.0       167.36
 21.0       132.35
 45.0       104.90
 78.2        87.02
```

It is perfectly stable beyond the polar circle, where Placidus has no cusps at
all, and violently sensitive near the equator — about 170 degrees across four
degrees of latitude. A birth place recorded to the nearest city is fine at 45
degrees and not fine at 5. Charts below 10 degrees latitude now carry a warning,
which matters directly for this product: Vietnam spans 8–23°N.

## Two bugs found while building it

**My day/night test was inverted.** Houses run forward in zodiacal longitude
from the Ascendant, so the first six are the half *below* the horizon; the Sun
is up when it is 180 degrees or more ahead of the Ascendant. I had the
inequality the other way, and a 14:35 chart came out as a night chart. The
failure mode is silent — a well-formed Lot at the reflection of the right one,
on exactly the charts where the conventions disagree. Caught by a smoke test
before any commit.

**Relocation carried the source chart's derived block wholesale**, shipped in
v1.7.0 and earlier. A chart relocated to London reported:

```
angles.ascendant.sign          scorpio     (correct)
derived.bigThree.rising        pisces      (Hanoi's)
derived.chartRuler             neptune     (ruler of Pisces)
houseRulers[0].cuspSign        pisces   vs   houses[0].sign  scorpio
```

The chart contradicted itself in two places. Most of the derived block is a
function of the angles and cusps relocation had just changed — the rising sign,
the chart ruler, every house ruler, the hemisphere and quadrant counts. Fixed by
injecting the builders, the same pattern progressions already uses for `natal`.

## Zodiac handling, which is where this family of bug lives

The three points split into two cases and the split is the whole story:

- the **vertex** comes from Swiss Ephemeris tropically, and is rotated with the
  rest of its `HouseCalculation`, so no single tropical value survives inside an
  otherwise sidereal object
- the **Lot** and the **south node** are arithmetic on longitudes the chart
  already holds, and the ayanamsa cancels through:
  `(Asc − a) + (Moon − a) − (Sun − a) = Asc + Moon − Sun − a`

Two mechanisms, one required result. Asserted: every point differs from its
tropical twin by exactly the recorded ayanamsa. A double rotation would show as
twice it; a missing one as zero.

Found on the way: `_to_sidereal_geometry` rebuilt the `HouseCalculation` and
dropped the new vertex field, so sidereal charts had no vertex at all. Caught by
the same assertion.

## Availability

Only the south node survives an unknown birth time — the other three need an
Ascendant, and nothing is substituted.

## Verification

```
ruff   clean
mypy   clean, 104 source files
pytest 584 passed, 1721 subtests, 0 skipped   (564 -> 584)
```

Versions: engine 1.7.0 → 1.8.0, natal schema 1.2.0 → 1.3.0. Additive for the new
`points` block; **not** additive for relocation, whose derived block now
describes the relocated chart rather than the source one.

## Next

S6b: point contacts in synastry, which now have something to contact.
