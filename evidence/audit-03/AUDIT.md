# Audit 03 — review of S1 through S12

Systematic cross-product review of everything built in the synastry roadmap,
using the strategy that has repeatedly worked here: cross one axis against every
capability, because the defects live in combinations nobody ran together.

**One real bug found.** Everything else that differed turned out to be correct
behaviour, and saying so is half the value of the review.

## The bug: a sidereal composite chart half in each frame

Isolated by building a sidereal profile identical to the tropical default in
every other respect — same house system, same rulership, same points — so the
zodiac was the only variable and anything that moved was a frame effect.

```
composite bodies       rotate by 23.724112   correct
composite mc / ic      rotate by 23.724112   correct
composite ascendant    rotate by 37.304311   WRONG, 13.58 degrees adrift
composite descendant   rotate by 37.304311   WRONG
```

The chain:

1. `mc_a` and `mc_b` come from the two natal charts, which on a sidereal engine
   are **already rotated**
2. their midpoint is therefore a sidereal Midheaven
3. `right_ascension_of(midheaven, obliquity)` converts ecliptic longitude to
   right ascension, which is measured **from the true equinox** — so it is only
   valid on a tropical longitude
4. the resulting ARMC is wrong by the ayanamsa, and `houses_armc` derives the
   Ascendant and every cusp from it

The Midheaven survived because it is carried through directly rather than read
back from the geometry. So the chart was internally inconsistent: bodies and
Midheaven in one frame, Ascendant and cusps in another.

It propagated to composite houses, composite transits to the angles, and the
progressed composite.

Fixed by putting the Midheaven back into the tropical frame for the geometry and
rotating the whole result once at the end — the same shape as
`_to_sidereal_geometry` and the astrocartography un-rotation. The offset is the
mean of the two charts' ayanamsas, which is the consistent choice for a midpoint
construction.

**No existing test caught it**, because none compared a sidereal composite's
angles against its own bodies. Four now do, and they fail on the old code with
`angles must share one rotation`.

## What differed and was correct

**Four angle interactions vanish under rotation.** All four sat at orb
6.93–6.99 against a 7.0 limit. The two charts carry *different* ayanamsas
(23.757077 and 23.691147, being born at different epochs), so the relative
geometry between them shifts by 0.066° — enough to flip contacts sitting inside
that of the boundary. A genuine property of sidereal synastry, not an error.

**Ruler interactions differ.** Rulership is by sign, and signs change under
rotation, so a chart's house rulers legitimately differ between zodiacs.

**Cross stelliums differ.** Also sign-based.

**Cross aspects, point contacts and progressed contacts are identical**, as they
must be: all are separations between quantities rotated by the same amount.

## The other axes, all clean

**Unknown birth time**, all four combinations across eight capabilities: every
one behaves. Progressions and progressed composite refuse in three of the four,
inherited from the progression layer's requirement for a known birth time.

**Composite transits when the composite has no angles**: `anglesIncluded: false`
and no contact to an angle that does not exist.

**Self-synastry**: coherent, and progressed A→natal B mirrors natal A→progressed
B exactly when both charts are the same, which is the right degenerate answer.

**Evidence rule, 15 random pairs**:

```
unresolved citations        0
duplicate ids               0
empty non-stellium patterns 0
view ids reaching the score 0
duplicate activation ids    0
evidence cap violations     0
section cap violations      0
```

The fourth line is the one worth naming: no pattern, point contact or ruler
interaction id ever appears in a score contribution. The shape that appeared
four times during the build — the same geometry counted twice under two names —
is not present anywhere in the finished result.

## Verification

```
ruff   clean
mypy   clean, 111 source files
pytest 644 passed, 2215 subtests, 0 skipped   (640 -> 644)
```

Engine 1.12.0 -> 1.12.1, composite schema 1.2.0 -> 1.2.1. A correctness fix:
sidereal composite charts change, tropical ones do not.
